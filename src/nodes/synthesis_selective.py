"""
Synthesis selective coding node.

LLM node: synthesises themes into insight statements, each linked to one or more
themes and traced back to a specific assumption. The LLM reasons about evidence
strength and whether the assumption is confirmed, challenged, or uncertain.
"""

from __future__ import annotations

from src.llm import call_llm_structured
from src.prompts.selective_coding import (
    SELECTIVE_CODING_SYSTEM,
    SelectiveCodingResult,
    get_selective_coding_prompt,
)
from src.state import Assumption, Insight, StudyState, Theme


def _draft_to_insight(
    draft,  # InsightDraft from prompt model
    index: int,
    study_id: str,
    themes: list[Theme],
) -> Insight:
    """Convert an InsightDraft Pydantic model into an Insight dataclass."""
    theme_ids = [
        themes[idx].id
        for idx in draft.theme_indices
        if idx < len(themes)
    ]
    return Insight(
        id=f"INS{index + 1}",
        study_id=study_id,
        statement=draft.statement,
        evidence_strength=draft.evidence_strength,
        theme_ids=theme_ids,
        counterevidence=draft.counterevidence,
        implication=draft.implication,
        assumption_id=draft.assumption_id,
        assumption_status=draft.assumption_status,
        supporting_quotes=draft.supporting_quotes,
        frequency=draft.frequency,
        why_it_matters=draft.why_it_matters,
        user_segments_affected=draft.user_segments_affected,
        current_workarounds=draft.current_workarounds,
        potential_solutions=draft.potential_solutions,
        actionability=draft.actionability,
        priority=draft.priority,
    )


def selective_coding(state: StudyState) -> dict:
    """Synthesise themes into Insight dataclasses; return updated insights list."""
    themes: list[Theme] = state["themes"]
    assumptions: list[Assumption] = state["assumptions"]

    theme_dicts = [
        {"index": i, "label": t.label, "description": t.description, "counterevidence": t.counterevidence}
        for i, t in enumerate(themes)
    ]
    assumption_dicts = [
        {"id": a.id, "statement": a.statement, "risk_lens": a.risk_lens}
        for a in assumptions
    ]

    prompt = get_selective_coding_prompt(theme_dicts, assumption_dicts, state["hypothesis"])
    result: SelectiveCodingResult = call_llm_structured(
        prompt, SelectiveCodingResult, SELECTIVE_CODING_SYSTEM
    )

    insights = [
        _draft_to_insight(draft, i, state["study_id"], themes)
        for i, draft in enumerate(result.insights)
    ]

    return {"insights": insights}
