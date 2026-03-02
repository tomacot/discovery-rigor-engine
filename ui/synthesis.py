"""
Synthesis page — structured coding pipeline from raw notes to decision record.

Single-phase flow (one graph invocation handles all sub-steps):
  ingest_notes → open_coding → axial_coding → selective_coding → decision_record_node

The fixture study ships with pre-loaded sessions so users can run synthesis
immediately without entering raw notes. For new studies, a session entry
form is shown first.
"""

from __future__ import annotations

import uuid

import streamlit as st

from src.state import Session, StudyState
from ui.components import render_evidence_chain


def _require_study() -> StudyState | None:
    """Return current state or show an error if no study is loaded."""
    state = st.session_state.get("current_state")
    if not state:
        st.warning("No study loaded. Go to Home and load the sample study or create a new one.")
        return None
    return state


def _run_graph(flow: str, state: StudyState) -> StudyState:
    """Invoke the graph with the given flow and persist the result."""
    graph = st.session_state.graph
    updated = graph.invoke({**state, "current_flow": flow})
    st.session_state.current_state = updated
    st.session_state.store.save_study(updated)
    return updated


def render() -> None:
    """Render the synthesis interface."""
    st.title("Structured Synthesis")
    st.markdown(
        "Raw interview notes → coded observations → themes → insights → decision record. "
        "Every insight traces back to specific sessions so any claim is auditable."
    )

    state = _require_study()
    if not state:
        return

    st.markdown(f"**Hypothesis:** _{state['hypothesis']}_")
    st.divider()

    # ── Show results if synthesis is complete ─────────────────────────────────
    if state["decision_record"]:
        _render_results(state)
        if st.button("Re-run synthesis"):
            state["observations"] = []
            state["themes"] = []
            state["insights"] = []
            state["decision_record"] = None
            st.session_state.current_state = state
            st.rerun()
        return

    # ── Session management ────────────────────────────────────────────────────
    st.subheader("Research sessions")

    if state["sessions"]:
        st.markdown(f"**{len(state['sessions'])} session(s) loaded:**")
        for s in state["sessions"]:
            with st.expander(f"{s.participant_id} — {s.id}", expanded=False):
                st.text(s.raw_notes[:500] + ("…" if len(s.raw_notes) > 500 else ""))
    else:
        st.info("No sessions loaded. Add at least 2 sessions before running synthesis.")

    # Add session form
    with st.expander("Add a session", expanded=not state["sessions"]):
        participant_id = st.text_input(
            "Participant ID",
            placeholder="P1",
            help="Use anonymised IDs like P1, P2. Do not enter names.",
        )
        raw_notes = st.text_area(
            "Raw interview notes",
            height=200,
            placeholder=(
                "Key quotes, observations, and behaviours from the session.\n\n"
                "Example:\n"
                "- Participant spends 2h/week manually resizing creative for different placements\n"
                "- 'I just duplicate the campaign and tweak the image'\n"
                "- Unaware that DSP supports dynamic creative optimisation"
            ),
        )
        if st.button("Add session"):
            if not participant_id.strip() or not raw_notes.strip():
                st.warning("Both participant ID and notes are required.")
            else:
                new_session = Session(
                    id=f"session-{uuid.uuid4().hex[:8]}",
                    study_id=state["study_id"],
                    participant_id=participant_id.strip(),
                    raw_notes=raw_notes.strip(),
                )
                state["sessions"] = [*state["sessions"], new_session]
                st.session_state.current_state = state
                st.rerun()

    st.divider()

    # ── Run synthesis ─────────────────────────────────────────────────────────
    session_count = len(state["sessions"])
    if session_count < 2:
        st.warning(
            f"Synthesis requires at least 2 sessions to identify reliable themes. "
            f"You have {session_count}."
        )
        return

    st.subheader("Run synthesis pipeline")
    st.markdown(
        "The pipeline runs four passes over your data:\n"
        "1. **Open coding** — extract discrete observations per session\n"
        "2. **Axial coding** — cluster observations into themes (≥2 sessions required per theme)\n"
        "3. **Selective coding** — generate insight statements from theme clusters\n"
        "4. **Decision record** — produce a recommendation with a deterministic confidence score"
    )

    if st.button("Run synthesis", type="primary"):
        with st.spinner(
            f"Synthesising {session_count} sessions — "
            "this runs 4 LLM passes and may take 30–60 seconds…"
        ):
            state = _run_graph("synthesis", state)
        st.rerun()


def _render_results(state: StudyState) -> None:
    """Render the full synthesis output: decision record, insights, evidence chain."""
    dr = state["decision_record"]

    # ── Decision record ────────────────────────────────────────────────────────
    st.subheader("Decision Record")

    recommendation_config = {
        "pursue": ("🟢", "Pursue"),
        "pivot": ("🟡", "Pivot"),
        "park": ("🔴", "Park"),
        "need_more_evidence": ("🔵", "Need more evidence"),
    }
    emoji, label = recommendation_config.get(dr.recommendation, ("❓", dr.recommendation))

    col1, col2 = st.columns([1, 3])
    with col1:
        st.markdown(f"### {emoji} {label}")
        st.metric("Confidence score", f"{dr.confidence_score}/100")
    with col2:
        st.markdown(f"**Research question:** {dr.question}")
        if dr.evidence_summary:
            st.markdown(dr.evidence_summary)

    # Confidence breakdown
    if dr.confidence_breakdown:
        with st.expander("Confidence score breakdown", expanded=False):
            st.caption(
                "Score is deterministic — computed from evidence strength, theme saturation, "
                "counterevidence coverage, and session diversity."
            )
            for component, value in dr.confidence_breakdown.items():
                st.markdown(f"- **{component.replace('_', ' ').title()}:** `{value:.2f}`")

    col1, col2, col3 = st.columns(3)
    if dr.remaining_risks:
        col1.markdown(f"**Remaining risks**\n\n{dr.remaining_risks}")
    if dr.descoped_items:
        col2.markdown(f"**Descoped items**\n\n{dr.descoped_items}")
    if dr.next_steps:
        col3.markdown(f"**Next steps**\n\n{dr.next_steps}")

    st.divider()

    # ── Insights summary ───────────────────────────────────────────────────────
    if state["insights"]:
        st.subheader(f"Insights ({len(state['insights'])})")
        for insight in state["insights"]:
            strength_colour = {"high": "green", "medium": "orange", "low": "red"}.get(
                insight.evidence_strength, "grey"
            )
            status_emoji = {
                "confirmed": "✅",
                "challenged": "❌",
                "uncertain": "❓",
            }.get(insight.assumption_status, "")
            st.markdown(
                f":{strength_colour}[**{insight.evidence_strength.upper()}**] "
                f"{status_emoji} {insight.statement}"
            )
            if insight.counterevidence:
                st.caption(f"Counterevidence: {insight.counterevidence}")
        st.divider()

    # ── Evidence chain ─────────────────────────────────────────────────────────
    if state["insights"] and state["themes"] and state["observations"]:
        render_evidence_chain(
            state["insights"],
            state["themes"],
            state["observations"],
        )
