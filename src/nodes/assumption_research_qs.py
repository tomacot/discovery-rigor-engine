"""
Assumption research questions node.

Generates one focused research question for each of the top 3 highest-risk
assumptions. Runs last in the assumption-mapping sub-flow, after scoring.
"""

from __future__ import annotations

from dataclasses import replace

from src.llm import call_llm_structured
from src.prompts.generate_research_questions import (
    RESEARCH_QS_SYSTEM,
    ResearchQuestions,
    get_research_questions_prompt,
)
from src.state import Assumption, StudyState


def generate_research_questions(state: StudyState) -> dict:
    """Add a research_question to the top 3 risk-scored assumptions via LLM."""
    assumptions: list[Assumption] = state["assumptions"]
    hypothesis: str = state["hypothesis"]

    top_3 = assumptions[:3]
    top_dicts = [
        {"id": a.id, "statement": a.statement, "risk_lens": a.risk_lens}
        for a in top_3
    ]

    prompt = get_research_questions_prompt(top_dicts, hypothesis)
    result: ResearchQuestions = call_llm_structured(
        prompt, ResearchQuestions, RESEARCH_QS_SYSTEM
    )

    question_lookup: dict[str, str] = {q.assumption_id: q.question for q in result.questions}

    updated = [
        replace(a, research_question=question_lookup[a.id])
        if a.id in question_lookup
        else a
        for a in assumptions
    ]

    return {"assumptions": updated}
