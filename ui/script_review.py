"""
Script Review page — bias analysis and de-biased rewrite generation.

Flow:
  1. User pastes (or uses existing) interview script text.
  2. Graph parses, analyses, and rewrites — single invocation.
  3. Results show per-question verdict cards and summary stats.

If the study already has a completed script review, the results are
shown immediately without rerunning.
"""

from __future__ import annotations

import uuid

import streamlit as st

from src.state import Script, StudyState
from ui.components import render_bias_verdict_card


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


def _latest_script(state: StudyState):
    """Return the most recent Script object, or None."""
    return state["scripts"][-1] if state["scripts"] else None


def _is_reviewed(script) -> bool:
    """Return True if the script has been through bias analysis."""
    return bool(script and script.questions and any(q.verdict for q in script.questions))


def render() -> None:
    """Render the script review interface."""
    st.title("Interview Script Review")
    st.markdown(
        "Paste your discussion guide below and the tool will flag bias patterns "
        "(leading questions, hypothetical framing, solution-selling, closed questions, "
        "and double-barrelled questions), explain each issue, and generate de-biased rewrites."
    )

    state = _require_study()
    if not state:
        return

    st.markdown(f"**Hypothesis:** _{state['hypothesis']}_")
    st.divider()

    script = _latest_script(state)

    # ── Show results if a reviewed script already exists ───────────────────────
    if _is_reviewed(script):
        _render_results(script)
        if st.button("Review a different script"):
            state["scripts"] = state["scripts"][:-1]
            st.session_state.current_state = state
            st.rerun()
        return

    # ── Input form ─────────────────────────────────────────────────────────────
    st.subheader("Paste your interview script")
    st.markdown(
        "Include the full discussion guide — numbered questions, section headers, and any "
        "probes. The tool will strip formatting and analyse each question individually."
    )

    default_text = script.raw_text if script else ""
    script_text = st.text_area(
        "Script text",
        value=default_text,
        height=300,
        placeholder=(
            "1. Tell me about your current creative workflow...\n"
            "2. How often do you run A/B tests on ad creative?\n"
            "3. Don't you think the current tools are too complex?"
        ),
    )

    if st.button("Analyse script for bias", type="primary"):
        if not script_text.strip():
            st.warning("Please paste a script before running the analysis.")
            return

        from dataclasses import replace as dc_replace

        if script:
            updated_script = dc_replace(script, raw_text=script_text.strip())
            state["scripts"] = [*state["scripts"][:-1], updated_script]
        else:
            new_script = Script(
                id=f"script-{uuid.uuid4().hex[:8]}",
                study_id=state["study_id"],
                raw_text=script_text.strip(),
            )
            state["scripts"] = [*state["scripts"], new_script]

        st.session_state.current_state = state
        with st.spinner("Parsing questions, detecting bias, generating rewrites…"):
            state = _run_graph("script_review", state)
        st.rerun()


def _render_results(script: Script) -> None:
    """Render the full bias analysis for a reviewed script."""
    total = len(script.questions)
    passed = sum(1 for q in script.questions if q.verdict == "pass")
    warned = sum(1 for q in script.questions if q.verdict == "warning")
    rewrites = sum(1 for q in script.questions if q.verdict == "rewrite_needed")

    st.subheader("Script Review Results")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total questions", total)
    col2.metric("Clean ✅", passed)
    col3.metric("Warning ⚠️", warned)
    col4.metric("Rewrite needed ❌", rewrites)

    if total > 0:
        health = round(passed / total * 100)
        colour = "green" if health >= 70 else "orange" if health >= 40 else "red"
        st.markdown(
            f"**Script health:** :{colour}[**{health}%** of questions are bias-free]"
        )

    st.divider()
    st.markdown("#### Question-by-question analysis")
    st.caption("Rewrite-needed questions are expanded by default.")

    for i, question in enumerate(script.questions):
        render_bias_verdict_card(question, i)

    if script.clean_text:
        st.divider()
        st.markdown("#### Clean script")
        st.caption("Rewrites applied. Copy this into your research plan.")
        st.text_area(
            "Clean script (read-only)",
            value=script.clean_text,
            height=300,
            disabled=True,
        )
