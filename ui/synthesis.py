"""
Synthesis page — structured coding pipeline from raw notes to decision record.

Single-phase flow (one graph invocation handles all sub-steps):
  ingest_notes → open_coding → axial_coding → selective_coding → decision_record_node

The fixture study ships with pre-loaded sessions so users can run synthesis
immediately without entering raw notes. For new studies, a session entry
form is shown first.

Results are shown in three tabs (B8 / A2):
  Decision — recommendation, confidence score, evidence summary, contradictions, next steps
  Insights — rich insight cards (quotes, frequency, why_it_matters, segments, workarounds, solutions)
  Evidence Chain — 3-level nested drill-down (A4)

A download button exports the full decision record as Markdown (A3).
"""

from __future__ import annotations

import re
import uuid
from pathlib import Path

import streamlit as st

from src.export import filename_for_decision_record, format_decision_record_md
from src.state import Session, StudyState
from ui.components import render_evidence_chain


def _extract_participant_id(filename: str) -> str:
    """Derive a participant ID from an uploaded filename.

    Scans the filename stem for a P-number pattern (e.g. P1, p2, participant3).
    Falls back to the full stem if no match is found.

    Examples:
        P1.txt              -> P1
        p2_interview.txt    -> P2
        participant3.txt    -> P3
        session_notes.txt   -> session_notes
    """
    stem = Path(filename).stem
    match = re.search(r"[Pp](?:articipant)?(\d+)", stem)
    if match:
        return f"P{match.group(1)}"
    return stem


def _require_study() -> StudyState | None:
    """Return current state or show an error if no study is loaded."""
    state = st.session_state.get("current_state")
    if not state:
        st.warning(
            "No study loaded. Go to Home and load the sample study or create a new one."
        )
        return None
    return state


def _run_graph(flow: str, state: StudyState) -> StudyState:
    """Invoke the graph with the given flow and persist the result."""
    graph = st.session_state.graph
    updated = graph.invoke({**state, "current_flow": flow})
    st.session_state.current_state = updated
    st.session_state.store.save_study(updated)
    return updated


_SYNTHESIS_NODE_LABELS = {
    "ingest_notes": "Ingesting session notes",
    "open_coding": "Open coding: extracting observations per session",
    "axial_coding": "Axial coding: clustering observations into themes",
    "selective_coding": "Selective coding: generating insight statements",
    "decision_record_node": "Generating decision record and confidence score",
}


