"""
Tests for StudyState shape, StudyStore operations, and fixture loading.

No LLM calls. No AWS credentials required.
"""

from __future__ import annotations

import pytest

from src.state import (
    Assumption,
    DecisionRecord,
    Insight,
    Script,
    ScriptQuestion,
    Session,
    Theme,
)
from src.store import StudyStore


# ── StudyStore.create_study ────────────────────────────────────────────────────


class TestCreateStudy:
    def test_returns_state_with_correct_study_id(self):
        store = StudyStore()
        state = store.create_study("study-001", "We believe X because Y")
        assert state["study_id"] == "study-001"

    def test_returns_state_with_correct_hypothesis(self):
        store = StudyStore()
        state = store.create_study("s", "The hypothesis")
        assert state["hypothesis"] == "The hypothesis"

    def test_initial_status_is_active(self):
        store = StudyStore()
        state = store.create_study("s", "h")
        assert state["status"] == "active"

    def test_initial_lists_are_empty(self):
        store = StudyStore()
        state = store.create_study("s", "h")
        assert state["assumptions"] == []
        assert state["scripts"] == []
        assert state["sessions"] == []
        assert state["observations"] == []
        assert state["themes"] == []
        assert state["insights"] == []

    def test_decision_record_is_none(self):
        store = StudyStore()
        state = store.create_study("s", "h")
        assert state["decision_record"] is None

    def test_assumption_map_complete_is_false(self):
        store = StudyStore()
        state = store.create_study("s", "h")
        assert state["assumption_map_complete"] is False

    def test_study_is_stored(self):
        store = StudyStore()
        store.create_study("study-abc", "h")
        assert "study-abc" in store.list_studies()


# ── StudyStore.get_study / save_study ─────────────────────────────────────────


class TestGetAndSaveStudy:
    def test_get_returns_none_for_unknown_id(self):
        store = StudyStore()
        assert store.get_study("nonexistent") is None

    def test_get_returns_state_after_create(self):
        store = StudyStore()
        store.create_study("s1", "h")
        result = store.get_study("s1")
        assert result is not None
        assert result["study_id"] == "s1"

    def test_save_then_get_roundtrip(self):
        store = StudyStore()
        state = store.create_study("s2", "h")
        state["status"] = "synthesised"
        store.save_study(state)
        retrieved = store.get_study("s2")
        assert retrieved["status"] == "synthesised"

    def test_save_updates_assumptions(self):
        store = StudyStore()
        state = store.create_study("s3", "h")
        assumption = Assumption(
            id="a1", statement="Users need X", risk_lens="desirability"
        )
        state["assumptions"] = [assumption]
        store.save_study(state)
        retrieved = store.get_study("s3")
        assert len(retrieved["assumptions"]) == 1
        assert retrieved["assumptions"][0].statement == "Users need X"


# ── StudyStore.load_fixture ────────────────────────────────────────────────────


class TestLoadFixture:
    def test_loads_adtech_study(self):
        store = StudyStore()
        state = store.load_fixture("adtech_study")
        assert state["study_id"] == "adtech-creative-optimisation"

    def test_fixture_has_ten_assumptions(self):
        store = StudyStore()
        state = store.load_fixture("adtech_study")
        assert len(state["assumptions"]) == 10

    def test_fixture_has_ten_sessions(self):
        store = StudyStore()
        state = store.load_fixture("adtech_study")
        assert len(state["sessions"]) == 10

    def test_fixture_has_script(self):
        store = StudyStore()
        state = store.load_fixture("adtech_study")
        assert len(state["scripts"]) >= 1

    def test_fixture_assumptions_are_assumption_objects(self):
        store = StudyStore()
        state = store.load_fixture("adtech_study")
        for a in state["assumptions"]:
            assert isinstance(a, Assumption)

    def test_fixture_sessions_are_session_objects(self):
        store = StudyStore()
        state = store.load_fixture("adtech_study")
        for s in state["sessions"]:
            assert isinstance(s, Session)

    def test_fixture_assumptions_have_valid_risk_lens(self):
        valid_lenses = {"desirability", "usability", "feasibility", "viability"}
        store = StudyStore()
        state = store.load_fixture("adtech_study")
        for a in state["assumptions"]:
            assert a.risk_lens in valid_lenses, f"Invalid risk_lens: {a.risk_lens}"

    def test_fixture_assumptions_have_risk_scores(self):
        """Fixture is pre-rated, so risk scores should be computed."""
        store = StudyStore()
        state = store.load_fixture("adtech_study")
        for a in state["assumptions"]:
            assert a.risk_score > 0, f"Assumption {a.id} has zero risk score"

    def test_fixture_sessions_have_raw_notes(self):
        store = StudyStore()
        state = store.load_fixture("adtech_study")
        for s in state["sessions"]:
            assert s.raw_notes.strip(), f"Session {s.id} has empty raw_notes"

    def test_missing_fixture_raises(self):
        store = StudyStore()
        with pytest.raises(FileNotFoundError):
            store.load_fixture("nonexistent_fixture")


# ── Dataclass constructors ─────────────────────────────────────────────────────


class TestDomainDataclasses:
    def test_assumption_defaults(self):
        a = Assumption(id="a1", statement="X", risk_lens="desirability")
        assert a.importance == 0
        assert a.evidence_level == 0
        assert a.risk_score == 0.0
        assert a.status == "untested"
        assert a.research_question == ""

    def test_script_question_defaults(self):
        q = ScriptQuestion(id="q1", original_text="Tell me about X")
        assert q.verdict == ""
        assert q.issue_types == []
        assert q.explanation == ""
        assert q.rewrite == ""

    def test_script_defaults(self):
        s = Script(id="s1", study_id="study-1", raw_text="Questions here")
        assert s.clean_text == ""
        assert s.bias_score == 0.0
        assert s.questions == []

    def test_session_fields(self):
        s = Session(
            id="ses1", study_id="study-1", participant_id="P1", raw_notes="Notes"
        )
        assert s.participant_id == "P1"
        assert s.raw_notes == "Notes"

    def test_session_summary_defaults_empty(self):
        s = Session(
            id="ses1", study_id="study-1", participant_id="P1", raw_notes="Notes"
        )
        assert s.summary == ""

    def test_theme_defaults(self):
        t = Theme(id="t1", study_id="s1", label="Theme A", description="desc")
        assert t.counterevidence == "none found"
        assert t.session_count == 0
        assert t.confidence == "emerging"
        assert t.assumption_id is None

    def test_insight_defaults(self):
        i = Insight(id="i1", study_id="s1", statement="Finding")
        assert i.evidence_strength == "low"
        assert i.theme_ids == []
        assert i.assumption_status == "uncertain"

    def test_decision_record_defaults(self):
        dr = DecisionRecord(
            id="dr1",
            study_id="s1",
            question="Should we pursue?",
            recommendation="pursue",
            evidence_summary="Summary",
        )
        assert dr.confidence_score == 0
        assert dr.confidence_breakdown == {}
        assert dr.descoped_items == ""
        assert dr.remaining_risks == ""
        assert dr.next_steps == ""
