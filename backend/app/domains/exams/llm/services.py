# ============================================================
# llm/services.py — ORCHESTRATION: paper record ─→ questions + report (File 16).
#
# Yahan teen kaam hote hain:
#   1. PAPER → PROMPT CONTEXT   (build_ctx / build_sources / plan_for_paper)
#   2. PAPER → QUESTIONS        (generate_paper_questions → generator.generate_all)
#   3. QUESTIONS → QUALITY      (check_quality: pehle rules, phir judge LLM)
#
# ------------------------------------------------------------
# ⭐ LAYER RULE (aaj ka sabse bada seekhne wala point)
# ------------------------------------------------------------
# Ye file **DB ko chhooti hi nahi**:
#   · koi `session` parameter nahi
#   · koi `repository` import nahi
#   · koi `session.commit()` nahi
#   · koi HTTPException nahi (ye HTTP ki cheez hai, service ki nahi)
#
# Kyun? Do wajah — aur dono production mein matter karti hain:
#
#   (a) TESTABILITY — paper ek simple object bhi ho sakta hai. DB chalane ki
#       zaroorat nahi:
#           from types import SimpleNamespace
#           paper = SimpleNamespace(total_marks=30, chapters=["Ch1"], part_b=[])
#           generate_paper_questions(paper, ...)   # bas chal jayega
#
#   (b) DEPENDENCY DIRECTION — `exams/service.py` (File 17) is file ko import
#       karega, is file ko `exams/service.py` ka pata nahi. Agar hum yahan
#       repository import karte to:
#           service.py → llm/services.py → repository.py
#       chal jata, par ulta banana (repository ko llm ke andar) circular import
#       de deta. Layer ka ek hi direction hona chahiye — ye "layered
#       architecture" ki asli shart hai, sirf ek diagram nahi.
#
#       Isliye idhar se hum sirf DATA return karte hain (questions + summary),
#       aur DB mein LIKHNA File 17 (exams/service.py) ka kaam hai:
#           run_generation():  llm.services.generate_paper_questions(paper)
#                              → paper.part_a = {...}  → repository.update_paper()
#
# ------------------------------------------------------------
# ⭐ Quality check ka 2-layer design (production pattern)
# ------------------------------------------------------------
#   LAYER 1: RULE CHECKS  (deterministic, instant, free, 100% reliable)
#            — khaali text, answer missing, MCQ ka option hi answer, duplicate,
#              chapter mismatch, marks-vs-difficulty
#   LAYER 2: LLM JUDGE    (semantic, slow, cost, ~80% reliable)
#            — off-syllabus, wording se answer leak, dishonesty with marks
#
# Kyun dono? Kyunki 70% problems RULES se pakdi jaati hain — unke liye 3 minute
# LLM call ka wait karwana bura UX hai. Jo rules nahi pakad sakte (matlab/semantic)
# wahi LLM judge ko dete hain.
# ============================================================

import logging
import re
import time
from typing import Any

from pydantic import BaseModel, Field

from app.core.config import settings
from app.domains.exams.llm.base import get_judge_llm, get_model_info
from app.domains.exams.llm.generator import (
    build_question_plan,
    generate_all,
)
from app.domains.exams.llm.prompts import (
    MAX_SLOTS_PER_CALL,
    build_quality_messages,
)

logger = logging.getLogger("eduverse.exams.llm.services")


# ------------------------------------------------------------
# Marks ka hisaab — teacher (part_b) vs AI (part_a)
# ------------------------------------------------------------


def part_b_marks(paper: Any) -> int:
    """Teacher ke custom questions ka total (`part_b` JSON se).

    `part_b` ki shape do tarah se aa sakti hai:
        list  → [ {marks: 2}, ... ]            (frontend yahi bhejta hai)
        dict  → {"questions": [ ... ]}         (wrapper ke saath)
    Dono handle karte hain — DB ke JSON column mein shape ki guarantee nahi hoti,
    isliye **boundary pe normalise karo**, aage bharosa karo.
    """
    part_b = getattr(paper, "part_b", None) or []
    if isinstance(part_b, dict):
        part_b = part_b.get("questions", [])
    if not isinstance(part_b, list):
        return 0
    return sum(int(q.get("marks", 0) or 0) for q in part_b if isinstance(q, dict))


