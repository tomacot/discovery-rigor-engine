"""
Assumption decompose node.

Calls the LLM to break a research hypothesis into discrete, testable assumptions.
This is the entry point for the assumption-mapping sub-flow.
"""

from __future__ import annotations

from src.llm import call_llm_structured
from src.prompts.decompose_hypothesis import (
    DECOMPOSE_SYSTEM,
    DecomposedAssumptions,
    get_decompose_prompt,
)
from src.state import Assumption, StudyState


def decompose_hypothesis(state: StudyState) -> dict:
    """Decompose the study hypothesis into a ranked list of Assumption dataclasses."""
    hypothesis = state["hypothesis"]
    prompt = get_decompose_prompt(hypothesis)
    result: DecomposedAssumptions = call_llm_structured(
        prompt, DecomposedAssumptions, DECOMPOSE_SYSTEM
    )

    assumptions = [
        Assumption(
            id=f"A{i + 1}",
            statement=draft.statement,
            risk_lens="",  # Populated by categorise_risk_lens node
        )
        for i, draft in enumerate(result.assumptions)
    ]

    return {"assumptions": assumptions}
