"""
Tests for the script review pipeline — bias detection and clean-script assembly.

Split into two layers:
  1. Deterministic unit tests — parse and assemble nodes (no LLM, always run)
  2. Integration accuracy test — actual LLM bias detection (requires AWS credentials)

The deterministic layer is the foundation: it ensures questions are correctly
extracted from raw text, and the bias score and clean script are correctly
assembled from verdict data. These run in CI without any external dependencies.

The integration layer runs the full LLM pipeline against 30 ground-truth questions
(20 known-biased, 10 known-clean) and reports true-positive / false-positive rates.
It is marked with @pytest.mark.integration and skipped unless AWS creds are available.
"""

from __future__ import annotations

import os
from dataclasses import replace

import pytest

from src.nodes.script_assemble import assemble_clean_script
from src.nodes.script_parse import parse_questions
from src.state import Script, ScriptQuestion, Session, StudyState


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_state(raw_text: str) -> StudyState:
    """Construct a minimal StudyState with one script for parse/assemble tests."""
    script = Script(id="s1", study_id="study-1", raw_text=raw_text)
    return {
        "study_id": "study-1",
        "hypothesis": "Test hypothesis",
        "status": "active",
        "assumptions": [],
        "assumption_map_complete": False,
        "scripts": [script],
        "sessions": [],
        "observations": [],
        "themes": [],
        "insights": [],
        "decision_record": None,
        "current_flow": "script_review",
        "messages": [],
    }


def _apply_verdicts(script: Script, verdicts: list[str]) -> Script:
    """Assign a verdict to each question in order (for assembly tests)."""
    updated_questions = [
        replace(q, verdict=v) for q, v in zip(script.questions, verdicts)
    ]
    return replace(script, questions=updated_questions)


# ── Parse node (deterministic) ─────────────────────────────────────────────────


class TestScriptParse:
    """parse_questions extracts numbered lines into ScriptQuestion objects."""

    def test_numbered_questions_extracted(self):
        state = _make_state("1. Tell me about yourself\n2. What tools do you use?")
        result = parse_questions(state)
        questions = result["scripts"][0].questions
        assert len(questions) == 2

    def test_numbering_stripped(self):
        state = _make_state("1. What do you think about X?\n2) How often do you Y?")
        result = parse_questions(state)
        questions = result["scripts"][0].questions
        assert questions[0].original_text == "What do you think about X?"
        assert questions[1].original_text == "How often do you Y?"

    def test_empty_lines_ignored(self):
        state = _make_state("1. Question one\n\n\n2. Question two\n")
        result = parse_questions(state)
        questions = result["scripts"][0].questions
        assert len(questions) == 2

    def test_question_ids_assigned(self):
        state = _make_state("1. Q one\n2. Q two\n3. Q three")
        result = parse_questions(state)
        questions = result["scripts"][0].questions
        assert questions[0].id == "Q1"
        assert questions[1].id == "Q2"
        assert questions[2].id == "Q3"

    def test_unnumbered_lines_preserved(self):
        """Lines without numbers are kept as-is (section headers, probes)."""
        state = _make_state("Tell me about X\nHow often do you Y?")
        result = parse_questions(state)
        questions = result["scripts"][0].questions
        assert len(questions) == 2
        assert questions[0].original_text == "Tell me about X"

    def test_single_question(self):
        state = _make_state("1. Single question")
        result = parse_questions(state)
        assert len(result["scripts"][0].questions) == 1

    def test_returns_script_in_list(self):
        """Node must return {"scripts": [Script]}, not {"scripts": Script}."""
        state = _make_state("1. A question")
        result = parse_questions(state)
        assert isinstance(result["scripts"], list)
        assert len(result["scripts"]) == 1


# ── Assemble node (deterministic) ─────────────────────────────────────────────