def ai_budget(paper: Any, *, total_marks: int | None = None) -> int:
    """AI ko kitne marks banane hain = total_marks - teacher ke marks.

    **Decision #1 ka pehla hissa** (blueprint §2.3.3). 30-mark paper + 7 marks
    ke 2 custom question → AI budget 23. Isse Marks Contract kabhi nahi tootta:
        23 (AI) + 7 (teacher) == 30 (total_marks)   ✅
    """
    total = int(
        total_marks
        if total_marks is not None
        else (getattr(paper, "total_marks", 0) or 0)
    )
    return max(0, total - part_b_marks(paper))


# ------------------------------------------------------------
# Paper record → prompt context
# ------------------------------------------------------------


def build_ctx(paper: Any, *, total_marks: int | None = None) -> dict[str, Any]:
    """Paper ke columns → prompt ka context dict (`build_context_block` ka input).

    Ye chhota function AI ki quality ka sabse sasta upgrade hai: bina iske model
    ko pata hi nahi hota ki paper Class 8 Science ka hai — woh "What is science?"
    jaisa generic question bana dega.
    """
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


def build_sources(paper: Any) -> tuple[list[dict[str, Any]], list[str]]:
    """`paper.sources` → (sources, excerpts) prompt ke liye.

    `excerpts` sirf **text** wale sources se bante hain (paste notes). PDF/image
    ka asli content Phase 3 (RAG/Qdrant) se aayega — tab yehi list retrieval se
    bhari jayegi, aur prompt/baaki code bilkul nahi badlega. Yehi "interface
    pehle, implementation baad" ka faayda hai.

    Label kyun lagate hain? Model ko dikhna chahiye ki excerpt kahan se aaya
    (`[Microorganisms NCERT PDF · p12-28] ...`) — isse woh source ko quote kar
    sakta hai aur teacher ko trace milta hai (blueprint §2.3.4 traceability).
    """
    raw = getattr(paper, "sources", None) or []
    sources = [s for s in raw if isinstance(s, dict)]
    excerpts: list[str] = []

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

    return sources, excerpts


def _normalise_blueprint(raw: Any) -> list[dict[str, Any]]:
    """Blueprint ko **hamesha list** banao (DB se dict bhi aa sakta hai).

    Production lesson: JSON column ka schema DB enforce nahi karta. Aaj list
    aata hai, kal koi wrapper dict likh dega — aur phir `for s in blueprint`
    silently ek dict ke keys par loop kar dega (mushkil se pakadne wala bug).
    Isliye ek hi jagah normalise karo aur poore code mein list maan lo.
    """
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
    llm: Any = None,
) -> dict[str, Any]:
    """Poora AI paper generate karo — plan → sections → questions + summary.

    **Ye function DB mein kuch nahi likhta.** Caller (File 17) `questions` ko
    `paper.part_a` mein save karega. Separation ka faayda: is function ko
    standalone chala kar test kar sakte ho, bina DB ke.

    `progress(stage, pct, extra)` callback job ke `stages` mein jaata hai →
    frontend polling se progress bar dikhata hai. Generator ko HTTP/DB ka pata
    nahi, services ko bhi nahi — bas "kahan pahunche" batate hain.
    """
    ctx = build_ctx(paper, total_marks=total_marks)
    plan = plan_for_paper(
        paper, blueprint=blueprint, coverage=coverage, total_marks=total_marks
    )
    sources, excerpts = build_sources(paper)
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
        return {
            "questions": [],
            "plan": plan,
            "ctx": ctx,
            "summary": _build_summary(plan, paper, empty),
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
    )

    summary = _build_summary(plan, paper, result)
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
    """Job ke `stages["result"]` mein jaane wala summary (frontend isi ko padhta hai).

    Yahan Marks Contract ka **final audit** hota hai:
        ai_marks (jo AI ne banaye) + teacher_marks (part_b) == total_marks ?
    `contract.ok=False` matlab paper abhi finalize ke laayak nahi — File 17/18
    isi par gate lagayenge.
    """
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
    """Option ka text — aage ka "A) " / "1. " hata kar normalise karo.

    ⚠️ REAL BUG (aaj ke LLM run ne pakda): model options **enumerate** karke
    deta hai — `['A) Yeast', 'B) Bacteria', ...]` — par answer seedha
    `"Bacteria"` hota hai. Bina prefix strip kiye comparison fail ho jaata hai
    aur `answer_mismatch` ka **jhootha alarm** aata hai (jo teacher ko
    "aapka answer galat hai" jaisa dikhta hai — sabse bura false positive).

    Ye function us galti ko ek hi jagah theek karta hai.
    """
    return _norm(_OPTION_PREFIX_RE.sub("", text or ""))


