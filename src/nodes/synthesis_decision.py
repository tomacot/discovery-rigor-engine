"""
Synthesis decision record node.

Hybrid node: LLM generates the narrative fields (recommendation, evidence summary,
next steps, etc.); deterministic scoring computes the confidence score from
insight/theme/session data. The split ensures the narrative is coherent but the
score is always reproducible.
"""

from __future__ import annotations

from src.llm import call_llm_structured
from src.prompts.decision_record import (
    DECISION_RECORD_SYSTEM,
    DecisionNarrative,
    get_decision_record_prompt,
)
from src.scoring import compute_confidence_score
from src.state import (
    Assumption,
    DecisionRecord,
    Insight,
    Session,
    StudyState,
    Theme,
)


def decision_record_node(state: StudyState) -> dict:
    """Generate narrative via LLM and compute confidence score deterministically."""
    insights: list[Insight] = state["insights"]
    themes: list[Theme] = state["themes"]
    sessions: list[Session] = state["sessions"]
    assumptions: list[Assumption] = state["assumptions"]

    insight_dicts = [
        {
            "statement": ins.statement,
            "evidence_strength": ins.evidence_strength,
            "implication": ins.implication,
            "assumption_status": ins.assumption_status,
        }
        for ins in insights
    ]
    assumption_dicts = [
        {"id": a.id, "statement": a.statement, "status": a.status} for a in assumptions
    ]

    prompt = get_decision_record_prompt(
        insight_dicts, assumption_dicts, state["hypothesis"]
    )
    narrative: DecisionNarrative = call_llm_structured(
        prompt, DecisionNarrative, DECISION_RECORD_SYSTEM
    )

    # Deterministic confidence score — never LLM-driven
    assumptions_tested = sum(1 for a in assumptions if a.status != "untested")
    score, breakdown = compute_confidence_score(
        insights, themes, len(sessions), max(assumptions_tested, 1)
    )

    record = DecisionRecord(
        id=f"DR-{state['study_id']}",
        study_id=state["study_id"],
        question=narrative.question,
        recommendation=narrative.recommendation,
        evidence_summary=narrative.evidence_summary,
        confidence_score=score,
        confidence_breakdown=breakdown,
        descoped_items=narrative.descoped_items,
        remaining_risks=narrative.remaining_risks,
        next_steps=narrative.next_steps,
        contradictions_and_open_questions=narrative.contradictions_and_open_questions,
        what_not_to_do=narrative.what_not_to_do,
        next_steps_immediate=narrative.next_steps_immediate,
        next_steps_short_term=narrative.next_steps_short_term,
        next_steps_long_term=narrative.next_steps_long_term,
        segment_specific_insights=narrative.segment_specific_insights,
    )

    return {"decision_record": record, "status": "decided"}