class TestScriptAssemble:
    """assemble_clean_script computes bias_score and builds clean_text."""

    def _state_with_verdicts(self, raw: str, verdicts: list[str]) -> StudyState:
        state = _make_state(raw)
        result = parse_questions(state)
        updated_script = _apply_verdicts(result["scripts"][0], verdicts)
        state["scripts"] = [updated_script]
        return state

    def test_all_pass_gives_score_1(self):
        state = self._state_with_verdicts("1. Q1\n2. Q2", ["pass", "pass"])
        result = assemble_clean_script(state)
        assert result["scripts"][0].bias_score == 1.0

    def test_all_rewrite_gives_score_0(self):
        state = self._state_with_verdicts("1. Q1\n2. Q2", ["rewrite_needed", "rewrite_needed"])
        result = assemble_clean_script(state)
        assert result["scripts"][0].bias_score == 0.0

    def test_mixed_verdicts_correct_score(self):
        """2 pass, 1 warning, 1 rewrite → 2/4 = 0.5."""
        state = self._state_with_verdicts(
            "1. Q1\n2. Q2\n3. Q3\n4. Q4",
            ["pass", "pass", "warning", "rewrite_needed"],
        )
        result = assemble_clean_script(state)
        assert result["scripts"][0].bias_score == pytest.approx(0.5)

    def test_clean_text_uses_rewrite_when_available(self):
        """For rewrite_needed questions with a rewrite, clean_text should use the rewrite."""
        state = _make_state("1. Don't you think the tool is too complex?")
        parse_result = parse_questions(state)
        script = parse_result["scripts"][0]
        # Simulate what the rewrite node would produce
        rewritten = replace(
            script.questions[0],
            verdict="rewrite_needed",
            rewrite="How would you describe the tool's complexity?",
        )
        script = replace(script, questions=[rewritten])
        state["scripts"] = [script]

        result = assemble_clean_script(state)
        clean = result["scripts"][0].clean_text
        assert "How would you describe" in clean
        assert "Don't you think" not in clean

    def test_clean_text_preserves_passing_questions(self):
        state = self._state_with_verdicts("1. Tell me about your workflow", ["pass"])
        result = assemble_clean_script(state)
        assert "Tell me about your workflow" in result["scripts"][0].clean_text

    def test_clean_text_is_numbered(self):
        state = self._state_with_verdicts("1. Q1\n2. Q2", ["pass", "pass"])
        result = assemble_clean_script(state)
        clean = result["scripts"][0].clean_text
        assert clean.startswith("1.")
        assert "2." in clean

    def test_empty_questions_gives_zero_score(self):
        state = _make_state("")
        # Override to have no questions
        state["scripts"][0] = replace(state["scripts"][0], questions=[])
        result = assemble_clean_script(state)
        assert result["scripts"][0].bias_score == 0.0


# ── Ground-truth question sets (for integration test) ────────────────────────


# 20 questions with known bias patterns — each should return verdict != "pass"
KNOWN_BIASED_QUESTIONS = [
    # Leading questions (presuppose the answer)
    "Don't you think the current workflow is too time-consuming?",
    "Wouldn't it be better if the tool automated this for you?",
    "You must find it frustrating when campaigns need manual resizing, right?",
    "Clearly you'd prefer a simpler process — what specifically bothers you?",
    "Given how inefficient your current tools are, what would you change first?",
    # Hypothetical / future-state framing
    "If we built a feature that automated creative resizing, would you use it?",
    "Imagine a world where all creative was auto-optimised — what would that look like?",
    "If you had unlimited budget, what would be the ideal solution?",
    # Solution-selling (introduces a specific solution before understanding the problem)
    "Our platform can handle cross-channel resizing automatically. Does that solve your problem?",
    "If we added AI-powered creative optimisation, would that make your job easier?",
    "Assuming we build a dynamic creative feature, how would you integrate it into your workflow?",
    # Closed questions (yes/no, kill follow-up)
    "Do you use creative automation tools?",
    "Is manual resizing a problem for your team?",
    "Have you tried any third-party creative tools?",
    "Did your last campaign meet its performance targets?",
    # Double-barrelled (asks two things at once)
    "How satisfied are you with the tool's speed and the quality of outputs?",
    "Can you describe your creative process and how it fits into campaign planning?",
    "What's most important to you — saving time or improving creative quality?",
    "Do you prefer automation or manual control, and why?",
    "How often do you brief designers and how do you track creative performance?",
]

