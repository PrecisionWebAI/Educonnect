# ============================================================
# llm/graph.py — LangGraph DAG: paper generation ka **asli flow** (blueprint §2.5).
#
# ------------------------------------------------------------
# Pehle kya tha, ab kya hai?
# ------------------------------------------------------------
# Pehle: `services.generate_paper_questions()` ek seedha function tha —
#        plan → loop over batches → generate → summary. Kaam karta tha, par
#        flow **code ke andar chhupa** hua tha (nodes/dekhne layak nahi).
# Ab   : wahi kaam ek **graph** (state machine) hai:
#
#     START → plan → guard ─┬─(slots khaali)─────────────→ finalize → END
#                           └─ retrieve → batches → ⚡fan-out per section⚡
#                                       → merge → check ─┬─(incomplete)─→ repair ─→ check
#                                                        └─ judge → finalize → END
#
# ------------------------------------------------------------
# ⭐ Kyun graph (aur ye kaun si asli production problem solve karta hai)
# ------------------------------------------------------------
#   1. **Parallel section generation** — MCQ aur Short ek saath ban sakte hain
#      (`Send` fan-out). Local model par bhi ye wall-clock time girata hai.
#   2. **Bounded repair loop** — conditional edge se "khaali question bacha hai" →
#      wapas generate (max `repair_passes`). Infinite loop ka rasta hi nahi.
#   3. **Node-level visibility** — `graph.stream(stream_mode="updates")` se har
#      node ka event milta hai, jo hum `GenerationJob.graph_state` mein likh dete
#      hain → job restart hone par pata chalta hai kahan tak hua tha
#      (yehi "checkpoint" hai, bina kisi extra service ke).
#   4. **DAG code mein dikhta hai** — naya step (jaise image lookup ya human gate)
#      add karna = ek node + ek edge, poori function ko chhedna nahi.
#
# ⚠️ Ye file **DB ko chhooti nahi** (wahi layer rule): progress/checkpoint ek
# callback (`on_event`) se bahar jaata hai — DB likhna `exams/service.py` ka kaam.
# ============================================================

import logging
import operator
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from app.core.config import settings
from app.domains.exams.llm.generator import (
    _merge_slots,
    generate_section,
)
from app.domains.exams.llm.services import (
    _build_summary,
    build_ctx,
    build_sources,
    check_quality,
    coverage_report,
    plan_for_paper,
    repair_incomplete,
    rule_checks,
)

logger = logging.getLogger("eduverse.exams.llm.graph")


# ------------------------------------------------------------
# STATE — graph ka "shared whiteboard"
# ------------------------------------------------------------
# ⚠️ Reducer (`Annotated[list, operator.add]`) wale keys par **sirf naya maal**
# return karo. Purani list dobara return karne se duplicate ho jaata hai
# (`operator.add` use jod deta hai) — ye classic LangGraph trap hai, isliye
# yahan har key ka role likha hua hai:
#   · produced / batch_labels / failed / warnings → REDUCER (append-only)
#   · baaki sab → scalar (last write wins)


class PaperState(TypedDict, total=False):
    # ---- input (frozen: job snapshot se aata hai) ----
    paper: Any
    blueprint: Any
    coverage_plan: Any
    total_marks: int | None
    used: list[str]  # anti-repeat: pehle use ho chuke questions
    repair_passes: int
    batch_size: int
    use_judge: bool
    # Source index validation (DB se service banati hai, graph sirf report karta
    # hai): {selected, indexed, pending[], failed[], missing[], note}. Graph DB ko
    # chhoota nahi — isliye ye **data** ke roop mein andar aata hai.
    source_index: dict[str, Any]

    # ---- reducer keys (append-only) ----
    produced: Annotated[list[list[dict[str, Any]]], operator.add]
    batch_labels: Annotated[list[str], operator.add]
    failed_batches: Annotated[list[str], operator.add]
    warnings: Annotated[list[str], operator.add]
    repaired: Annotated[list[str], operator.add]

    # ---- runtime scalars ----
    batch: dict[str, Any]  # fan-out (`Send`) ka per-batch payload
    ctx: dict[str, Any]
    plan: dict[str, Any]
    sources: list[dict[str, Any]]
    excerpts: list[str]
    batches: list[dict[str, Any]]
    questions: list[dict[str, Any]]
    broken: list[dict[str, Any]]
    issues: list[dict[str, Any]]
    quality: dict[str, Any]
    coverage: list[dict[str, Any]]  # output: coverage ROWS (input = coverage_plan)
    repair_count: int
    summary: dict[str, Any]


