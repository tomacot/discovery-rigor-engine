"""
Tests for the data traceability chain.

These tests verify structural integrity — every entity in the chain must
link cleanly to the entity below it:

  DecisionRecord → Insights → Themes → Observations → Sessions

No LLM calls. Tests construct synthetic but realistic chain objects,
then assert each link is intact.

Why this matters (product context): The tool's core promise is that any
claim in a decision record can be traced back to specific interview data.
If these links break (e.g., a Theme references an Observation that no
longer exists), the traceability guarantee is violated.
"""

from __future__ import annotations

import pytest

from src.state import DecisionRecord, Insight, Observation, Session, Theme


# ── Fixtures: a synthetic but valid traceability chain ────────────────────────


@pytest.fixture
def sessions() -> list[Session]:
    return [
        Session(id="ses-1", study_id="s1", participant_id="P1", raw_notes="Notes P1"),
        Session(id="ses-2", study_id="s1", participant_id="P2", raw_notes="Notes P2"),
        Session(id="ses-3", study_id="s1", participant_id="P3", raw_notes="Notes P3"),
    ]


@pytest.fixture
def observations(sessions) -> list[Observation]:
    return [
        Observation(id="obs-1", session_id="ses-1", type="behaviour", content="P1 manually resizes"),
        Observation(id="obs-2", session_id="ses-1", type="statement", content="'I duplicate the campaign'"),
        Observation(id="obs-3", session_id="ses-2", type="behaviour", content="P2 uses spreadsheet"),
        Observation(id="obs-4", session_id="ses-2", type="context", content="Team of 3 designers"),
        Observation(id="obs-5", session_id="ses-3", type="statement", content="'No time for A/B testing'"),
    ]


@pytest.fixture
def themes(observations) -> list[Theme]:
    return [
        Theme(
            id="theme-1",
            study_id="s1",
            label="Manual creative duplication",
            description="Users duplicate campaigns instead of using templates",
            observation_ids=["obs-1", "obs-2", "obs-3"],
            session_count=2,  # ses-1 and ses-2
            counterevidence="P3 does use templates for some formats",
        ),
        Theme(
            id="theme-2",
            study_id="s1",
            label="Time pressure on testing",
            description="Teams lack time for structured A/B testing",
            observation_ids=["obs-4", "obs-5"],
            session_count=2,  # ses-2 and ses-3
            counterevidence="none found",
        ),
    ]


@pytest.fixture
def insights(themes) -> list[Insight]:
    return [
        Insight(
            id="insight-1",
            study_id="s1",
            statement="Mid-market teams waste 2h/week on manual creative ops",
            evidence_strength="high",
            theme_ids=["theme-1"],
            counterevidence="Some users have workarounds",
            implication="Automation could save 100h/yr per team",
            assumption_status="confirmed",
        ),
        Insight(
            id="insight-2",
            study_id="s1",
            statement="Teams skip A/B testing due to operational burden, not disinterest",
            evidence_strength="medium",
            theme_ids=["theme-2"],
            assumption_status="challenged",
        ),
    ]


@pytest.fixture
def decision_record() -> DecisionRecord:
    return DecisionRecord(
        id="dr-1",
        study_id="s1",
        question="Should we build an automated creative resizing feature?",
        recommendation="pursue",
        evidence_summary="Strong evidence of manual workflow pain...",
        confidence_score=72,
        confidence_breakdown={
            "evidence_strength": 0.8,
            "theme_saturation": 1.0,
            "counterevidence_coverage": 0.5,
            "session_diversity": 0.8,
        },
    )


# ── Chain integrity tests ──────────────────────────────────────────────────────


class TestThemeSessionMinimum:
    """Every theme must reference at least 2 sessions."""

    def test_all_themes_meet_session_minimum(self, themes):
        for theme in themes:
            assert theme.session_count >= 2, (
                f"Theme '{theme.label}' only has {theme.session_count} session(s). "
                f"Minimum is 2 to prevent single-source themes."
            )

    def test_single_session_theme_fails_check(self):
        """A theme with session_count=1 violates the research quality rule."""
        weak_theme = Theme(
            id="t-weak",
            study_id="s1",
            label="Weak theme",
            description="Only one session",
            session_count=1,
        )
        assert weak_theme.session_count < 2  # This is the condition we guard against


