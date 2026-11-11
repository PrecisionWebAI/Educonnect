# ============================================================
# exams/llm — paper generation ka AI layer (blueprint §2.4/§2.5).
#
# Layer ka kaam:  service (business rules) ko LLM ki detail se door rakhna.
#   service  →  llm.services  →  llm.generator  →  llm.base (client)
#                                               →  llm.prompts (template)
#
# Yahan kabhi DB/SQL ka kaam nahi hota — sirf AI.
# ============================================================

from .base import (
    LLMNotConfigured,
    LLMUnavailable,
    build_llm,
    get_judge_llm,
    get_llm,
    get_model_info,
    is_llm_available,
)
from .generator import (
    build_question_plan,
    extract_json,
    generate_all,
    generate_section,
)
from .graph import build_paper_graph, run_paper_graph
from .prompts import (
    build_quality_messages,
    build_question_block,
    build_section_messages,
)
from .services import (
    ai_budget,
    build_ctx,
    build_sources,
    check_quality,
    config_to_source,
    coverage_report,
    generate_paper_questions,
    part_b_marks,
    plan_for_paper,
    repair_incomplete,
    rule_checks,
    suggest_marks,
)

__all__ = [
    "LLMNotConfigured",
    "LLMUnavailable",
    "ai_budget",
    "build_ctx",
    "build_llm",
    "build_paper_graph",
    "build_quality_messages",
    "build_question_block",
    "build_question_plan",
    "build_section_messages",
    "build_sources",
    "check_quality",
    "config_to_source",
    "coverage_report",
    "extract_json",
    "generate_all",
    "generate_paper_questions",
    "generate_section",
    "get_judge_llm",
    "get_llm",
    "get_model_info",
    "is_llm_available",
    "part_b_marks",
    "plan_for_paper",
    "repair_incomplete",
    "rule_checks",
    "run_paper_graph",
    "suggest_marks",
]
