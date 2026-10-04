import logging
import re
import time
from types import SimpleNamespace
from typing import Any

from pydantic import BaseModel, Field

from app.core.config import settings
from app.domains.exams.llm.base import get_judge_llm, get_model_info
from app.domains.exams.llm.generator import (
    build_question_plan,
    generate_all,
    generate_section,
)
from app.domains.exams.llm.prompts import (
    MAX_SLOTS_PER_CALL,
    build_quality_messages,
)

logger = logging.getLogger("eduverse.exams.llm.services")


def part_b_marks(paper: Any) -> int:

    part_b = getattr(paper, "part_b", None) or []
    if isinstance(part_b, dict):
        part_b = part_b.get("questions", [])
    if not isinstance(part_b, list):
        return 0
    return sum(int(q.get("marks", 0) or 0) for q in part_b if isinstance(q, dict))


def ai_budget(paper: Any, *, total_marks: int | None = None) -> int:

    total = int(
        total_marks
        if total_marks is not None
        else (getattr(paper, "total_marks", 0) or 0)
    )
    return max(0, total - part_b_marks(paper))


# ------------------------------------------------------------
# Paper record → prompt context
# ------------------------------------------------------------


def config_to_source(config: dict[str, Any]) -> SimpleNamespace:

    cfg = config or {}
    return SimpleNamespace(
        id=None,
        title=cfg.get("title") or "",
        class_name=cfg.get("class_name") or "",
        subject=cfg.get("subject") or "",
        board=cfg.get("board") or "CBSE",
        exam_type=cfg.get("exam_type") or "Unit Test",
        language=cfg.get("language") or "English",
        chapters=list(cfg.get("chapters") or []),
        total_marks=int(cfg.get("total_marks") or 0),
        duration_minutes=int(cfg.get("duration_minutes") or 60),
        instructions=list(cfg.get("instructions") or []),
        scope=dict(cfg.get("scope") or {}),
        constraints=dict(cfg.get("constraints") or {}),
        sources=list(cfg.get("sources") or []),
        blueprint=cfg.get("blueprint") or [],
        coverage_mode=cfg.get("coverage_mode") or "auto",
        coverage_plan=cfg.get("coverage_plan") or {},
        part_a=[],
        part_b=list(cfg.get("part_b") or []),
        status=None,
    )


def build_ctx(paper: Any, *, total_marks: int | None = None) -> dict[str, Any]:

    return {
        "exam_title": getattr(paper, "title", "") or "",
        "class_name": getattr(paper, "class_name", "") or "",
        "subject": getattr(paper, "subject", "") or "",
        "board": getattr(paper, "board", "") or "CBSE",
        "exam_type": getattr(paper, "exam_type", "") or "Unit Test",
        "language": getattr(paper, "language", "") or "English",
        "chapters": list(getattr(paper, "chapters", None) or []),
        "total_marks": int(
            total_marks
            if total_marks is not None
            else (getattr(paper, "total_marks", 0) or 0)
        ),
        "duration_minutes": int(getattr(paper, "duration_minutes", 60) or 60),
        # Distribution settings .env se (File 9) — deterministic rotation inhi se
        "difficulty_mix": settings.difficulty_mix_list,
        "bloom_mix": settings.bloom_mix_list,
        "instructions": [
            str(i)
            for i in (getattr(paper, "instructions", None) or [])
            if str(i).strip()
        ],
        "scope": dict(getattr(paper, "scope", None) or {}),
        "constraints": dict(getattr(paper, "constraints", None) or {}),
    }