def _token_set(text: str) -> set[str]:
    """Chhote shabd (is/of/ka) hata kar tokens — duplicate detect ke liye."""
    return {t for t in _norm(text).split() if len(t) > 3}


def _jaccard(a: set[str], b: set[str]) -> float:
    """Do text kitne milte hain (0.0 = alag, 1.0 = same). 0.8+ = near-duplicate."""
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


# Question type ke hisaab se "honest" marks — isse zyada marks 1-mark question pe
# = marks_mismatch. (recommend_marks ka ulta check.)
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
    """Layer 1 — LLM ke bina, deterministic checks. Instant + free + reliable.

    Ye woh problems pakadta hai jo **hamesha** problem hoti hain (kisi paper mein
    bhi, kisi bhi model ke saath). Inke liye LLM call karna paisa aur time
    dono barbaad karna hai.

    Return: `[{question_id, code, severity, message}, ...]`
    """
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

        # 1) khaali / adhoora question (batch fail hone pe aise hote hain)
        if not text.strip() or q.get("incomplete"):
            issues.append(
                {
                    "question_id": qid,
                    "code": "incomplete",
                    "severity": "high",
                    "message": "Question text khaali hai — ise regenerate karo.",
                }
            )

        # 2) answer missing → answer key adhoori
        if not answer.strip():
            issues.append(
                {
                    "question_id": qid,
                    "code": "missing_answer",
                    "severity": "high",
                    "message": "Expected answer nahi hai — answer key adhoori rahegi.",
                }
            )

        # 3)  ANSWER LEAK — question ke ANDAR hi answer likha ho
        #     ⚠️ BUG FIX (test ne pakda): pehle hum "MCQ ka option == answer"
        #     ko leak maan rahe the — jo GALAT hai. MCQ mein sahi jawab options
        #     mein hota hi hai, wahi to MCQ ki paribhasha hai! Us rule se har
        #     valid MCQ flag ho raha tha (false positive factory).
        #
        #     Asli leak: answer **question stem ke andar** khud likha hua ho
        #     ("Which organism Lactobacillus bacteria helps in making curd?").
        #     `len >= 12` ka matlab: chhote answers ("5", "Yes") par ye check
        #     lagta hi nahi — warna numeric answers pe jhoothe alarm aate.
        na = _norm(answer)
        if na and len(na) >= 12 and na in _norm(text):
            issues.append(
                {
                    "question_id": qid,
                    "code": "answer_leak",
                    "severity": "high",
                    "message": (
                        "Question ke andar hi answer likha hua hai — "
                        "question ko us tarah likho ki jawab chhupa rahe."
                    ),
                }
            )

        # 4) MCQ ke options — count, duplicates, aur key ka match
        if qtype in ("MCQ", "MultipleSelect"):
            if 0 < len(options) < 4:
                issues.append(
                    {
                        "question_id": qid,
                        "code": "weak_options",
                        "severity": "medium",
                        "message": f"{qtype} mein sirf {len(options)} options hain (4 expected).",
                    }
                )

            normed = [o for o in (_norm_option(opt) for opt in options) if o]

            if len(normed) != len(set(normed)):
                issues.append(
                    {
                        "question_id": qid,
                        "code": "duplicate_option",
                        "severity": "medium",
                        "message": "Do options ek jaise hain — ek ko badlo.",
                    }
                )

            # Key ka match: MCQ ka answer options mein se hi hona chahiye.
            # Model "A" / "Option B" bhi likh deta hai — us case ko chhod dete hain.
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
                                "Answer key kisi option se match nahi karta — "
                                "answer ya options theek karo."
                            ),
                        }
                    )

        # 5) duplicate — exact normalized match ya high token overlap
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
                        "message": f"Ye question {dup_of} jaisa hi hai — duplicate hatao.",
                    }
                )
            else:
                seen.append((qid, nt, tokens))

        # 6) chapter selected list se bahar
        if chapters and chapter and chapter not in chapters:
            issues.append(
                {
                    "question_id": qid,
                    "code": "off_chapter",
                    "severity": "medium",
                    "message": f"Chapter '{chapter}' selected chapters mein nahi hai.",
                }
            )

        # 7) marks vs difficulty honest hai?
        limit = MAX_HONEST_MARKS.get(qtype)
        if limit and marks > limit:
            issues.append(
                {
                    "question_id": qid,
                    "code": "marks_mismatch",
                    "severity": "medium",
                    "message": (
                        f"{qtype} ke liye {marks} marks zyada hai "
                        f"(usually max {limit}) — depth check karo."
                    ),
                }
            )
        if difficulty == "Hard" and marks <= 1:
            issues.append(
                {
                    "question_id": qid,
                    "code": "marks_mismatch",
                    "severity": "low",
                    "message": "Hard difficulty par 1 mark kam lagta hai.",
                }
            )

    return issues


