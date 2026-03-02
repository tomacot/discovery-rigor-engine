"""
Assumption Map page — hypothesis decomposition, interactive rating, and prioritised output.

Two-phase flow:
  Phase 1: User provides hypothesis → graph decomposes and categorises assumptions.
  Phase 2: User rates each assumption (importance + evidence level) → graph scores
           and generates research questions for all assumptions.

The human-in-the-loop rating step happens in Streamlit sliders between the two
graph invocations, rather than via LangGraph's interrupt mechanism. Simpler.

Sliders start at LLM-estimated scores (B3) with rationale captions below each
pair (B4). A download button produces a Markdown research script once the map
is complete (B6).
"""

from __future__ import annotations

from dataclasses import replace

import streamlit as st

from src.export import filename_for_research_script, format_research_script_md
from src.state import Assumption, StudyState
from ui.components import render_assumption_matrix


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
    """Render the assumption mapping interface."""
    st.title("Assumption Map")
    st.markdown(
        "Decompose your hypothesis into testable assumptions, rate them by "
        "importance and evidence level, and surface your riskiest beliefs."
    )

    state = _require_study()
    if not state:
        return

    st.markdown(f"**Hypothesis:** _{state['hypothesis']}_")
    st.divider()

    # ── Phase 1: Decompose and categorise ──────────────────────────────────────
    if not state["assumptions"]:
        st.subheader("Step 1: Decompose your hypothesis")
        if st.button("Decompose hypothesis into assumptions", type="primary"):
            with st.spinner("Decomposing hypothesis and categorising assumptions…"):
                state = _run_graph("assumption_mapping_phase1", state)
            st.rerun()
        return

    # ── Phase 2: Interactive rating ────────────────────────────────────────────
    if not state["assumption_map_complete"]:
        st.subheader("Step 2: Rate each assumption")
        st.markdown(
            "Scores below are LLM estimates — adjust based on your own knowledge:\n"
            "- **Importance:** If this assumption is wrong, does the idea collapse? (1=peripheral, 5=core)\n"
            "- **Evidence level:** How much validated evidence already exists? (1=pure assumption, 5=well established)"
        )

        rated_assumptions: list[Assumption] = []
        for i, a in enumerate(state["assumptions"]):
            with st.expander(f"{i + 1}. [{a.risk_lens}] {a.statement}", expanded=True):
                col1, col2 = st.columns(2)
                importance = col1.slider(
                    "Importance",
                    1,
                    5,
                    max(a.importance, 1),
                    key=f"imp_{a.id}",
                    help="5 = if wrong, the entire idea collapses",
                )
                evidence = col2.slider(
                    "Evidence level",
                    1,
                    5,
                    max(a.evidence_level, 1),
                    key=f"ev_{a.id}",
                    help="5 = strong, validated evidence already exists",
                )

                # LLM-generated rationale captions (B4)
                if a.importance_rationale:
                    col1.caption(f"ℹ️ {a.importance_rationale}")
                if a.evidence_rationale:
                    col2.caption(f"ℹ️ {a.evidence_rationale}")

                rated_assumptions.append(
                    replace(a, importance=importance, evidence_level=evidence)
                )

        if st.button("Calculate risk scores and generate research questions", type="primary"):
            state["assumptions"] = rated_assumptions
            with st.spinner("Scoring assumptions and generating research questions…"):
                state = _run_graph("assumption_mapping_phase2", state)
            st.rerun()
        return

    # ── Results ────────────────────────────────────────────────────────────────
    st.subheader("Assumption Map")
    st.success("Assumption map complete.")

    top3 = sorted(state["assumptions"], key=lambda a: a.risk_score, reverse=True)[:3]
    st.markdown("#### Top 3 riskiest assumptions")
    for i, a in enumerate(top3, 1):
        st.markdown(f"**{i}. {a.statement}**")
        st.caption(f"Risk score: `{a.risk_score:.0f}` · Lens: `{a.risk_lens}`")
        if a.research_question:
            st.info(f"Research question: {a.research_question}")

    st.divider()
    render_assumption_matrix(state["assumptions"])

    # ── Download research script (B6) ─────────────────────────────────────────
    md = format_research_script_md(state)
    fname = filename_for_research_script(state)
    st.download_button(
        label="Download Research Script (.md)",
        data=md,
        file_name=fname,
        mime="text/markdown",
        help="Downloads all assumptions with research questions as a Markdown interview guide.",
    )

    if st.button("Reset assumption map"):
        state["assumptions"] = []
        state["assumption_map_complete"] = False
        st.session_state.current_state = state
        st.rerun()