def _run_synthesis_streaming(state: StudyState) -> StudyState:
    """Run synthesis using graph.stream() so each node completion triggers a status update.

    graph.stream(stream_mode="updates") yields {node_name: state_update_dict} after
    each node finishes. We accumulate updates into a running state so that after the
    last node, we have the full final state without a second graph.invoke() call.

    Why not token streaming: the 4 LLM nodes all use call_llm_structured() which goes
    through Bedrock's tool-use API. Tool-use responses arrive as a single JSON block,
    not as readable token chunks — there is nothing to stream at the token level for
    structured output. Node-level progress (this function) is what users actually see.
    """
    graph = st.session_state.graph
    current: StudyState = {**state, "current_flow": "synthesis"}  # type: ignore[misc]

    with st.status("Running synthesis pipeline…", expanded=True) as status:
        for chunk in graph.stream(current, stream_mode="updates"):
            for node_name, updates in chunk.items():
                label = _SYNTHESIS_NODE_LABELS.get(node_name, node_name)
                st.write(f"✓ {label}")
                current = {**current, **updates}  # type: ignore[misc]
        status.update(label="Synthesis complete!", state="complete", expanded=False)

    st.session_state.current_state = current
    st.session_state.store.save_study(current)
    return current


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
                st.text_area(
                    "Notes",
                    value=s.raw_notes,
                    height=300,
                    disabled=True,
                    label_visibility="collapsed",
                    key=f"notes_display_{s.id}",
                )
    else:
        st.info("No sessions loaded. Add at least 2 sessions before running synthesis.")

    # Upload transcript files
    with st.expander("Upload transcript files (.txt)", expanded=False):
        st.caption(
            "Upload one .txt file per participant. Name files P1.txt, P2.txt, etc. "
            "for automatic participant ID detection — or any filename works and you can "
            "rename the ID before importing."
        )
        uploaded_files = st.file_uploader(
            "Transcripts",
            type=["txt"],
            accept_multiple_files=True,
            label_visibility="collapsed",
            key="transcript_uploader",
        )
        if uploaded_files:
            preview = [
                {
                    "File": f.name,
                    "Detected participant ID": _extract_participant_id(f.name),
                    "Characters": f"{f.size:,}",
                }
                for f in uploaded_files
            ]
            st.table(preview)
            if st.button(
                f"Import {len(uploaded_files)} session(s) from files", type="primary"
            ):
                new_sessions = []
                for f in uploaded_files:
                    new_sessions.append(
                        Session(
                            id=f"session-{uuid.uuid4().hex[:8]}",
                            study_id=state["study_id"],
                            participant_id=_extract_participant_id(f.name),
                            raw_notes=f.read().decode("utf-8").strip(),
                        )
                    )
                state["sessions"] = [*state["sessions"], *new_sessions]
                st.session_state.current_state = state
                st.rerun()

    # Add session form
    with st.expander("Add a session", expanded=not state["sessions"]):
        participant_id = st.text_input(
            "Participant ID",
            placeholder="P1",
            help="Use anonymised IDs like P1, P2. Do not enter names.",
        )
        raw_notes = st.text_area(
            "Raw interview notes",
            height=350,
            max_chars=10000,
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
        state = _run_synthesis_streaming(state)
        st.rerun()


def _render_results(state: StudyState) -> None:
    """Render the full synthesis output across three tabs: Decision, Insights, Evidence Chain."""
    dr = state["decision_record"]

    tab_decision, tab_insights, tab_evidence = st.tabs(
        ["Decision", "Insights", "Evidence Chain"]
    )

    # ── Tab 1: Decision ────────────────────────────────────────────────────────
    with tab_decision:
        _render_decision_tab(dr)

    # ── Tab 2: Insights ────────────────────────────────────────────────────────
    with tab_insights:
        _render_insights_tab(state)

    # ── Tab 3: Evidence Chain ──────────────────────────────────────────────────
    with tab_evidence:
        if state["insights"] and state["themes"] and state["observations"]:
            render_evidence_chain(
                state["insights"],
                state["themes"],
                state["observations"],
                state["sessions"],
            )
        else:
            st.info("No evidence chain available yet.")

    # ── Download button ────────────────────────────────────────────────────────
    st.divider()
    md = format_decision_record_md(state)
    fname = filename_for_decision_record(state)
    st.download_button(
        label="Download Decision Record (.md)",
        data=md,
        file_name=fname,
        mime="text/markdown",
        help="Full decision record with insights, themes, and next steps as a Markdown document.",
    )

    st.divider()
    st.info(
        "**Done:** Export your decision record above, or start a new study from the home page."
    )
    if st.button("Go to Home →", key="nav_synthesis_to_home"):
        st.session_state["sidebar_nav"] = "Home"
        st.rerun()


def _render_decision_tab(dr) -> None:
    """Render the decision record: recommendation, evidence summary, next steps."""
    recommendation_config = {
        "pursue": ("🟢", "Pursue"),
        "pivot": ("🟡", "Pivot"),
        "park": ("🔴", "Park"),
        "need_more_evidence": ("🔵", "Need more evidence"),
    }
    emoji, label = recommendation_config.get(
        dr.recommendation, ("❓", dr.recommendation)
    )

    col1, col2 = st.columns([1, 3])
    with col1:
        st.markdown(f"### {emoji} {label}")
        st.metric("Confidence score", f"{dr.confidence_score}/100")
    with col2:
        st.markdown(f"**Research question:** {dr.question}")
        if dr.evidence_summary:
            st.markdown(dr.evidence_summary)

    if dr.confidence_breakdown:
        with st.expander("Confidence score breakdown", expanded=False):
            st.caption(
                "Score is deterministic — computed from evidence strength, theme saturation, "
                "counterevidence coverage, and session diversity."
            )
            for component, value in dr.confidence_breakdown.items():
                st.markdown(
                    f"- **{component.replace('_', ' ').title()}:** `{value:.2f}`"
                )

    if dr.segment_specific_insights:
        st.markdown("#### Segment-Specific Insights")
        st.markdown(dr.segment_specific_insights)

    if dr.contradictions_and_open_questions:
        st.markdown("#### Contradictions & Open Questions")
        st.markdown(dr.contradictions_and_open_questions)

    st.divider()
    st.markdown("#### Next Steps")
    col1, col2, col3 = st.columns(3)
    if dr.next_steps_immediate:
        col1.markdown("**Immediate (do now)**")
        col1.markdown(dr.next_steps_immediate)
    if dr.next_steps_short_term:
        col2.markdown("**Short-term (next quarter)**")
        col2.markdown(dr.next_steps_short_term)
    if dr.next_steps_long_term:
        col3.markdown("**Long-term (future strategy)**")
        col3.markdown(dr.next_steps_long_term)
    # Fall back to legacy field if new fields are empty
    if not any(
        [dr.next_steps_immediate, dr.next_steps_short_term, dr.next_steps_long_term]
    ):
        if dr.next_steps:
            st.markdown(dr.next_steps)

    st.divider()
    col1, col2, col3 = st.columns(3)
    if dr.remaining_risks:
        col1.markdown(f"**Remaining risks**\n\n{dr.remaining_risks}")
    if dr.descoped_items:
        col2.markdown(f"**Descoped items**\n\n{dr.descoped_items}")
    if dr.what_not_to_do:
        col3.markdown(f"**What NOT to do**\n\n{dr.what_not_to_do}")


def _render_insights_tab(state: StudyState) -> None:
    """Render rich insight cards with quotes, frequency, why_it_matters, workarounds, solutions."""
    insights = state["insights"]
    if not insights:
        st.info("No insights generated yet.")
        return

    st.markdown(
        f"**{len(insights)} insight(s) from {len(state['sessions'])} sessions**"
    )

    for insight in insights:
        strength_colour = {"high": "green", "medium": "orange", "low": "red"}.get(
            insight.evidence_strength, "grey"
        )
        priority_colour = {
            "critical": "red",
            "high": "orange",
            "medium": "blue",
            "low": "grey",
        }.get(insight.priority, "grey")
        status_emoji = {
            "confirmed": "✅",
            "challenged": "❌",
            "uncertain": "❓",
        }.get(insight.assumption_status, "")
        actionability_colour = {
            "clear": "green",
            "fuzzy": "orange",
            "needs_more_research": "red",
        }.get(insight.actionability, "grey")

        with st.expander(
            f":{strength_colour}[**{insight.evidence_strength.upper()}**] "
            f"{status_emoji} {insight.statement}",
            expanded=False,
        ):
            # Badge row
            badge_parts = [
                f":{priority_colour}[Priority: **{insight.priority}**]",
                f":{actionability_colour}[Actionability: **{insight.actionability}**]",
            ]
            if insight.frequency:
                badge_parts.append(f"`{insight.frequency}`")
            st.markdown("  ·  ".join(badge_parts))

            if insight.why_it_matters:
                st.info(f"**Why it matters:** {insight.why_it_matters}")

            if insight.supporting_quotes:
                st.markdown("**Supporting quotes:**")
                for q in insight.supporting_quotes:
                    st.markdown(f'> *"{q}"*')

            col1, col2 = st.columns(2)
            if insight.user_segments_affected:
                col1.markdown(
                    f"**Segments affected:**  \n{insight.user_segments_affected}"
                )
            if insight.current_workarounds:
                col2.markdown(
                    f"**Current workarounds:**  \n{insight.current_workarounds}"
                )

            if insight.potential_solutions:
                st.markdown("**Potential directions to explore:**")
                for s in insight.potential_solutions:
                    st.markdown(f"- {s}")

            st.divider()
            st.caption(f"Counterevidence: {insight.counterevidence}")
            st.caption(f"Implication: {insight.implication}")