def _batch_label(batch: dict[str, Any]) -> str:
    """`"MCQ 1-8"` jaisa label — progress UI mein insaani-readable."""
    return str(batch.get("label") or batch.get("type") or "batch")


# ------------------------------------------------------------
# Graph builder
# ------------------------------------------------------------


def build_paper_graph(on_event: Any = None, llm: Any = None):
    """Paper-generation graph banao (compiled).

    `on_event(event: dict)` — har node ek chhota event bhejta hai:
    `{"node": "generate", "stage": "Writing MCQ 1-8...", "pct": 42}`.
    Service isse DB (`job.stages` + `job.graph_state`) mein likhta hai — isliye
    ye file DB se azaad rehti hai (aur tests mein callback capture kar lete hain).

    `llm` — tests ke liye inject (fake model). Production mein None = real client.
    """

    def emit(node: str, **extra: Any) -> None:
        if callable(on_event):
            on_event({"node": node, **extra})

    # ---- Node 1: PLAN (blueprint + budget → slots) ----
    def node_plan(state: PaperState) -> dict[str, Any]:
        paper = state["paper"]
        total_marks = state.get("total_marks")
        ctx = build_ctx(paper, total_marks=total_marks)
        plan = plan_for_paper(
            paper,
            blueprint=state.get("blueprint"),
            coverage=state.get("coverage_plan"),
            total_marks=total_marks,
        )
        slots = plan.get("slots") or []
        emit("plan", stage="Planning questions...", pct=2, total=len(slots))
        logger.info(
            "graph.plan: %s slots | ai_budget=%s", len(slots), plan.get("ai_budget")
        )
        return {"ctx": ctx, "plan": plan}

    # ---- Node 2: GUARD (kuch banane layak hai?) ----
    def node_guard(state: PaperState) -> dict[str, Any]:
        plan = state.get("plan") or {}
        if plan.get("slots"):
            return {}
        # Khaali plan ka matlab: budget 0 ya blueprint khaali. Yahan saaf wajah
        # banate hain — service ise job result mein daalta hai (silent empty nahi).
        budget = int(plan.get("ai_budget") or 0)
        note = (
            "AI ke liye 0 marks bache — teacher ke custom questions (part_b) ne poora "
            "total_marks kha liya. Custom questions ke marks kam karo ya total_marks "
            "badhao, phir generate karo."
            if budget <= 0
            else "Plan se koi slot nahi bana — blueprint ke count/marksEach check karo."
        )
        emit("guard", stage=note, pct=100)
        logger.warning("graph.guard: koi slot nahi (budget=%s)", budget)
        return {"warnings": [note]}

    # ---- Node 3: RETRIEVE (RAG context pack) ----
    def node_retrieve(state: PaperState) -> dict[str, Any]:
        paper = state["paper"]
        emit("retrieve", stage="Retrieving source content...", pct=5)
        sources, excerpts = build_sources(paper, plan=state.get("plan"))
        logger.info(
            "graph.retrieve: %s sources | %s excerpts", len(sources), len(excerpts)
        )
        return {"sources": sources, "excerpts": excerpts}

    # ---- Node 4: PREPARE BATCHES (type-wise grouping) ----
    def node_batches(state: PaperState) -> dict[str, Any]:
        slots: list[dict[str, Any]] = list((state.get("plan") or {}).get("slots") or [])
        size = max(1, int(state.get("batch_size") or 8))

        # Order preserve (blueprint ka order = paper ka order)
        order: list[str] = []
        by_type: dict[str, list[dict[str, Any]]] = {}
        for slot in slots:
            qtype = str(slot.get("type") or "Short")
            if qtype not in by_type:
                order.append(qtype)
                by_type[qtype] = []
            by_type[qtype].append(slot)

        batches: list[dict[str, Any]] = []
        index = 0
        for qtype in order:
            type_slots = by_type[qtype]
            for start in range(0, len(type_slots), size):
                chunk = type_slots[start : start + size]
                batches.append(
                    {
                        "index": index,
                        "type": qtype,
                        "slots": chunk,
                        "label": f"{qtype} {start + 1}-{start + len(chunk)}",
                    }
                )
                index += 1

        emit("batches", stage=f"Preparing {len(batches)} batches...", pct=8)
        return {"batches": batches}

    def fan_out(state: PaperState) -> list[Send]:
        """Har batch ko `generate` node par bhej — **parallel** fan-out.

        ⚠️ `Send` ka payload us node ka state hota hai, isliye jo cheezein
        `generate` ko chahiye (ctx/sources/excerpts/used) woh **explicitly**
        bhej rahe hain. Warna parallel branch mein ye keys gayab ho jaati hain
        aur prompt bina class/subject ke ban jaata hai (classic fan-out bug).
        """
        shared = {
            "ctx": state.get("ctx") or {},
            "sources": state.get("sources") or [],
            "excerpts": state.get("excerpts") or [],
            "used": state.get("used") or [],
        }
        return [
            Send("generate", {**shared, "batch": batch})
            for batch in state.get("batches") or []
        ]

    # ---- Node 5: GENERATE (ek batch — fan-out se multiple instances) ----
    def node_generate(state: PaperState) -> dict[str, Any]:
        batch = state.get("batch") or {}
        slots = list(batch.get("slots") or [])
        label = _batch_label(batch)
        emit(
            "generate",
            stage=f"Writing {label}...",
            pct=10 + int(batch.get("index") or 0),
        )

        produced = generate_section(
            qtype=str(batch.get("type") or "Short"),
            ctx=state.get("ctx") or {},
            slots=slots,
            sources=state.get("sources"),
            excerpts=state.get("excerpts"),
            constraints=(state.get("ctx") or {}).get("constraints"),
            instructions=(state.get("ctx") or {}).get("instructions"),
            used=state.get("used"),
            llm=llm,
        )
        if not produced:
            # Batch fail → khaali slots "incomplete" ke saath rakho, taaki repair
            # node unhe pakad sake (silent drop nahi).
            logger.warning("graph.generate: batch '%s' fail (empty output)", label)
            return {
                "produced": [
                    [
                        {**q, "batch_index": batch.get("index")}
                        for q in _merge_slots(slots, [])
                    ]
                ],
                "batch_labels": [label],
                "failed_batches": [label],
            }

        return {
            "produced": [[{**q, "batch_index": batch.get("index")} for q in produced]],
            "batch_labels": [label],
        }

    # ---- Node 6: MERGE (fan-in → ordered question list) ----
    def node_merge(state: PaperState) -> dict[str, Any]:
        produced = state.get("produced") or []
        # Fan-out ka order guaranteed nahi hai → `batch_index` se sort karke
        # blueprint ka order wapas banaate hain (paper mein wahi order chahiye).
        ordered = sorted(
            (batch for batch in produced if batch),
            key=lambda batch: int(((batch or [{}])[0] or {}).get("batch_index") or 0),
        )
        questions = [q for batch in ordered for q in batch]
        for q in questions:
            q.pop("batch_index", None)
        emit("merge", stage=f"Merged {len(questions)} questions", pct=70)
        logger.info("graph.merge: %s questions", len(questions))
        return {"questions": questions}

    # ---- Node 7: CHECK (rules + coverage + broken list) ----
    def node_check(state: PaperState) -> dict[str, Any]:
        questions = list(state.get("questions") or [])
        ctx = state.get("ctx") or {}
        coverage_plan = state.get("coverage_plan") or {}

        broken = [
            q
            for q in questions
            if q.get("incomplete") or not str(q.get("text") or "").strip()
        ]
        issues = rule_checks(questions, coverage_plan=coverage_plan, ctx=ctx)
        coverage_rows = coverage_report(coverage_plan, questions)
        emit(
            "check",
            stage=f"Checking quality ({len(broken)} incomplete)",
            pct=80,
            issues=len(issues),
        )
        return {"broken": broken, "issues": issues, "coverage": coverage_rows}

    def route_after_check(state: PaperState) -> str:
        """Repair karein ya aage badhein? (bounded — `repair_count` gate)."""
        broken = state.get("broken") or []
        used_passes = int(state.get("repair_count") or 0)
        allowed = int(state.get("repair_passes") or 0)
        if broken and used_passes < allowed:
            return "repair"
        return "judge" if state.get("use_judge") else "finalize"

    # ---- Node 8: REPAIR (sirf khaali slots, bounded) ----
    def node_repair(state: PaperState) -> dict[str, Any]:
        count = int(state.get("repair_count") or 0) + 1
        emit("repair", stage=f"Repairing incomplete questions (pass {count})", pct=85)
        questions, repaired = repair_incomplete(
            questions=list(state.get("questions") or []),
            ctx=state.get("ctx") or {},
            sources=state.get("sources"),
            excerpts=state.get("excerpts"),
            constraints=(state.get("ctx") or {}).get("constraints"),
            instructions=(state.get("ctx") or {}).get("instructions"),
            llm=llm,
            passes=1,  # ek pass per graph loop — `repair_passes` se bounded
        )
        logger.info("graph.repair: %s question(s) dobara bane", len(repaired))
        return {"questions": questions, "repaired": repaired, "repair_count": count}

    # ---- Node 9: JUDGE (LLM quality check — optional, flag se on/off) ----
    def node_judge(state: PaperState) -> dict[str, Any]:
        emit("judge", stage="Running AI quality check...", pct=92)
        report = check_quality(
            list(state.get("questions") or []),
            ctx=state.get("ctx") or {},
            coverage_plan=state.get("coverage_plan") or {},
            use_llm=True,
            llm=llm,
        )
        logger.info("graph.judge: verdict=%s", report.get("verdict"))
        return {"quality": report}

    # ---- Node 10: FINALIZE (summary + Marks Contract audit) ----
    def node_finalize(state: PaperState) -> dict[str, Any]:
        plan = state.get("plan") or {}
        questions = list(state.get("questions") or [])
        # ⚠️ Marks Contract honest rakho: khaali/incomplete question ke marks
        # "generate ho gaye" nahi maane jaate. Warna finalize gate aise paper
        # ko paas kar deta jisme aadhe question khaali hain (silent pass).
        filled: list[dict[str, Any]] = []
        incomplete: list[dict[str, Any]] = []
        for q in questions:
            if str(q.get("text") or "").strip() and not q.get("incomplete"):
                filled.append(q)
            else:
                incomplete.append(q)
        result = {
            "questions": questions,
            "generated": len(filled),
            "expected": len(plan.get("slots") or []),
            "marks": sum(int(q.get("marks") or 0) for q in filled),
            "elapsed": 0.0,
            "failed_batches": list(state.get("failed_batches") or []),
        }
        summary = _build_summary(plan, state["paper"], result)
        summary["incomplete_marks"] = sum(int(q.get("marks") or 0) for q in incomplete)
        summary["repaired"] = list(state.get("repaired") or [])
        summary["repaired_count"] = len(state.get("repaired") or [])
        summary["incomplete"] = [
            str(q.get("id") or "?")
            for q in questions
            if str(q.get("text") or "").strip() == "" or q.get("incomplete")
        ]
        summary["issues"] = list(state.get("issues") or [])
        summary["coverage"] = list(state.get("coverage") or [])
        summary["quality"] = state.get("quality") or {}
        summary["warnings"] = list(state.get("warnings") or [])
        # ---- Source index validation report (Validator ka ek hissa) ----
        # Kitne selected sources indeed indexed the? Jo indexed nahi, unka
        # content retrieval mein nahi aaya — isliye ye baat summary mein aur
        # (agar kuch pending/failed hai to) warnings mein bhi jaati hai. UI isse
        # teacher ko dikhata hai ("is source ne contribute nahi kiya").
        source_index = state.get("source_index") or {}
        if source_index:
            summary["source_index"] = source_index
            if source_index.get("note"):
                summary["warnings"] = [
                    *summary["warnings"],
                    str(source_index["note"]),
                ]
        if not questions and state.get("warnings"):
            summary["note"] = state["warnings"][0]
        emit("finalize", stage="Finalising paper", pct=98)
        logger.info(
            "graph.finalize: %s/%s questions | %s marks | contract_ok=%s",
            summary.get("question_count"),
            summary.get("expected_count"),
            summary.get("marks_total"),
            (summary.get("contract") or {}).get("ok"),
        )
        return {"summary": summary, "questions": questions}

    # ---- Graph wiring (DAG banta hua saaf dikhta hai) ----
    builder = StateGraph(PaperState)
    builder.add_node("plan", node_plan)
    builder.add_node("guard", node_guard)
    builder.add_node("retrieve", node_retrieve)
    builder.add_node("batches", node_batches)
    builder.add_node("generate", node_generate)
    builder.add_node("merge", node_merge)
    builder.add_node("check", node_check)
    builder.add_node("repair", node_repair)
    builder.add_node("judge", node_judge)
    builder.add_node("finalize", node_finalize)

    builder.add_edge(START, "plan")
    builder.add_edge("plan", "guard")
    builder.add_conditional_edges(
        "guard",
        lambda s: "retrieve" if (s.get("plan") or {}).get("slots") else "finalize",
        ["retrieve", "finalize"],
    )
    builder.add_edge("retrieve", "batches")
    builder.add_conditional_edges("batches", fan_out, ["generate"])
    builder.add_edge("generate", "merge")
    builder.add_edge("merge", "check")
    builder.add_conditional_edges(
        "check", route_after_check, ["repair", "judge", "finalize"]
    )
    builder.add_edge("repair", "check")  # loop (repair_count se bounded)
    builder.add_edge("judge", "finalize")
    builder.add_edge("finalize", END)

    return builder.compile()


