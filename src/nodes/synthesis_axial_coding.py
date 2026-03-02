"""
Synthesis axial coding node.

LLM node: clusters observations into themes. Enforces the ≥2-session minimum
deterministically after the LLM responds — themes spanning only one session are
filtered out (or marked 'emerging' if allowed through with session_count==1).
"""

from __future__ import annotations

from src.llm import call_llm_structured
from src.prompts.axial_coding import (
    AXIAL_CODING_SYSTEM,
    AxialCodingResult,
    get_axial_coding_prompt,
)
from src.state import Assumption, Observation, StudyState, Theme


def _draft_to_theme(
    draft,  # ThemeDraft from prompt model
    index: int,
    study_id: str,
    observations: list[Observation],
) -> Theme:
    """Convert a ThemeDraft Pydantic model into a Theme dataclass."""
    obs_ids = [
        observations[idx].id
        for idx in draft.observation_indices
        if idx < len(observations)
    ]
    session_count = len(set(draft.session_ids))
    confidence = "strong" if session_count >= 3 else "moderate" if session_count >= 2 else "emerging"

    return Theme(
        id=f"T{index + 1}",
        study_id=study_id,
        label=draft.label,
        description=draft.description,
        observation_ids=obs_ids,
        session_count=session_count,
        counterevidence=draft.counterevidence,
        assumption_id=draft.assumption_id,
        confidence=confidence,
    )


def axial_coding(state: StudyState) -> dict:
    """Cluster observations into themes; filter themes with fewer than 2 sessions."""
    observations: list[Observation] = state["observations"]
    assumptions: list[Assumption] = state["assumptions"]

    obs_dicts = [
        {"index": i, "session_id": obs.session_id, "type": obs.type, "content": obs.content}
        for i, obs in enumerate(observations)
    ]
    assumption_dicts = [{"id": a.id, "statement": a.statement} for a in assumptions]

    prompt = get_axial_coding_prompt(obs_dicts, assumption_dicts)
    result: AxialCodingResult = call_llm_structured(
        prompt, AxialCodingResult, AXIAL_CODING_SYSTEM
    )

    themes = [
        _draft_to_theme(draft, i, state["study_id"], observations)
        for i, draft in enumerate(result.themes)
    ]

    # Enforce ≥2-session minimum — single-session themes are unreliable
    themes = [t for t in themes if t.session_count >= 2]

    return {"themes": themes}