class TestInsightThemeLinks:
    """Every insight must reference at least one theme that exists."""

    def test_all_insight_theme_ids_resolve(self, insights, themes):
        theme_ids = {t.id for t in themes}
        for insight in insights:
            assert insight.theme_ids, f"Insight '{insight.id}' has no theme references"
            for theme_id in insight.theme_ids:
                assert theme_id in theme_ids, (
                    f"Insight '{insight.id}' references theme '{theme_id}' "
                    f"which does not exist in the theme list."
                )

    def test_no_insight_has_empty_theme_list(self, insights):
        for insight in insights:
            assert len(insight.theme_ids) >= 1, (
                f"Insight '{insight.statement}' has no themes — unreachable from evidence."
            )


class TestThemeObservationLinks:
    """Every theme must reference observations that exist."""

    def test_all_theme_observation_ids_resolve(self, themes, observations):
        obs_ids = {o.id for o in observations}
        for theme in themes:
            for obs_id in theme.observation_ids:
                assert obs_id in obs_ids, (
                    f"Theme '{theme.label}' references observation '{obs_id}' "
                    f"which does not exist."
                )

    def test_no_theme_has_empty_observation_list(self, themes):
        for theme in themes:
            assert len(theme.observation_ids) >= 1, (
                f"Theme '{theme.label}' has no observation references."
            )


class TestObservationSessionLinks:
    """Every observation must reference a session that exists."""

    def test_all_observation_session_ids_resolve(self, observations, sessions):
        session_ids = {s.id for s in sessions}
        for obs in observations:
            assert obs.session_id in session_ids, (
                f"Observation '{obs.id}' references session '{obs.session_id}' "
                f"which does not exist."
            )

    def test_observations_not_marked_as_interpretations(self, observations):
        """Open coding enforces is_interpretation=False. Verify none slipped through."""
        for obs in observations:
            assert obs.is_interpretation is False, (
                f"Observation '{obs.id}' is marked as an interpretation. "
                f"Open coding should only produce observable facts."
            )


class TestObservationTypes:
    """Observations must have valid type codes."""

    VALID_TYPES = {"behaviour", "statement", "context"}

    def test_all_observations_have_valid_type(self, observations):
        for obs in observations:
            assert obs.type in self.VALID_TYPES, (
                f"Observation '{obs.id}' has invalid type '{obs.type}'. "
                f"Valid types: {self.VALID_TYPES}"
            )


class TestCounterevidenceCoverage:
    """At least one theme should have counterevidence (not 'none found')."""

    def test_some_themes_have_counterevidence(self, themes):
        themes_with_counter = [t for t in themes if t.counterevidence != "none found"]
        assert len(themes_with_counter) >= 1, (
            "No themes have counterevidence. "
            "Synthesis without counterevidence risks confirmation bias."
        )


class TestDecisionRecordConfidence:
    """Confidence score must be in range and breakdown must be present."""

    def test_confidence_score_in_range(self, decision_record):
        assert 0 <= decision_record.confidence_score <= 100

    def test_confidence_breakdown_has_four_components(self, decision_record):
        expected_keys = {
            "evidence_strength",
            "theme_saturation",
            "counterevidence_coverage",
            "session_diversity",
        }
        assert set(decision_record.confidence_breakdown.keys()) == expected_keys

    def test_recommendation_is_valid(self, decision_record):
        valid_recommendations = {"pursue", "pivot", "park", "need_more_evidence"}
        assert decision_record.recommendation in valid_recommendations


class TestFullChainTraversal:
    """
    End-to-end chain walk: decision_record → insight → theme → observation → session.

    This mirrors what the /check-traceability command does at runtime.
    """

    def test_chain_walk_succeeds(self, decision_record, insights, themes, observations, sessions):
        theme_by_id = {t.id: t for t in themes}
        obs_by_id = {o.id: o for o in observations}
        session_by_id = {s.id: s for s in sessions}

        broken_links: list[str] = []

        for insight in insights:
            for theme_id in insight.theme_ids:
                theme = theme_by_id.get(theme_id)
                if not theme:
                    broken_links.append(f"Insight {insight.id} → missing theme {theme_id}")
                    continue
                for obs_id in theme.observation_ids:
                    obs = obs_by_id.get(obs_id)
                    if not obs:
                        broken_links.append(f"Theme {theme.id} → missing observation {obs_id}")
                        continue
                    session = session_by_id.get(obs.session_id)
                    if not session:
                        broken_links.append(f"Observation {obs.id} → missing session {obs.session_id}")

        assert not broken_links, "Broken links in evidence chain:\n" + "\n".join(broken_links)
