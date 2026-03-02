"""
Script Review page — bias analysis and de-biased rewrite generation.

Flow:
  1. User selects an example script or pastes their own discussion guide.
  2. Graph parses, analyses, and rewrites — single invocation.
  3. Results show per-question verdict cards and summary stats.

If the study already has a completed script review, the results are
shown immediately without rerunning.

B7: 5 example scripts selectable from a dropdown (1 original + 4 new adtech topics).
"""

from __future__ import annotations

import uuid

import streamlit as st

from src.state import Script, StudyState
from ui.components import render_bias_verdict_card

# ── Example scripts (B7) ──────────────────────────────────────────────────────
_ADTECH_SCRIPT = """\
1. Tell me about your current creative workflow across channels.
2. How often do you update or refresh ad creative during a campaign?
3. Don't you think manual creative resizing is the biggest time sink for your team?
4. What tools do you currently use to manage creative assets across platforms?
5. Would you use a tool that automated creative adaptation if we built one for you?
6. How do you currently track creative performance — what metrics do you look at?
7. Have you ever turned off a campaign because the creative wasn't working? What happened?
8. Surely the platforms' own creative tools aren't good enough for cross-channel management, right?
9. What would your ideal creative management workflow look like if you could design it?
10. If we solved the creative problem tomorrow, what would be the next biggest workflow challenge?"""

_AUDIENCE_SEGMENTATION_SCRIPT = """\
1. Tell me about your current audience targeting approach across your campaigns.
2. Don't you think broad demographic targeting is the main reason your ROAS is underperforming?
3. How do you decide which audience segments to use for a new campaign?
4. Would you use an AI-powered segmentation tool if we built one for you?
5. How often do you review audience performance and adjust your targeting?
6. Have you ever tried to build custom audience segments from your CRM data? What happened?
7. Surely lookalike audiences aren't giving you the granularity you need, right?
8. What would a perfect audience targeting workflow look like for your team?
9. Do you think the problem is your data quality or the platform tools?
10. If we gave you better segmentation tools, would that fix your ROAS issues?"""

_ATTRIBUTION_SCRIPT = """\
1. Walk me through how your team currently measures campaign performance across channels.
2. Don't you think last-click attribution is fundamentally broken for modern multi-channel campaigns?
3. How do you decide which channels are working and which aren't?
4. Have you ever questioned whether your attribution model was giving you a misleading picture?
5. Would you switch your whole budget to awareness channels if you had better attribution data?
6. Do you use GA4 for attribution? Is it good enough for what you need, or not?
7. How do you and your CFO agree on which channels deserve more budget?
8. Surely the attribution problem is worse now than it was before iOS privacy changes?
9. What would your ideal attribution model look like if you could design it yourself?
10. How often do you change channel budget allocations and what drives those decisions?"""

_PACING_SCRIPT = """\
1. Describe how you currently manage budget pacing across your campaigns.
2. How much time per week do you spend making manual pacing adjustments?
3. Don't you think manual pacing is one of the biggest sources of wasted ad spend in your account?
4. What happens when a campaign underpaces — what's your standard response?
5. Have you ever calculated how much budget waste comes from poor pacing?
6. Would you trust an automated system to adjust your campaign budgets in real-time?
7. What would have to happen for you to feel confident in an automated pacing tool?
8. How do the pacing controls in your DSP fall short of what you actually need?
9. If you had perfect pacing, what other problems would still hold back your campaign performance?
10. What's the worst pacing situation you've had to clean up? What caused it?"""

_CREATIVE_TESTING_SCRIPT = """\
1. Tell me about your current creative testing process — what does a typical A/B test look like?
2. How many creative variants do you typically run per campaign?
3. Don't you think most advertisers are far too conservative with their creative testing?
4. What's the biggest blocker to running more creative experiments right now?
5. How do you decide when a test has enough data to call a winner?
6. Have you ever found a creative insight that genuinely changed your whole approach?
7. Would an automated creative testing tool help you run five times more experiments?
8. How do you currently track and compare creative performance across different platforms?
9. What happens to the knowledge from a creative test — how does your team capture it?
10. If you had unlimited creative production budget, would testing volume actually increase?"""

EXAMPLE_SCRIPTS: dict[str, str] = {
    "None — paste my own script": "",
    "Creative Asset Review (AdTech)": _ADTECH_SCRIPT,
    "Audience Segmentation Discovery": _AUDIENCE_SEGMENTATION_SCRIPT,
    "Attribution Methodology Interview": _ATTRIBUTION_SCRIPT,
    "Campaign Pacing Pain Points": _PACING_SCRIPT,
    "Creative Testing Habits": _CREATIVE_TESTING_SCRIPT,
}


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

    # ── Example script selector (B7) ───────────────────────────────────────────
    st.subheader("Paste your interview script")
    st.markdown(
        "Include the full discussion guide — numbered questions, section headers, and any "
        "probes. The tool will strip formatting and analyse each question individually."
    )

    selected_example = st.selectbox(
        "Load an example script to explore the tool",
        list(EXAMPLE_SCRIPTS.keys()),
    )
    example_text = EXAMPLE_SCRIPTS[selected_example]

    # Pre-fill from example, or from existing script, or leave blank
    if example_text:
        default_text = example_text
    elif script:
        default_text = script.raw_text
    else:
        default_text = ""

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
