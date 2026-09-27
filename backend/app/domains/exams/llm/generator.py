

import json
import logging
import re
import time
from typing import Any

from pydantic import BaseModel, Field

from app.domains.exams.llm.base import get_llm
from app.domains.exams.llm.prompts import (
    MAX_SLOTS_PER_CALL,
    build_section_messages,
)

logger = logging.getLogger("eduverse.exams.llm.generator")


# ------------------------------------------------------------
# Output schema — model ko yahi shape bharni hai
# ------------------------------------------------------------
# Pydantic v2 ka `Field(description=...)` sirf docs ke liye nahi hota —
# tool-calling mein ye **JSON schema** ka hissa ban jaata hai, aur model
# usi description ko padh kar field samajhta hai. Isliye description
# English mein, saaf, aur "example ke saath" likho.


class GeneratedQuestion(BaseModel):
    """Ek question jo LLM ne banaya. Marks/type/slot se hum bharte hain."""

    text: str = Field(description="The question itself, without any numbering.")
    answer: str = Field(description="Expected answer, or key points for subjective.")
    options: list[str] = Field(
        default_factory=list,
        description="Options for MCQ/multiple-select. Empty list for other types.",
    )
    marking_scheme: str = Field(
        default="",
        description="One short line: how the marks are split for this answer.",
    )


class QuestionSet(BaseModel):
    """Ek batch ka output — `questions` array (slot plan ke same order mein)."""

    questions: list[GeneratedQuestion] = Field(
        description="One entry per slot in the slot plan, in the SAME order."
    )


# ------------------------------------------------------------
# Distribution helpers — deterministic rotation
# ------------------------------------------------------------

DIFFICULTIES = ["Easy", "Medium", "Hard"]
BLOOMS = ["Remember", "Understand", "Apply", "Analyze"]


def _rotate(allowed: list[str], index: int) -> str:
    """List ko cycle karo — `index` ke hisaab se (deterministic, random nahi)."""
    return allowed[index % len(allowed)] if allowed else "Medium"


