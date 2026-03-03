"""
Home page — study selection and creation.

Initialises the store and graph in st.session_state (once per browser session),
then lets the user load one of 6 sample studies, upload their own, or create a
new study from scratch.
"""

from __future__ import annotations

import json
import uuid

import streamlit as st

from src.graph import build_graph
from src.store import get_store

SAMPLE_STUDIES = {
    "Creative Asset Optimisation (AdTech)": "adtech_study",
    "Audience Segmentation Automation": "audience_segmentation",
    "Attribution Modelling Gaps": "attribution_modelling",
    "Campaign Pacing Optimisation": "campaign_pacing",
    "Creative Testing at Scale": "creative_testing",
    "Cross-Channel Frequency Management": "frequency_management",
}


def _init_session() -> None:
    """Initialise store and compiled graph in session_state if not already done."""
    if "store" not in st.session_state:
        st.session_state.store = get_store()
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

    # ── Sample studies ────────────────────────────────────────────────────────
    st.markdown("### Load a Sample Study")
    st.markdown(
        "Six pre-built AdTech studies — each with a hypothesis, 8–10 rated assumptions, "
        "a biased interview script, and 5 mock interview sessions including sceptical participants."
    )

    selected_label = st.selectbox(
        "Choose a sample study",
        list(SAMPLE_STUDIES.keys()),
        label_visibility="collapsed",
    )
    if st.button("Load Sample Study", type="primary", use_container_width=True):
        store = st.session_state.store
        fixture_name = SAMPLE_STUDIES[selected_label]
        state = store.load_fixture(fixture_name)
        st.session_state.current_state = state
        st.success(
            f"Loaded **{selected_label}** — "
            f"{len(state['assumptions'])} assumptions, {len(state['sessions'])} sessions."
        )
        st.info(
            "Navigate to Assumption Map, Script Review, or Synthesis in the sidebar."
        )

    st.divider()

    col1, col2 = st.columns(2)

    # ── New study ─────────────────────────────────────────────────────────────
    with col1:
        st.markdown("### New Study")
        st.markdown(
            "Start from scratch. Enter your own hypothesis and work through "
            "the full discovery workflow."
        )
        hypothesis = st.text_area(
            "Hypothesis",
            placeholder="We believe that [target user] struggle with [problem] because [reason]...",
            height=100,
            max_chars=2000,
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

    # ── Upload study ─────────────────────────────────────────────────────────
    with col2:
        st.markdown("### Upload Your Own Study")
        st.markdown(
            "Upload a `.json` file to load your own study data. "
            "Minimum required fields: `study_id`, `hypothesis`, and at least 2 `sessions`."
        )
        uploaded_file = st.file_uploader(
            "Upload study JSON",
            type=["json"],
            label_visibility="collapsed",
        )
        if uploaded_file is not None:
            try:
                data = json.loads(uploaded_file.read())
                store = st.session_state.store
                state = store.load_from_dict(data)
                st.session_state.current_state = state
                st.success(
                    f"Uploaded **{state['study_id']}** — "
                    f"{len(state['assumptions'])} assumptions, {len(state['sessions'])} sessions."
                )
                st.info(
                    "Navigate to Assumption Map, Script Review, or Synthesis in the sidebar."
                )
            except (json.JSONDecodeError, KeyError) as e:
                st.error(f"Could not parse JSON file: {e}")

        with st.expander("Expected JSON format", expanded=False):
            st.code(
                """{
  "study_id": "my-study-slug",
  "hypothesis": "We believe...",
  "sessions": [
    {
      "id": "SES1",
      "study_id": "my-study-slug",
      "participant_id": "P1",
      "raw_notes": "Notes from the session..."
    }
  ],
  "assumptions": [],
  "scripts": []
}""",
                language="json",
            )
        st.caption(
            "Tip: `assumptions` and `scripts` are optional — the tool generates these for you. "
            "Minimum 2 sessions are required for synthesis."
        )

    # ── Currently loaded study summary ────────────────────────────────────────
    if st.session_state.current_state:
        state = st.session_state.current_state
        st.divider()
        st.markdown("#### Currently loaded study")
        cols = st.columns(4)
        cols[0].metric("Study", state["study_id"])
        cols[1].metric("Assumptions", len(state["assumptions"]))
        cols[2].metric("Sessions", len(state["sessions"]))
        cols[3].metric("Status", state["status"])