def build_sources(
    paper: Any,
    *,
    plan: dict[str, Any] | None = None,
    school_id: int | str | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:

    raw = getattr(paper, "sources", None) or []
    sources = [s for s in raw if isinstance(s, dict)]
    excerpts: list[str] = []

    # ---- Layer 3: paste/typed text (frontend se seedha) ----
    for s in sources:
        text = str(s.get("textExcerpt") or s.get("text") or "").strip()
        if not text:
            continue
        label = (
            s.get("label")
            or s.get("fileName")
            or s.get("url")
            or s.get("bankRef")
            or s.get("sourceType")
            or "source"
        )
        excerpts.append(f"[{label}] {text}")

    rag_meta: dict[str, Any] = {}
    if settings.RAG_ENABLED:
        try:
            from app.domains.exams.rag import retriever

            pack = retriever.context_pack(paper, plan=plan, school_id=school_id)
            rag_meta = {
                "used_rag": pack.get("used_rag"),
                "hits": len(pack.get("hits") or []),
                "warnings": pack.get("warnings") or [],
            }
            if pack.get("excerpts"):
                excerpts.extend(pack["excerpts"])
            if pack.get("sources"):
                sources = [*sources, *(pack["sources"] or [])]
        except Exception as exc:
            logger.warning("RAG retrieval skip: %s: %s", type(exc).__name__, exc)
            rag_meta = {"used_rag": False, "error": f"{type(exc).__name__}: {exc}"}

    logger.info(
        "build_sources: %s teacher sources + %s excerpts (rag=%s, hits=%s)",
        len(sources),
        len(excerpts),
        rag_meta.get("used_rag"),
        rag_meta.get("hits"),
    )
    return sources, excerpts


def _normalise_blueprint(raw: Any) -> list[dict[str, Any]]:

    if isinstance(raw, list):
        return [s for s in raw if isinstance(s, dict)]

    if isinstance(raw, dict):
        for key in ("sections", "blueprint", "items"):
            if isinstance(raw.get(key), list):
                return [s for s in raw[key] if isinstance(s, dict)]
        if raw.get("type"):  # single section dict
            return [raw]

    return []


# ------------------------------------------------------------
# Plan — paper → slot plan
# ------------------------------------------------------------


def plan_for_paper(
    paper: Any,
    *,
    blueprint: Any = None,
    coverage: Any = None,
    total_marks: int | None = None,
    ai_marks: int | None = None,
) -> dict[str, Any]:
    """Paper → slot plan (`build_question_plan`) + budget.

    `ai_budget` plan ke andar daal dete hain, taaki summary/report mein
    "plan kitna tha vs budget kitna tha" compare ho sake (audit trail).
    """
    blueprint_list = (
        _normalise_blueprint(blueprint)
        if blueprint is not None
        else _normalise_blueprint(getattr(paper, "blueprint", None))
    )
    raw_coverage = (
        coverage if coverage is not None else getattr(paper, "coverage_plan", None)
    )
    coverage_plan = raw_coverage if isinstance(raw_coverage, dict) else {}

    budget = (
        int(ai_marks)
        if ai_marks is not None
        else ai_budget(paper, total_marks=total_marks)
    )

    ctx = build_ctx(paper, total_marks=total_marks)
    plan = build_question_plan(
        blueprint=blueprint_list,
        ai_budget=budget,
        coverage_plan=coverage_plan,
        chapters=ctx["chapters"],
        difficulty_mix=ctx["difficulty_mix"],
        bloom_mix=ctx["bloom_mix"],
    )
    plan["ai_budget"] = budget
    return plan


# ------------------------------------------------------------
# Generation — paper → QUESTIONS
# ------------------------------------------------------------


def generate_paper_questions(
    paper: Any,
    *,
    blueprint: Any = None,
    coverage: Any = None,
    total_marks: int | None = None,
    batch_size: int | None = None,
    progress: Any = None,
    repair_passes: int = 1,
    used: list[str] | None = None,
    llm: Any = None,
) -> dict[str, Any]:

    ctx = build_ctx(paper, total_marks=total_marks)
    plan = plan_for_paper(
        paper, blueprint=blueprint, coverage=coverage, total_marks=total_marks
    )
    sources, excerpts = build_sources(paper, plan=plan)
    slots = plan.get("slots") or []

    if not slots:
        # Blueprint khaali / budget 0 → generate karne layak kuch nahi.
        # (File 17 ise job ke `done` + saaf message ke saath handle karega.)
        logger.warning(
            "generate_paper_questions: plan mein koi slot nahi (budget=%s)",
            plan.get("ai_budget"),
        )
        empty = {
            "questions": [],
            "generated": 0,
            "expected": 0,
            "marks": 0,
            "elapsed": 0.0,
            "failed_batches": [],
        }
        summary = _build_summary(plan, paper, empty)
        summary["repaired"] = []
        summary["repaired_count"] = 0
        summary["incomplete"] = []
        # Saaf wajah (frontend ko "0 questions kyun?" ka jawab dikhana zaroori hai):
        if int(plan.get("ai_budget") or 0) <= 0:
            summary["note"] = (
                "AI ke liye 0 marks bache — teacher ke custom questions (part_b) ne "
                "poora total_marks kha liya. Custom questions ke marks kam karo ya "
                "total_marks badhao, phir generate karo."
            )
        else:
            summary["note"] = (
                "Plan se koi slot nahi bana — blueprint ke count/marksEach check karo."
            )
        return {
            "questions": [],
            "plan": plan,
            "ctx": ctx,
            "summary": summary,
            "model_info": get_model_info(),
        }

    if progress:
        progress(
            f"Planning {len(slots)} questions...",
            1,
            {"stage": "planning", "total": len(slots)},
        )

    result = generate_all(
        plan=plan,
        ctx=ctx,
        sources=sources,
        excerpts=excerpts,
        constraints=ctx["constraints"],
        instructions=ctx["instructions"],
        llm=llm,
        progress=progress,
        batch_size=batch_size or MAX_SLOTS_PER_CALL,
        used=used,
    )

    questions = result["questions"]
    repaired: list[str] = []
    if repair_passes > 0 and questions:
        if progress:
            progress("Repairing incomplete questions...", 92, {"stage": "repairing"})
        questions, repaired = repair_incomplete(
            questions=questions,
            ctx=ctx,
            sources=sources,
            excerpts=excerpts,
            constraints=ctx["constraints"],
            instructions=ctx["instructions"],
            llm=llm,
            passes=repair_passes,
        )
        if repaired:
            result = {
                **result,
                "questions": questions,
                "generated": sum(
                    1 for q in questions if str(q.get("text") or "").strip()
                ),
                "marks": sum(int(q.get("marks") or 0) for q in questions),
            }

    summary = _build_summary(plan, paper, result)
    summary["repaired"] = repaired
    summary["repaired_count"] = len(repaired)
    incomplete = [
        str(q.get("id") or "?")
        for q in questions
        if q.get("incomplete") or not str(q.get("text") or "").strip()
    ]
    summary["incomplete"] = incomplete
    logger.info(
        "generate_paper_questions: %s/%s questions | %s marks (budget %s) | balanced=%s",
        summary["question_count"],
        summary["expected_count"],
        summary["marks_total"],
        summary["ai_budget"],
        summary["balanced"],
    )

    return {
        "questions": result["questions"],
        "plan": plan,
        "ctx": ctx,
        "summary": summary,
        "model_info": get_model_info(),
    }


def _build_summary(
    plan: dict[str, Any], paper: Any, result: dict[str, Any]
) -> dict[str, Any]:

    teacher_marks = part_b_marks(paper)
    total = int(getattr(paper, "total_marks", 0) or 0)
    ai_marks = int(result.get("marks") or 0)

    return {
        "question_count": int(result.get("generated") or 0),
        "expected_count": int(result.get("expected") or 0),
        "marks_total": ai_marks,
        "ai_budget": plan.get("ai_budget"),
        "planned_marks": plan.get("planned_marks"),
        "plan_marks": plan.get("final_marks"),
        "trimmed": plan.get("trimmed") or [],
        "trimmed_marks": plan.get("trimmed_marks") or 0,
        "gap_filled": plan.get("gap_filled") or [],
        "gap_bumped": plan.get("gap_bumped") or [],
        "failed_batches": result.get("failed_batches") or [],
        "elapsed": result.get("elapsed") or 0.0,
        "balanced": bool(plan.get("balanced")) and ai_marks == plan.get("ai_budget"),
        "contract": {
            "ai_marks": ai_marks,
            "teacher_marks": teacher_marks,
            "total_marks": total,
            "ok": (ai_marks + teacher_marks) == total and total > 0,
        },
    }


def coverage_report(
    coverage_plan: dict[str, Any] | None,
    questions: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:

    plan_chapters = [
        c for c in ((coverage_plan or {}).get("chapters") or []) if c.get("chapter")
    ]
    mode = str((coverage_plan or {}).get("mode") or "auto")

    per_chapter: dict[str, int] = {}
    total = 0
    for q in questions or []:
        if not isinstance(q, dict):
            continue
        marks = int(q.get("marks") or 0)
        total += marks
        chapter = str(q.get("chapter") or "")
        per_chapter[chapter] = per_chapter.get(chapter, 0) + marks

    if not plan_chapters:
        return [
            {
                "chapter": "Auto (all marks via Random)",
                "target": 0,
                "got": total,
                "ok": True,
                "mode": mode,
            }
        ]

    rows: list[dict[str, Any]] = []
    for c in plan_chapters:
        chapter = str(c.get("chapter") or "")
        target = int(c.get("targetMarks") or 0)
        got = int(per_chapter.get(chapter, 0))
        rows.append(
            {
                "chapter": chapter,
                "target": target,
                "got": got,
                # `percent` mode mein target **%** hai (marks nahi), isliye
                # comparison bekaar hai — wahan sirf information dikhate hain.
                "ok": True if mode != "marks" else got == target,
                "mode": mode,
            }
        )
    return rows


# ------------------------------------------------------------
# BOUNDED REPAIR — failed/incomplete slots dobara (agentic, par leash ke saath)
# ------------------------------------------------------------


def _slot_from_question(q: dict[str, Any], index: int) -> dict[str, Any]:

    return {
        "slot_id": str(q.get("id") or f"Q{index + 1}"),
        "type": str(q.get("type") or "Short"),
        "marks": int(q.get("marks") or 1),
        "difficulty": q.get("difficulty") or "Medium",
        "bloom": q.get("bloom") or "Understand",
        "chapter": q.get("chapter") or "",
        "topic": q.get("topic") or "",
        "has_image": bool(q.get("hasImage")),
        "origin": "ai",
        "repair": True,
    }


def repair_incomplete(
    *,
    questions: list[dict[str, Any]],
    ctx: dict[str, Any],
    sources: list[dict[str, Any]] | None,
    excerpts: list[str] | None,
    constraints: dict[str, Any] | None,
    instructions: list[str] | None,
    llm: Any = None,
    passes: int = 1,
) -> tuple[list[dict[str, Any]], list[str]]:

    if passes <= 0 or not questions:
        return questions, []

    repaired_ids: list[str] = []
    current = [dict(q) for q in questions]

    for _ in range(passes):
        broken = [
            (i, q)
            for i, q in enumerate(current)
            if q.get("incomplete") or not str(q.get("text") or "").strip()
        ]
        if not broken:
            break

        by_type: dict[str, list[tuple[int, dict[str, Any]]]] = {}
        for i, q in broken:
            by_type.setdefault(str(q.get("type") or "Short"), []).append((i, q))

        fixed_any = False
        for qtype, items in by_type.items():
            slots = [_slot_from_question(q, i) for i, q in items]
            broken_indices = {i for i, _ in items}
            used = [
                str(x.get("text"))
                for j, x in enumerate(current)
                if j not in broken_indices and x.get("text")
            ]
            produced = generate_section(
                qtype=qtype,
                ctx=ctx,
                slots=slots,
                sources=sources,
                excerpts=excerpts,
                constraints=constraints,
                instructions=instructions,
                used=used,
                llm=llm,
            )
            if not produced:
                logger.warning("repair: %s ke liye model ne kuch nahi diya", qtype)
                continue
            for (idx, old), fresh in zip(items, produced, strict=False):
                if not str(fresh.get("text") or "").strip():
                    continue
                current[idx] = {**old, **fresh, "incomplete": False, "repaired": True}
                repaired_ids.append(str(current[idx].get("id") or idx))
                fixed_any = True

        if not fixed_any:
            break

    if repaired_ids:
        logger.info("repair: %s question(s) dobara bane", len(repaired_ids))
    return current, repaired_ids


# ------------------------------------------------------------
# QUALITY — Layer 1: rule checks (deterministic, instant)
# ------------------------------------------------------------

_NORM_RE = re.compile(r"[^a-z0-9]+")

# Model options ko enumerate karke deta hai: "A) Yeast", "1. Bacteria", "b- Virus".
# Isliye comparison se pehle ye prefix hatana zaroori hai.
_OPTION_PREFIX_RE = re.compile(r"^\s*(?:[a-dA-D]|\d{1,2})\s*[).:\-]\s*")


def _norm(text: str) -> str:
    """Compare karne ke liye text saaf karo — case/punctuation/space ka farq hatao."""
    return _NORM_RE.sub(" ", (text or "").lower()).strip()


def _norm_option(text: str) -> str:
    return _norm(_OPTION_PREFIX_RE.sub("", text or ""))


def _token_set(text: str) -> set[str]:

    return {t for t in _norm(text).split() if len(t) > 3}


def _jaccard(a: set[str], b: set[str]) -> float:

    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


MAX_HONEST_MARKS: dict[str, int] = {
    "MCQ": 2,
    "TrueFalse": 2,
    "FillBlanks": 2,
    "OneWord": 2,
    "VeryShort": 2,
    "Match": 3,
    "AssertionReason": 3,
    "MultipleSelect": 3,
    "Short": 4,
    "Long": 8,
    "Essay": 10,
    "CaseStudy": 10,
    "Diagram": 5,
    "Map": 4,
    "Graph": 5,
    "LabelDiagram": 4,
}


def rule_checks(
    questions: list[dict[str, Any]],
    *,
    coverage_plan: dict[str, Any] | None = None,
    ctx: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:

    issues: list[dict[str, Any]] = []
    seen: list[tuple[str, str, set[str]]] = []  # (id, normalized, tokens)
    chapters = {c for c in ((ctx or {}).get("chapters") or []) if c}

    for q in questions or []:
        if not isinstance(q, dict):
            continue

        qid = str(q.get("id") or "?")
        text = str(q.get("text") or "")
        answer = str(q.get("answer") or "")
        qtype = str(q.get("type") or "")
        options = [str(o) for o in (q.get("options") or [])]
        marks = int(q.get("marks") or 0)
        difficulty = str(q.get("difficulty") or "Medium")
        chapter = str(q.get("chapter") or "")

        if not text.strip() or q.get("incomplete"):
            issues.append(
                {
                    "question_id": qid,
                    "code": "incomplete",
                    "severity": "high",
                    "message": "This question has no text. Regenerate it, or write your own version.",
                }
            )

        if not answer.strip():
            issues.append(
                {
                    "question_id": qid,
                    "code": "missing_answer",
                    "severity": "high",
                    "message": "No expected answer was provided, so the answer key will be incomplete.",
                }
            )

        na = _norm(answer)
        if na and len(na) >= 12 and na in _norm(text):
            issues.append(
                {
                    "question_id": qid,
                    "code": "answer_leak",
                    "severity": "high",
                    "message": (
                        "The answer is written inside the question itself. "
                        "Reword the question so the answer stays hidden."
                    ),
                }
            )

        if qtype in ("MCQ", "MultipleSelect"):
            if 0 < len(options) < 4:
                issues.append(
                    {
                        "question_id": qid,
                        "code": "weak_options",
                        "severity": "medium",
                        "message": f"This {qtype} has only {len(options)} options; 4 are expected.",
                    }
                )

            normed = [o for o in (_norm_option(opt) for opt in options) if o]

            if len(normed) != len(set(normed)):
                issues.append(
                    {
                        "question_id": qid,
                        "code": "duplicate_option",
                        "severity": "medium",
                        "message": "Two options are identical. Change one of them.",
                    }
                )

            if answer.strip() and na:
                positional = na in {"a", "b", "c", "d"} or na.startswith("option ")
                matched = any(na in no or no in na for no in normed if len(no) > 1)
                if not positional and not matched:
                    issues.append(
                        {
                            "question_id": qid,
                            "code": "answer_mismatch",
                            "severity": "high",
                            "message": (
                                "The answer key does not match any option. "
                                "Fix the answer or the options."
                            ),
                        }
                    )

        nt = _norm(text)
        if nt:
            dup_of: str | None = None
            tokens = _token_set(text)
            for other_id, other_norm, other_tokens in seen:
                if other_norm == nt or _jaccard(tokens, other_tokens) >= 0.8:
                    dup_of = other_id
                    break
            if dup_of:
                issues.append(
                    {
                        "question_id": qid,
                        "code": "duplicate",
                        "severity": "high",
                        "message": f"This question is a duplicate of {dup_of}. Remove one of them.",
                    }
                )
            else:
                seen.append((qid, nt, tokens))

        if chapters and chapter and chapter not in chapters:
            issues.append(
                {
                    "question_id": qid,
                    "code": "off_chapter",
                    "severity": "medium",
                    "message": f"Chapter '{chapter}' is not one of the selected chapters.",
                }
            )

        limit = MAX_HONEST_MARKS.get(qtype)
        if limit and marks > limit:
            issues.append(
                {
                    "question_id": qid,
                    "code": "marks_mismatch",
                    "severity": "medium",
                    "message": (
                        f"{marks} marks is high for a {qtype} "
                        f"(usually up to {limit}). Check the depth."
                    ),
                }
            )
        if difficulty == "Hard" and marks <= 1:
            issues.append(
                {
                    "question_id": qid,
                    "code": "marks_mismatch",
                    "severity": "low",
                    "message": "1 mark seems low for a Hard question.",
                }
            )

    return issues


# ------------------------------------------------------------
# QUALITY — Layer 2: LLM judge (semantic)
# ------------------------------------------------------------


class QualityIssue(BaseModel):
    question_id: str = Field(description="Question id from the given list, e.g. q3.")
    code: str = Field(
        description=(
            "One of: answer_leak, answer_mismatch, duplicate_option, "
            "marks_mismatch, off_syllabus, language_mismatch, unclear."
        )
    )
    severity: str = Field(default="medium", description="high | medium | low")
    message: str = Field(description="One line, simple English, actionable.")


class QualityReport(BaseModel):
    issues: list[QualityIssue] = Field(default_factory=list)


_ALLOWED_CODES = {
    "answer_leak",
    "answer_mismatch",
    "duplicate_option",
    "marks_mismatch",
    "off_syllabus",
    "language_mismatch",
    "unclear",
}
_ALLOWED_SEVERITY = {"high", "medium", "low"}


def _sanitise_llm_issues(
    raw_issues: list[dict[str, Any]], valid_ids: set[str]
) -> list[dict[str, Any]]:

    out: list[dict[str, Any]] = []
    for issue in raw_issues or []:
        if not isinstance(issue, dict):
            continue
        qid = str(issue.get("question_id") or "").strip()
        code = str(issue.get("code") or "").strip()
        severity = str(issue.get("severity") or "medium").strip().lower()
        message = str(issue.get("message") or "").strip()

        if qid and qid not in valid_ids:
            logger.debug("judge ne unknown question_id diya: %s (drop)", qid)
            continue
        if code not in _ALLOWED_CODES:
            code = "unclear"
        if severity not in _ALLOWED_SEVERITY:
            severity = "medium"
        if not message:
            continue

        out.append(
            {
                "question_id": qid,
                "code": code,
                "severity": severity,
                "message": message,
                "by": "judge",
            }
        )
    return out


def check_quality(
    questions: list[dict[str, Any]],
    *,
    ctx: dict[str, Any] | None = None,
    coverage_plan: dict[str, Any] | None = None,
    use_llm: bool = True,
    llm: Any = None,
    max_llm_issues: int = 12,
) -> dict[str, Any]:

    t0 = time.time()
    questions = questions or []
    ctx = ctx or {}

    # --- Layer 1: rules (kabhi fail nahi hote, kabhi slow nahi) ---
    issues: list[dict[str, Any]] = [
        {**issue, "by": "rules"}
        for issue in rule_checks(questions, coverage_plan=coverage_plan, ctx=ctx)
    ]
    source = "rules"
    llm_error: str | None = None

    # --- Layer 2: judge (semantic) ---
    if use_llm and questions:
        try:
            judge = llm or get_judge_llm()
            messages = build_quality_messages(
                ctx=ctx, questions=questions, coverage_plan=coverage_plan
            )
            structured = judge.with_structured_output(QualityReport)
            report = structured.invoke(messages)
            raw = [
                i.model_dump() if isinstance(i, BaseModel) else dict(i)
                for i in (getattr(report, "issues", None) or [])
            ][:max_llm_issues]
            valid_ids = {
                str(q.get("id") or "?") for q in questions if isinstance(q, dict)
            }
            issues.extend(_sanitise_llm_issues(raw, valid_ids))
            source = "rules+judge"
        except Exception as exc:
            llm_error = f"{type(exc).__name__}: {exc}"
            logger.warning("quality judge fail (rules-only report): %s", llm_error)

    deduped: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, str]] = set()
    for issue in issues:
        key = (str(issue.get("question_id") or ""), str(issue.get("code") or ""))
        if key in seen_keys:
            continue
        seen_keys.add(key)
        deduped.append(issue)

    counts = {"high": 0, "medium": 0, "low": 0}
    for issue in deduped:
        sev = str(issue.get("severity") or "medium")
        counts[sev] = counts.get(sev, 0) + 1

    verdict = "ok" if counts["high"] == 0 else "review"

    result = {
        "issues": deduped,
        "counts": {**counts, "total": len(deduped)},
        "verdict": verdict,
        "source": source,
        "llm_error": llm_error,
        "elapsed": round(time.time() - t0, 1),
    }
    logger.info(
        "check_quality: %s issues (%s) | verdict=%s | %ss",
        len(deduped),
        source,
        verdict,
        result["elapsed"],
    )
    return result


BASE_MARKS_BY_TYPE: dict[str, int] = {
    "MCQ": 1,
    "TrueFalse": 1,
    "FillBlanks": 1,
    "Match": 2,
    "AssertionReason": 2,
    "MultipleSelect": 2,
    "VeryShort": 1,
    "Short": 2,
    "Long": 4,
    "Essay": 5,
    "CaseStudy": 5,
    "Diagram": 3,
    "Map": 2,
    "Graph": 3,
    "LabelDiagram": 2,
}


class MarksSuggestion(BaseModel):
    """LLM se ek hi number — schema mein band, isliye parse ka jhanjhat nahi."""

    marks: int = Field(ge=1, le=20, description="Suggested marks for this question.")
    reason: str = Field(default="", description="One short line why.")


def suggest_marks(
    question: dict[str, Any],
    *,
    use_llm: bool = False,
    llm: Any = None,
    text_length: int | None = None,
) -> dict[str, Any]:

    qtype = str(question.get("type") or "")
    difficulty = str(question.get("difficulty") or "Medium")
    text = str(question.get("text") or "")

    # Rules length par chalti hain — aur length caller bhi de sakta hai.
    length = int(text_length) if text_length is not None else len(text)

    base = BASE_MARKS_BY_TYPE.get(qtype, 2)
    reasons = [f"base for {qtype or 'unknown type'} = {base}"]

    if difficulty == "Hard":
        base += 1
        reasons.append("Hard difficulty +1")
    if length > 120:
        base += 1
        reasons.append("lamba question +1")
    if length > 300:
        base += 1
        reasons.append("bahut lamba question +1")

    marks = max(1, min(base, 10))
    source = "rules"
    llm_marks: int | None = None
    llm_error: str | None = None

    if use_llm:
        try:
            judge = llm or get_judge_llm()
            prompt = (
                "You are a school examiner. Suggest fair marks for this question.\n"
                f"Type: {qtype or 'unknown'}\n"
                f"Difficulty: {difficulty}\n"
                f"Question: {text[:600]}\n"
                "Answer in the required schema."
            )
            structured = judge.with_structured_output(MarksSuggestion)
            suggestion = structured.invoke(prompt)
            llm_marks = int(getattr(suggestion, "marks", marks) or marks)
            # ±1 clamp — AI contract nahi tod sakta
            marks = max(1, min(base + 1, max(base - 1, llm_marks)))
            source = "rules+llm"
            reason = str(getattr(suggestion, "reason", "") or "").strip()
            if reason:
                reasons.append(f"judge: {reason}")
        except Exception as exc:
            llm_error = f"{type(exc).__name__}: {exc}"
            logger.warning("suggest_marks judge fail (rules-only): %s", llm_error)
            source = "rules"

    return {
        "marks": marks,
        "base": base,
        "source": source,
        "reasons": reasons,
        "llm_marks": llm_marks,
        "llm_error": llm_error,
    }


# ------------------------------------------------------------
# Public API
# ------------------------------------------------------------

__all__ = [
    "BASE_MARKS_BY_TYPE",
    "MAX_HONEST_MARKS",
    "MarksSuggestion",
    "QualityIssue",
    "QualityReport",
    "ai_budget",
    "build_ctx",
    "build_sources",
    "check_quality",
    "config_to_source",
    "coverage_report",
    "generate_paper_questions",
    "part_b_marks",
    "plan_for_paper",
    "repair_incomplete",
    "rule_checks",
    "suggest_marks",
]
