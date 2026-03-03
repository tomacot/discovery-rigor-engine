"""
Tests for deterministic scoring functions.

All tests here are pure arithmetic — no LLM calls, no AWS credentials required.
These are the quality guardrails: the scoring must be reproducible and auditable.

Risk score range: 1 (lowest risk) to 25 (highest risk)
Confidence score range: 0 to 100
"""

from __future__ import annotations

import pytest

from src.scoring import compute_confidence_score, compute_risk_score
from src.state import Insight, Theme


# ── Risk score ─────────────────────────────────────────────────────────────────


class TestComputeRiskScore:
    """Formula: importance × (6 - evidence_level). Range 1–25."""

    def test_maximum_risk(self):
        """Importance 5, evidence 1 → 5 × 5 = 25."""
        assert compute_risk_score(5, 1) == 25.0

    def test_minimum_risk(self):
        """Importance 1, evidence 5 → 1 × 1 = 1."""
        assert compute_risk_score(1, 5) == 1.0

    def test_mid_values(self):
        """Importance 3, evidence 3 → 3 × 3 = 9."""
        assert compute_risk_score(3, 3) == 9.0

    def test_high_importance_medium_evidence(self):
        """Importance 5, evidence 3 → 5 × 3 = 15."""
        assert compute_risk_score(5, 3) == 15.0

    def test_low_importance_no_evidence(self):
        """Importance 1, evidence 1 → 1 × 5 = 5."""
        assert compute_risk_score(1, 1) == 5.0

    def test_returns_float(self):
        """Return type must be float, not int."""
        result = compute_risk_score(2, 4)
        assert isinstance(result, float)

    @pytest.mark.parametrize(
        "importance,evidence,expected",
        [
            (5, 1, 25.0),
            (5, 2, 20.0),
            (5, 3, 15.0),
            (5, 4, 10.0),
            (5, 5, 5.0),
            (1, 1, 5.0),
            (1, 5, 1.0),
            (3, 3, 9.0),
            (4, 2, 16.0),
        ],
    )
    def test_parametrised_cases(self, importance, evidence, expected):
        assert compute_risk_score(importance, evidence) == expected


# ── Confidence score ───────────────────────────────────────────────────────────


def _make_insight(
    strength: str, theme_ids: list[str], assumption_status: str = "uncertain"
) -> Insight:
    """Helper to construct a minimal Insight for testing."""
    return Insight(
        id="i1",
        study_id="test",
        statement="Test insight",
        evidence_strength=strength,
        theme_ids=theme_ids,
        assumption_status=assumption_status,
    )


def _make_theme(session_count: int, counterevidence: str = "none found") -> Theme:
    """Helper to construct a minimal Theme for testing."""
    return Theme(
        id="t1",
        study_id="test",
        label="Test theme",
        description="desc",
        session_count=session_count,
        counterevidence=counterevidence,
    )


class TestComputeConfidenceScore:
    """Confidence score = weighted sum of 4 components × 100."""

    def test_empty_inputs_returns_zero(self):
        score, breakdown = compute_confidence_score([], [], 5, 3)
        assert score == 0
        assert all(v == 0.0 for v in breakdown.values())

    def test_zero_sessions_returns_zero(self):
        insights = [_make_insight("high", ["t1"])]
        themes = [_make_theme(2)]
        score, _ = compute_confidence_score(insights, themes, 0, 1)
        assert score == 0

    def test_all_high_evidence_with_counterevidence(self):
        """All-high evidence + counterevidence on all themes → high score."""
        insights = [
            _make_insight("high", ["t1"]),
            _make_insight("high", ["t2"]),
        ]
        themes = [
            _make_theme(3, counterevidence="Some users prefer manual workflow"),
            _make_theme(4, counterevidence="P2 reported no time pressure"),
        ]
        score, breakdown = compute_confidence_score(insights, themes, 5, 2)
        # Evidence strength = 1.0, all themes have counterevidence → high score
        assert score > 60
        assert breakdown["evidence_strength"] == 1.0
        assert breakdown["counterevidence_coverage"] == 1.0

    def test_all_low_evidence_no_counterevidence(self):
        """All-low evidence + no counterevidence → low score."""
        insights = [_make_insight("low", ["t1"])]
        themes = [_make_theme(1)]  # only 1 session
        score, _ = compute_confidence_score(insights, themes, 5, 3)
        assert score < 40

    def test_breakdown_keys_present(self):
        """Breakdown must always contain all four component keys."""
        insights = [_make_insight("medium", ["t1"])]
        themes = [_make_theme(2)]
        _, breakdown = compute_confidence_score(insights, themes, 3, 2)
        assert set(breakdown.keys()) == {
            "evidence_strength",
            "theme_saturation",
            "counterevidence_coverage",
            "session_diversity",
        }

    def test_score_is_integer(self):
        """Score must be an int, not a float."""
        insights = [_make_insight("medium", ["t1"])]
        themes = [_make_theme(2)]
        score, _ = compute_confidence_score(insights, themes, 3, 2)
        assert isinstance(score, int)

    def test_score_bounded_0_100(self):
        """Score must be in [0, 100] regardless of inputs."""
        insights = [_make_insight("high", ["t1"])] * 10
        themes = [_make_theme(10, counterevidence="lots")] * 10
        score, _ = compute_confidence_score(insights, themes, 10, 10)
        assert 0 <= score <= 100

    def test_theme_saturation_capped_at_1(self):
        """More themes than assumptions tested → saturation capped at 1.0, not > 1."""
        insights = [_make_insight("high", ["t1"])]
        themes = [_make_theme(2)] * 5  # 5 themes, only 2 assumptions tested
        _, breakdown = compute_confidence_score(insights, themes, 3, 2)
        assert breakdown["theme_saturation"] == 1.0

    def test_mixed_evidence_averages_correctly(self):
        """high + low = mean 0.65 → evidence_strength component = 0.65."""
        insights = [
            _make_insight("high", ["t1"]),  # 1.0
            _make_insight("low", ["t2"]),  # 0.3
        ]
        themes = [_make_theme(2), _make_theme(2)]
        _, breakdown = compute_confidence_score(insights, themes, 4, 2)
        # (1.0 + 0.3) / 2 = 0.65
        assert breakdown["evidence_strength"] == pytest.approx(0.65, abs=0.001)
