"""
Assumption score node.

Deterministic: computes risk_score from user-rated importance and evidence_level,
then sorts assumptions by score descending. Marks the assumption map as complete.
No LLM call — scoring must be reproducible and auditable.
"""

from __future__ import annotations

from dataclasses import replace

from src.scoring import compute_risk_score
from src.state import Assumption, StudyState


def compute_risk_scores(state: StudyState) -> dict:
    """Score and sort assumptions by risk; mark assumption_map_complete True."""
    assumptions: list[Assumption] = state["assumptions"]

    scored = [
        replace(a, risk_score=compute_risk_score(a.importance, a.evidence_level))
        for a in assumptions
    ]

    sorted_assumptions = sorted(scored, key=lambda a: a.risk_score, reverse=True)

    return {
        "assumptions": sorted_assumptions,
        "assumption_map_complete": True,
    }
