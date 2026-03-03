"""
Deterministic scoring functions.

All scoring in this file is arithmetic — no LLM calls. This is deliberate:
the parts of the tool that enforce research quality must be reproducible
and auditable, not dependent on LLM output.

See CLAUDE.md "Product Decisions" for why this split matters.
"""

from __future__ import annotations

from typing import Sequence

from src.state import Insight, Theme

# Named constants — no magic numbers
MIN_SESSIONS_PER_THEME = 2
STRENGTH_MAP: dict[str, float] = {"high": 1.0, "medium": 0.6, "low": 0.3}

# Confidence score weights
WEIGHT_EVIDENCE_STRENGTH = 0.40
WEIGHT_THEME_SATURATION = 0.25
WEIGHT_COUNTER_COVERAGE = 0.20
WEIGHT_SESSION_DIVERSITY = 0.15


def compute_risk_score(importance: int, evidence_level: int) -> float:
    """
    Compute risk score for an assumption.

    Higher score = riskier (high importance + low evidence).
    Formula: importance × (6 - evidence_level)
    Range: 1×1=1 (lowest risk) to 5×5=25 (highest risk)
    """
    return float(importance * (6 - evidence_level))


def compute_confidence_score(
    insights: Sequence[Insight],
    themes: Sequence[Theme],
    total_sessions: int,
    assumptions_tested: int,
) -> tuple[int, dict[str, float]]:
    """
    Compute the confidence score (0-100) for a decision record.

    Returns the score and a breakdown dict showing each component's contribution.
    The breakdown is displayed in the UI for transparency.
    """
    if not insights or not themes or total_sessions == 0:
        return 0, {
            "evidence_strength": 0.0,
            "theme_saturation": 0.0,
            "counterevidence_coverage": 0.0,
            "session_diversity": 0.0,
        }

    # Evidence strength: mean of insight strength ratings
    evidence_strength = sum(
        STRENGTH_MAP.get(i.evidence_strength, 0.0) for i in insights
    ) / len(insights)

    # Theme saturation: proportion of tested assumptions covered by themes
    theme_saturation = min(1.0, len(themes) / max(assumptions_tested, 1))

    # Counterevidence coverage: proportion of themes with populated counterevidence
    counter_coverage = sum(
        1 for t in themes if t.counterevidence != "none found"
    ) / len(themes)

    # Session diversity: proportion of sessions referenced across all observations
    referenced_sessions: set[int] = set()
    for theme in themes:
        # Session count is tracked on the theme
        referenced_sessions.update(range(theme.session_count))
    session_diversity = min(1.0, len(referenced_sessions) / max(total_sessions, 1))

    # Weighted aggregate
    raw = (
        evidence_strength * WEIGHT_EVIDENCE_STRENGTH
        + theme_saturation * WEIGHT_THEME_SATURATION
        + counter_coverage * WEIGHT_COUNTER_COVERAGE
        + session_diversity * WEIGHT_SESSION_DIVERSITY
    )

    breakdown = {
        "evidence_strength": round(evidence_strength, 3),
        "theme_saturation": round(theme_saturation, 3),
        "counterevidence_coverage": round(counter_coverage, 3),
        "session_diversity": round(session_diversity, 3),
    }

    return round(raw * 100), breakdown
