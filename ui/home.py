"""
Home page — study selection and creation.

Initialises the store and graph in st.session_state (once per browser session),
then lets the user load the adtech sample study or create a new study from scratch.
"""

from __future__ import annotations

import uuid

import streamlit as st

from src.graph import build_graph
from src.store import StudyStore


def _init_session() -> None:
    """Initialise store and compiled graph in session_state if not already done."""
    if "store" not in st.session_state:
        st.session_state.store = StudyStore()
    if "graph" not in st.session_state:
        st.session_state.graph = build_graph()
    if "current_state" not in st.session_state:
        st.session_state.current_state = None


def render() -> None:
    """Render the home page with study selection and creation options."""
    _init_session()

    st.title("Discovery Rigor Engine")
    st.markdown(
        "An agentic tool that brings process discipline to PM-led user research — "
        "from assumption mapping through synthesis to traceable decisions."
    )
    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Sample Study")
        st.markdown(
            "**Creative Asset Optimisation for Mid-Market Advertisers**\n\n"
            "Pre-loaded with a hypothesis, 10 rated assumptions, a biased interview "
            "script, and 5 mock interview sessions (P1–P5)."
        )
        if st.button("Load Sample Study", type="primary", use_container_width=True):
            store: StudyStore = st.session_state.store
            state = store.load_fixture("adtech_study")
            st.session_state.current_state = state
            st.success(f"Loaded study: **{state['study_id']}** with {len(state['assumptions'])} assumptions and {len(state['sessions'])} sessions.")
            st.info("Navigate to Assumption Map, Script Review, or Synthesis in the sidebar.")

    with col2:
        st.markdown("### New Study")
        st.markdown(
            "Start from scratch. Enter your own hypothesis and work through "
            "the full discovery workflow."
        )
        hypothesis = st.text_area(
            "Hypothesis",
            placeholder="We believe that [target user] struggle with [problem] because [reason]...",
            height=100,
        )
        if st.button("Create New Study", use_container_width=True):
            if not hypothesis.strip():
                st.warning("Please enter a hypothesis before creating a study.")
            else:
                store = st.session_state.store
                study_id = f"study-{uuid.uuid4().hex[:8]}"
                state = store.create_study(study_id, hypothesis.strip())
                st.session_state.current_state = state
                st.success(f"Created new study: `{study_id}`")
                st.info("Start with Assumption Map in the sidebar.")

    # Show currently loaded study summary
    if st.session_state.current_state:
        state = st.session_state.current_state
        st.divider()
        st.markdown("#### Currently loaded study")
        cols = st.columns(4)
        cols[0].metric("Study", state["study_id"])
        cols[1].metric("Assumptions", len(state["assumptions"]))
        cols[2].metric("Sessions", len(state["sessions"]))
        cols[3].metric("Status", state["status"])
