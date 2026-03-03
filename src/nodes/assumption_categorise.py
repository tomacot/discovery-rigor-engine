"""
Assumption categorise node.

Tags each assumption with a risk lens (desirability, usability, feasibility, viability).
Runs after decompose_hypothesis, before the user's interactive rating step.
"""

from __future__ import annotations

from dataclasses import replace

from src.llm import call_llm_structured
from src.prompts.categorise_risk_lens import (
    CATEGORISE_SYSTEM,
    CategorisedAssumptions,
    get_categorise_prompt,
)
from src.state import Assumption, StudyState


def categorise_risk_lens(state: StudyState) -> dict:
    """Tag each assumption with its risk lens via LLM; return updated assumptions list."""
    assumptions: list[Assumption] = state["assumptions"]

    assumption_dicts = [{"id": a.id, "statement": a.statement} for a in assumptions]
    prompt = get_categorise_prompt(assumption_dicts)
    result: CategorisedAssumptions = call_llm_structured(
        prompt, CategorisedAssumptions, CATEGORISE_SYSTEM
    )

    lens_lookup: dict[str, str] = {
        t.assumption_id: t.risk_lens for t in result.taggings
    }

    updated = [
        replace(a, risk_lens=lens_lookup.get(a.id, "desirability")) for a in assumptions
    ]

    return {"assumptions": updated}