# 10 questions that are open, exploratory, and unbiased — should return verdict == "pass"
KNOWN_CLEAN_QUESTIONS = [
    "Walk me through how you manage creative production for a typical campaign.",
    "Tell me about a recent campaign where you were happy with the creative outcome.",
    "What does your creative review process look like?",
    "How do you decide when a piece of creative is ready to go live?",
    "Can you describe a time when the creative process didn't go to plan?",
    "What tools are part of your current workflow, and how did you end up using them?",
    "How do you coordinate between your creative team and your media buyers?",
    "What does a typical week look like for you in terms of creative work?",
    "How do you measure whether creative is performing well?",
    "Tell me about a decision you made about creative strategy that you're proud of.",
]


# ── Integration test (skipped unless AWS credentials available) ────────────────


def _has_aws_credentials() -> bool:
    """Check if AWS credentials are configured (env vars or ~/.aws/credentials)."""
    import boto3

    try:
        boto3.client("sts", region_name="us-east-1").get_caller_identity()
        return True
    except Exception:
        return False


@pytest.mark.integration
@pytest.mark.skipif(
    not os.environ.get("RUN_INTEGRATION_TESTS"),
    reason="Set RUN_INTEGRATION_TESTS=1 and configure AWS credentials to run LLM tests",
)
class TestBiasDetectionAccuracy:
    """
    Accuracy test: run real LLM bias detection against 30 ground-truth questions.

    Target performance:
      - True positive rate (biased correctly flagged): ≥ 80%
      - False positive rate (clean incorrectly flagged): ≤ 20%
    """

    @pytest.fixture(scope="class")
    def analysed_results(self):
        """Run the full script review pipeline once and cache results."""
        from src.graph import build_graph
        from src.state import Script

        all_questions = KNOWN_BIASED_QUESTIONS + KNOWN_CLEAN_QUESTIONS
        raw_text = "\n".join(f"{i + 1}. {q}" for i, q in enumerate(all_questions))

        script = Script(id="test-script", study_id="test", raw_text=raw_text)
        state: StudyState = {
            "study_id": "test",
            "hypothesis": "We believe mid-market advertisers struggle with creative ops",
            "status": "active",
            "assumptions": [],
            "assumption_map_complete": False,
            "scripts": [script],
            "sessions": [],
            "observations": [],
            "themes": [],
            "insights": [],
            "decision_record": None,
            "current_flow": "script_review",
            "messages": [],
        }
        graph = build_graph()
        result = graph.invoke(state)
        return result["scripts"][0].questions

    def test_true_positive_rate_above_80_percent(self, analysed_results):
        """≥80% of known-biased questions should be flagged (not pass)."""
        biased_verdicts = analysed_results[: len(KNOWN_BIASED_QUESTIONS)]
        flagged = sum(1 for q in biased_verdicts if q.verdict != "pass")
        tp_rate = flagged / len(KNOWN_BIASED_QUESTIONS)
        assert tp_rate >= 0.80, (
            f"True-positive rate is {tp_rate:.0%} "
            f"({flagged}/{len(KNOWN_BIASED_QUESTIONS)} biased questions flagged). "
            f"Expected ≥80%."
        )

    def test_false_positive_rate_below_20_percent(self, analysed_results):
        """≤20% of known-clean questions should be incorrectly flagged."""
        clean_verdicts = analysed_results[len(KNOWN_BIASED_QUESTIONS):]
        false_flagged = sum(1 for q in clean_verdicts if q.verdict != "pass")
        fp_rate = false_flagged / len(KNOWN_CLEAN_QUESTIONS)
        assert fp_rate <= 0.20, (
            f"False-positive rate is {fp_rate:.0%} "
            f"({false_flagged}/{len(KNOWN_CLEAN_QUESTIONS)} clean questions incorrectly flagged). "
            f"Expected ≤20%."
        )

    def test_all_questions_received_a_verdict(self, analysed_results):
        total = len(KNOWN_BIASED_QUESTIONS) + len(KNOWN_CLEAN_QUESTIONS)
        assert len(analysed_results) == total
        for q in analysed_results:
            assert q.verdict in {"pass", "warning", "rewrite_needed"}, (
                f"Question '{q.original_text[:50]}' has unexpected verdict: {q.verdict}"
            )
