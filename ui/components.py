"""
Shared UI components used across multiple pages.

Each component takes domain objects and renders them using Streamlit.
No business logic — purely presentation.
"""

from __future__ import annotations

import streamlit as st

from src.state import Assumption, DecisionRecord, Insight, Observation, ScriptQuestion, Theme


def render_assumption_matrix(assumptions: list[Assumption]) -> None:
    """Render assumptions as a sortable table with risk-level colour coding."""
    if not assumptions:
        return

    st.markdown("#### Assumption Risk Rankings")
    for a in sorted(assumptions, key=lambda x: x.risk_score, reverse=True):
        risk_emoji = "🔴" if a.risk_score >= 20 else "🟡" if a.risk_score >= 12 else "🟢"
        lens_colour = {
            "desirability": "blue",
            "usability": "orange",
            "feasibility": "violet",
            "viability": "green",
        }.get(a.risk_lens, "grey")

        st.markdown(
            f"{risk_emoji} **{a.statement}**  \n"
            f":{lens_colour}[{a.risk_lens}] · "
            f"Importance `{a.importance}/5` · Evidence `{a.evidence_level}/5` · "
            f"Risk score `{a.risk_score:.0f}`"
        )
        if a.research_question:
            st.caption(f"Research question: _{a.research_question}_")
        st.divider()


def render_bias_verdict_card(question: ScriptQuestion, index: int) -> None:
    """Render one interview question with its bias verdict, explanation, and rewrite."""
    verdict_config = {
        "pass": ("✅", "Pass"),
        "warning": ("⚠️", "Warning"),
        "rewrite_needed": ("❌", "Rewrite needed"),
    }
    emoji, label = verdict_config.get(question.verdict, ("❓", "Pending"))
    expand = question.verdict == "rewrite_needed"
    preview = question.original_text[:80] + ("…" if len(question.original_text) > 80 else "")

    with st.expander(f"{emoji} Q{index + 1}: {preview}", expanded=expand):
        st.markdown(f"**Original:** {question.original_text}")

        if question.issue_types:
            tags = "  ".join(f"`{t}`" for t in question.issue_types)
            st.markdown(f"**Bias patterns:** {tags}")

        if question.explanation:
            st.info(question.explanation)

        if question.rewrite:
            st.success(f"**Suggested rewrite:** {question.rewrite}")
        elif question.verdict == "pass":
            st.caption("No changes needed.")


def render_evidence_chain(
    insights: list[Insight],
    themes: list[Theme],
    observations: list[Observation],
) -> None:
    """Render the traceable chain: insight → theme → observation → raw notes."""
    st.markdown("### Evidence Chain")
    st.caption("Trace any claim in the decision record back to raw interview data.")

    theme_by_id = {t.id: t for t in themes}
    obs_by_id = {o.id: o for o in observations}

    for insight in insights:
        with st.expander(f"💡 {insight.statement}", expanded=False):
            col1, col2 = st.columns([1, 3])
            with col1:
                strength_colour = {"high": "green", "medium": "orange", "low": "red"}.get(
                    insight.evidence_strength, "grey"
                )
                st.markdown(f":{strength_colour}[**{insight.evidence_strength.upper()} evidence**]")
            with col2:
                if insight.implication:
                    st.markdown(f"**Implication:** {insight.implication}")

            if insight.counterevidence:
                st.warning(f"**Counterevidence:** {insight.counterevidence}")

            st.markdown("**Themes:**")
            for theme_id in insight.theme_ids:
                theme = theme_by_id.get(theme_id)
                if not theme:
                    continue
                st.markdown(f"— 🏷️ **{theme.label}** ({theme.session_count} sessions)")
                st.caption(theme.description)
                for obs_id in theme.observation_ids[:3]:
                    obs = obs_by_id.get(obs_id)
                    if obs:
                        st.caption(f"    › `[{obs.type}]` {obs.content[:120]}")