# ------------------------------------------------------------
# Public API — service isi ko bulata hai
# ------------------------------------------------------------


def run_paper_graph(
    *,
    paper: Any,
    blueprint: Any = None,
    coverage_plan: Any = None,
    total_marks: int | None = None,
    used: list[str] | None = None,
    repair_passes: int | None = None,
    batch_size: int | None = None,
    use_judge: bool | None = None,
    on_event: Any = None,
    llm: Any = None,
    on_checkpoint: Any = None,
    source_index: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Graph chalao aur **final state** wapas do (`summary` + `questions` andar).

    `on_event`     — progress events (service DB mein likhta hai).
    `on_checkpoint`— har node ke baad `(node_name, state)` — yehi LangGraph-style
                     checkpoint hai jo `GenerationJob.graph_state` mein jaata hai
                     (server restart ke baad pata chale kahan tak pahunche the).
    `source_index` — service ka source-index validation report (selected sources
                     indexed hain ya nahi). Ye graph mein **data** ke roop mein
                     aata hai, kyunki graph DB ko nahi chhoota.

    `graph.stream(stream_mode="updates")` use karte hain (na ki `invoke`), kyunki
    humein **node-by-node** visibility chahiye — progress bar aur checkpoint dono
    isi se bante hain.
    """
    graph = build_paper_graph(on_event=on_event, llm=llm)
    initial: PaperState = {
        "paper": paper,
        "blueprint": blueprint,
        "coverage_plan": coverage_plan if isinstance(coverage_plan, dict) else {},
        "total_marks": total_marks,
        "used": list(used or []),
        "repair_passes": (
            settings.EXAMS_REPAIR_PASSES if repair_passes is None else repair_passes
        ),
        "batch_size": batch_size or 8,
        "use_judge": settings.EXAMS_USE_LLM_JUDGE if use_judge is None else use_judge,
        "repair_count": 0,
        "source_index": dict(source_index or {}),
    }

    final_state: dict[str, Any] = dict(initial)
    done_nodes: list[str] = []

    # ⚠️ LangGraph ka default `recursion_limit` 25 hai — bade paper (bahut se
    # batches) aur repair loop mein wo kam pad jaata hai (`GraphRecursionError`,
    # jo production mein "aadha paper" ban ke aata). Graph khud bounded hai
    # (`repair_count <= repair_passes`), isliye limit aaram se badha dete hain.
    config = {"recursion_limit": 100}

    for update in graph.stream(initial, config, stream_mode="updates"):
        for node_name, patch in (update or {}).items():
            done_nodes.append(node_name)
            if isinstance(patch, dict):
                final_state.update(patch)
            if callable(on_checkpoint):
                on_checkpoint(node_name, done_nodes, final_state)

    final_state["nodes_done"] = done_nodes
    return final_state


__all__ = ["PaperState", "build_paper_graph", "run_paper_graph"]