def _expand_mix(
    categories: list[str], mix: list[int], total_slots: int = 20
) -> list[str]:
    """`[30, 50, 20]` + `['Easy','Medium','Hard']` → weighted cycle list.

    30/50/20 aur 20 slots → ~6 Easy, 10 Medium, 4 Hard — lekin **interleaved**.

    Interleave kyun? Agar seedha block banaye (Easy Easy Easy... Hard Hard Hard)
    to paper ka pehla hissa aasaan aur aakhir mushkil ho jaata — teachers ise
    "bura paper" kehte hain. Rotation se mix natural lagta hai.
    """
    if not mix or sum(mix) <= 0:
        return [categories[0]] * total_slots

    counts = [max(0, round(m * total_slots / sum(mix))) for m in mix]
    buckets = [
        [cat] * cnt for cat, cnt in zip(categories, counts, strict=False) if cnt > 0
    ]
    out: list[str] = []
    while any(buckets):
        for b in buckets:
            if b:
                out.append(b.pop())
    while len(out) < total_slots:
        out.append(categories[len(categories) // 2])  # fallback: Medium/Understand
    return out


def _chapter_sequence(coverage_plan: dict[str, Any], chapters: list[str]) -> list[str]:
    """Coverage plan se chapter-wise "quota list" banao — marks ke hisaab se.

    Misaal: Ch1=6 marks, Ch2=4 marks -> [Ch1 x6, Ch2 x4] (interleaved)

    Kyun aise? "AI ko chapter chunne do" ka matlab hai coverage se bhatakna.
    Hum quota banate hain, model sirf content likhta hai. Coverage plan khaali
    ho to chapters ko equally rotate karo.
    """
    plan_chapters = [
        c for c in (coverage_plan or {}).get("chapters", []) if c.get("chapter")
    ]

    if plan_chapters:
        weights = {
            c["chapter"]: max(1, int(c.get("targetMarks") or 0)) for c in plan_chapters
        }
        remaining = dict(weights)
        quota: list[str] = []
        budget = 60  # itna lamba quota kaafi hai; caller trim kar dega
        while len(quota) < budget and any(v > 0 for v in remaining.values()):
            for ch in weights:
                if remaining.get(ch, 0) > 0 and len(quota) < budget:
                    quota.append(ch)
                    remaining[ch] -= 1
        return quota

    if not chapters:
        return []
    return [chapters[i % len(chapters)] for i in range(60)]


def _topic_for(chapter: str, coverage_plan: dict[str, Any], index: int) -> str:
    """Chapter ke andar topic — coverage plan ke topics se rotate karo."""
    for c in (coverage_plan or {}).get("chapters", []):
        if c.get("chapter") == chapter:
            topics = [t.get("topic") for t in c.get("topics", []) if t.get("topic")]
            if topics:
                return topics[index % len(topics)]
    return ""


# ------------------------------------------------------------
# ⭐ THE SLOT PLAN — blueprint + budget → khaali slots
# ------------------------------------------------------------


def build_question_plan(
    *,
    blueprint: list[dict[str, Any]],
    ai_budget: int,
    coverage_plan: dict[str, Any] | None = None,
    chapters: list[str] | None = None,
    difficulty_mix: list[int] | None = None,
    bloom_mix: list[int] | None = None,
) -> dict[str, Any]:
    """Blueprint ko expand karke slots banao, phir `ai_budget` mein fit karo.

    **Ye Decision #1 ka implementation hai** (blueprint §2.3.3):
        blueprint total   = 30 marks  (teacher ne plan kiya)
        part_b (teacher)  =  7 marks  (2 custom questions)
        ai_budget         = 23 marks  <-- AI ko SIRF itna banana hai
        blueprint expand  = 30 marks ke slots
        trim              = aakhir se 7 marks ke slots hatao (last section pehle)

    Trim aakhir se kyun? Kyunki blueprint ka **order** paper ka order hai
    (MCQ → Short → Long). Beech se haato to paper ka dhancha ajeeb lagta hai.
    Aakhir se kaatna = "poora paper rehta hai, bas chhota hota hai".

    **Gap fill (Step 2b)** — trim ka ulta problem: 22 - 8 = 14, par budget 15.
    Tab hum **sabse saste type** ke slots add karte hain (1-mark MCQ) taaki
    final_marks **exactly** ai_budget ho. Warna Marks Contract toot jata
    (14 + 7 = 21 != 22). Gap saste question se bhi chhota ho to aakhri slot ke
    marks bada dete hain (`gap_bumped` mein report hota hai).

    Invariant: `balanced == True` matlab `final_marks == ai_budget`.

    Return: `{slots, planned_marks, final_marks, ai_budget, trimmed, trimmed_marks,
              gap_filled, gap_bumped, by_section, balanced}`
    """
    allowed_d = _expand_mix(DIFFICULTIES, difficulty_mix or [30, 50, 20])
    allowed_b = _expand_mix(BLOOMS, bloom_mix or [20, 40, 30, 10])
    chapter_seq = _chapter_sequence(coverage_plan or {}, chapters or [])

    # ---- Step 1: poora expand (blueprint ke order mein) ----
    slots: list[dict[str, Any]] = []
    n = 0
    for section in blueprint or []:
        qtype = str(section.get("type") or "").strip()
        count = max(0, int(section.get("count") or 0))
        marks_each = int(section.get("marksEach") or section.get("marks_each") or 0)
        has_image = bool(section.get("hasImage") or section.get("has_image"))
        for _ in range(count):
            chapter = chapter_seq[n] if n < len(chapter_seq) else ""
            slots.append(
                {
                    "slot_id": f"Q{n + 1}",
                    "type": qtype,
                    "marks": marks_each,
                    "difficulty": _rotate(allowed_d, n),
                    "bloom": _rotate(allowed_b, n),
                    "chapter": chapter,
                    "topic": _topic_for(chapter, coverage_plan or {}, n),
                    "has_image": has_image,
                    "origin": "ai",
                }
            )
            n += 1

    planned_marks = sum(s["marks"] for s in slots)

    # ---- Step 2: budget ke hisaab se trim (aakhir se) ----
    trimmed: list[dict[str, Any]] = []
    while slots and sum(s["marks"] for s in slots) > max(0, ai_budget):
        trimmed.insert(0, slots.pop())

    # ---- Step 2b: GAP FILL (trim ka ulta problem) ----
    # Trim kabhi-kabhi budget se **kam** reh jata hai, kyunki question ke marks
    # fixed hote hain: 22 - 8 (do Long) = 14, par budget 15. Gap = 1 mark.
    #
    # Aur ye Marks Contract tod deta hai:
    #     part_a 14 + part_b 7 = 21  !=  total_marks 22   ❌
    #
    # Isliye 2-step fill:
    #   1. Sabse **sasta** section dhoondho (min marksEach) aur uske slots add karo
    #      (jaise 1-mark MCQ se gap bharna — blueprint ka dhancha todne se behtar)
    #   2. Agar gap saste question se bhi chhota ho (gap < cheapest), aakhri slot
    #      ke marks bada do (absorb). Report mein `bumped` flag se pata chalega.
    #
    # Isse invariant guarantee hoti hai: final_marks == ai_budget (jab ai_budget > 0)
    gap = max(0, ai_budget - sum(s["marks"] for s in slots))
    added_ids: list[str] = []
    bumped: list[str] = []

    if gap > 0:
        sections = [s for s in (blueprint or []) if int(s.get("count") or 0) > 0]
        candidates = [
            (
                str(s.get("type") or "").strip(),
                int(s.get("marksEach") or s.get("marks_each") or 0),
            )
            for s in sections
        ]
        candidates = [(t, m) for t, m in candidates if t and m > 0]

        if candidates:
            cheap_type, cheap_marks = min(candidates, key=lambda x: x[1])
            while gap >= cheap_marks:
                n += 1
                slots.append(
                    {
                        "slot_id": f"Q{n}",
                        "type": cheap_type,
                        "marks": cheap_marks,
                        "difficulty": _rotate(allowed_d, n - 1),
                        "bloom": _rotate(allowed_b, n - 1),
                        "chapter": chapter_seq[(n - 1) % len(chapter_seq)]
                        if chapter_seq
                        else "",
                        "topic": _topic_for(
                            chapter_seq[(n - 1) % len(chapter_seq)]
                            if chapter_seq
                            else "",
                            coverage_plan or {},
                            n - 1,
                        ),
                        "has_image": False,
                        "origin": "ai",
                        "gap_fill": True,
                    }
                )
                added_ids.append(f"Q{n}")
                gap -= cheap_marks

        if gap > 0 and slots:
            slots[-1]["marks"] += gap
            bumped.append(slots[-1]["slot_id"])
            gap = 0

    final_marks = sum(s["marks"] for s in slots)

    # ---- Step 3: section summary (Review dashboard ke liye) ----
    by_section: dict[str, dict[str, int]] = {}
    for s in slots:
        entry = by_section.setdefault(s["type"], {"count": 0, "marks": 0})
        entry["count"] += 1
        entry["marks"] += s["marks"]

    report: dict[str, Any] = {
        "slots": slots,
        "planned_marks": planned_marks,
        "final_marks": final_marks,
        "ai_budget": ai_budget,
        "trimmed": [s["slot_id"] for s in trimmed],
        "trimmed_marks": planned_marks - final_marks,
        "gap_filled": added_ids,
        "gap_bumped": bumped,
        "by_section": by_section,
        "balanced": final_marks == ai_budget,
    }

    logger.info(
        "slot plan: blueprint=%s marks -> %s slots | trimmed=%s (%s) | gap_filled=%s | "
        "final=%s / ai_budget=%s | balanced=%s",
        planned_marks,
        len(slots),
        report["trimmed_marks"],
        ",".join(report["trimmed"]) or "-",
        ",".join(added_ids) or "-",
        final_marks,
        ai_budget,
        report["balanced"],
    )
    return report


# ------------------------------------------------------------
# JSON extraction — Plan-B ka dil
# ------------------------------------------------------------

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def extract_json(text: str) -> dict[str, Any] | None:
    """LLM ke text se JSON nikaalo — chhote models ke liye zaroori.

    Real duniya mein model ye sab kar deta hai (chahe bolo "only JSON"):
      1. ```json ... ``` fence mein lapet deta hai
      2. "Sure! Here are your questions:" preamble
      3. aakhir mein "Let me know if you want more!" suffix
      4. trailing comma, single quotes

    Isliye: fence hatao -> pehla `{` se aakhir `}` tak ka hissa lo -> parse karo.
    Ye "best-effort" hai; fail ho to None (aur caller retry karega).
    """
    if not text:
        return None

    candidate = text.strip()

    fence = _FENCE_RE.search(candidate)
    if fence:
        candidate = fence.group(1).strip()

    start = candidate.find("{")
    end = candidate.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    candidate = candidate[start : end + 1]

    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as exc:
        logger.warning("json extract fail: %s | first 200: %s", exc, candidate[:200])
        return None
    return parsed if isinstance(parsed, dict) else None


# ------------------------------------------------------------
# Ek batch generate karo
# ------------------------------------------------------------


def generate_section(
    *,
    qtype: str,
    ctx: dict[str, Any],
    slots: list[dict[str, Any]],
    sources: list[dict[str, Any]] | None = None,
    excerpts: list[str] | None = None,
    constraints: dict[str, Any] | None = None,
    instructions: list[str] | None = None,
    used: list[str] | None = None,
    llm: Any = None,
    max_attempts: int = 2,
) -> list[dict[str, Any]]:
    """Ek batch (same type ke slots) ke questions banao.

    Do raaste (production mein dono zaroori):
      ATTEMPT 1 — `with_structured_output`: schema-enforced JSON (safe)
      ATTEMPT 2 — plain invoke + `extract_json` (Plan-B: chhote local models)

    Return: list of question dicts, slot fields **merged**
            (marks/type/chapter hum dete hain, model sirf content deta hai).
    """
    if not slots:
        return []

    messages = build_section_messages(
        qtype=qtype,
        ctx=ctx,
        slots=slots,
        sources=sources,
        excerpts=excerpts,
        constraints=constraints,
        instructions=instructions,
        used=used,
    )
    client = llm or get_llm()
    last_error: str | None = None

    for attempt in range(1, max_attempts + 1):
        t0 = time.time()
        try:
            if attempt == 1:
                structured = client.with_structured_output(QuestionSet)
                result = structured.invoke(messages)
                raw_questions = [
                    q.model_dump() if isinstance(q, BaseModel) else dict(q)
                    for q in (result.questions if result else [])
                ]
                mode = "structured"
            else:
                resp = client.invoke(messages)
                data = extract_json(getattr(resp, "content", "") or "")
                raw_questions = list((data or {}).get("questions", []))
                mode = "json-fallback"

            elapsed = round(time.time() - t0, 1)

            if not raw_questions:
                last_error = f"attempt {attempt} ({mode}): empty questions"
                logger.warning("section %s: %s", qtype, last_error)
                continue

            merged = _merge_slots(slots, raw_questions)
            logger.info(
                "section %s: %s questions via %s in %ss",
                qtype,
                len(merged),
                mode,
                elapsed,
            )
            return merged

        except Exception as exc:
            last_error = f"attempt {attempt}: {type(exc).__name__}: {exc}"
            logger.warning("section %s failed: %s", qtype, last_error)

    logger.error("section %s: sab attempts fail (%s)", qtype, last_error)
    return []


def _merge_slots(
    slots: list[dict[str, Any]], raw: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Model ka content + humara slot = final question.

    **Ye line Marks Contract ki guarantee hai:** `marks`, `type`, `chapter`,
    `topic` hum **slot se** lete hain — model se nahi. Model ke output mein
    marks bhale kuch bhi ho, hum use ignore karte hain.

    Agar model ne kam questions diye: baaki slots "incomplete" flag ke saath
    aayenge — taaki teacher ko dikhe ki kaun sa question adhoora raha
    (silent drop nahi, production mein ye farq bahut matter karta hai).
    """
    out: list[dict[str, Any]] = []
    for i, slot in enumerate(slots):
        raw_q = raw[i] if i < len(raw) else {}
        question = {
            "id": slot["slot_id"].lower(),  # q1, q2 ...
            "type": slot["type"],
            "marks": slot["marks"],  # <<< slot se, model se NAHI
            "difficulty": slot["difficulty"],
            "bloom": slot["bloom"],
            "chapter": slot["chapter"],
            "topic": slot["topic"],
            "hasImage": slot.get("has_image", False),
            "origin": "ai",
            # Every generated question starts LOCKED. Changing a question (edit,
            # regenerate, or replacing it with your own) requires an explicit
            # unlock first — that is what makes a regeneration touch only the
            # questions the teacher deliberately opened up.
            "locked": True,
            "text": str(raw_q.get("text") or "").strip(),
            "answer": str(raw_q.get("answer") or "").strip(),
            "options": list(raw_q.get("options") or []),
            "markingScheme": str(raw_q.get("marking_scheme") or "").strip(),
            "sourceRefs": [],
        }
        if not question["text"]:
            question["incomplete"] = True
        out.append(question)
    return out


# ------------------------------------------------------------
# Poora paper — section-wise + batches + progress
# ------------------------------------------------------------


def generate_all(
    *,
    plan: dict[str, Any],
    ctx: dict[str, Any],
    sources: list[dict[str, Any]] | None = None,
    excerpts: list[str] | None = None,
    constraints: dict[str, Any] | None = None,
    instructions: list[str] | None = None,
    used: list[str] | None = None,
    llm: Any = None,
    progress: Any = None,
    batch_size: int = MAX_SLOTS_PER_CALL,
) -> dict[str, Any]:
    """Slot plan ke saare slots bharo — section-wise, chhote batches mein.

    `progress` ek callback hai: `progress(stage: str, pct: int, extra: dict|None)`.
    Service layer ise job ke `stages` mein save karta hai, aur frontend usko
    poll karke progress bar dikhata hai. Isliye generator ko HTTP/DB ka pata
    nahi hona chahiye — sirf "batao kahan pahunche" (separation of concerns).

    Kyun section-wise? (blueprint §2.5)
      · Har type ka prompt alag (MCQ ko 4 options, Long ko structure)
      · Ek bada call = bad JSON risk + timeout
      · Batch chhota = fail hone pe sirf woh batch dobara (poora paper nahi)

    Return: `{questions, generated, expected, marks, elapsed, failed_batches}`
    """
    slots: list[dict[str, Any]] = list(plan.get("slots") or [])
    total_slots = len(slots)
    if not total_slots:
        return {
            "questions": [],
            "generated": 0,
            "expected": 0,
            "marks": 0,
            "elapsed": 0.0,
            "failed_batches": [],
        }

    # Slots ko type ke hisaab se group karo, **order barqarar rakhte hue**
    # (blueprint ka order = paper ka order: MCQ pehle, phir Short, phir Long)
    order: list[str] = []
    by_type: dict[str, list[dict[str, Any]]] = {}
    for s in slots:
        if s["type"] not in by_type:
            order.append(s["type"])
            by_type[s["type"]] = []
        by_type[s["type"]].append(s)

    questions: list[dict[str, Any]] = []
    failed_batches: list[str] = []
    done_slots = 0
    t_start = time.time()

    for qtype in order:
        type_slots = by_type[qtype]
        for start in range(0, len(type_slots), batch_size):
            batch = type_slots[start : start + batch_size]
            label = f"{qtype} {start + 1}-{start + len(batch)}"

            if progress:
                pct = int(done_slots / total_slots * 100)
                progress(
                    f"Writing {label}...",
                    pct,
                    {"batch": label, "done": done_slots, "total": total_slots},
                )

            produced = generate_section(
                qtype=qtype,
                ctx=ctx,
                slots=batch,
                sources=sources,
                excerpts=excerpts,
                constraints=constraints,
                instructions=instructions,
                used=[q["text"] for q in questions if q.get("text")] or used,
                llm=llm,
            )

            if not produced:
                failed_batches.append(label)
                # Batch fail hone pe bhi slots "incomplete" ke saath add karo —
                # teacher ko dikhe ki kahan khaali jagah hai.
                questions.extend(_merge_slots(batch, []))

            else:
                questions.extend(produced)

            done_slots += len(batch)

    elapsed = round(time.time() - t_start, 1)
    generated = sum(1 for q in questions if q.get("text"))
    marks = sum(int(q.get("marks") or 0) for q in questions)

    if progress:
        progress(
            f"Generated {generated}/{total_slots} questions",
            100,
            {"generated": generated, "total": total_slots},
        )

    logger.info(
        "generate_all: %s/%s questions | %s marks | %ss | failed batches=%s",
        generated,
        total_slots,
        marks,
        elapsed,
        failed_batches or "none",
    )

    return {
        "questions": questions,
        "generated": generated,
        "expected": total_slots,
        "marks": marks,
        "elapsed": elapsed,
        "failed_batches": failed_batches,
    }