# ------------------------------------------------------------
# QUALITY — Layer 2: LLM judge (semantic)
# ------------------------------------------------------------


class QualityIssue(BaseModel):
    """Judge ka ek issue.

    `code`/`severity` schema mein band hai, isliye model kuch bhi random nahi
    likh sakta (structured output ka asli faayda — prompt mein "please" kehne ki
    zaroorat nahi, schema hi deewar hai).
    """

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
    """Judge ka poora output."""

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
    """Judge ke issues ko filter karo — model ki 'shayad sach' wali baatein hatao.

    Production ka rule: LLM ka output **trust nahi, validate** karo. Judge kabhi
    kabhi aisa question_id de deta hai jo exist hi nahi karta, ya naya `code`
    invent kar deta hai. Aise issues teacher ke UI mein 'ghost problem' ban
    jaate hain — isliye yahan filter hai.
    """
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
    """Poora quality report — rules + (optional) LLM judge.

    `use_llm=False` ka matlab: sirf deterministic checks (instant). Ye flag
    production mein zaroori hai — agar judge model down hai to bhi Quality step
    khaali nahi dikhna chahiye, rules chalein.

    Return: `{issues, counts, verdict, source, llm_error, elapsed}`
    """
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

    # --- dedupe: same question + same code ek hi baar (rules aur judge overlap) ---
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


# ------------------------------------------------------------
# MARKS SUGGESTION — rules + optional LLM refine
# ------------------------------------------------------------

# Wahi base map jo `exams/service.py` (File 6) mein hai — yahan bhi chahiye
# kyunki llm layer service ko import nahi kar sakta (circular). File 17 mein
# service ise **delegate** karega (`suggest_marks`), tab duplicate hata jayega.
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
    """Teacher ke custom question ke liye marks suggestion.

    **Design decision (File 6 se continue):** default **rule-based** hai.
    Marks ek *contract* ka hissa hai (total_marks se juda hua) — usko
    non-deterministic AI par chhodna production mein theek nahi. Isliye:

      · rules  → hamesha same jawab, instant, free   (default)
      · LLM    → optional "second opinion", ±1 marks ke andar clamp

    `±1 clamp` ka matlab: judge model keh bhi de "8 marks", hum usse base se ek
    hi qadam door jaane dete hain. AI ko contract todne ka adhikaar nahi.

    `text_length` — jab caller ke paas **sirf length** ho (poora text nahi).
    Isse `exams/service.recommend_marks()` isi function ko delegate kar sakta
    hai, aur rules ki **copy do jagah nahi** rehti (single source of truth).
    """
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
    "generate_paper_questions",
    "part_b_marks",
    "plan_for_paper",
    "rule_checks",
    "suggest_marks",
]
