"""
Shared UI components used across multiple pages.

Each component takes domain objects and renders them using Streamlit.
No business logic — purely presentation.
"""

from __future__ import annotations

import streamlit as st

from src.state import Assumption, Insight, Observation, ScriptQuestion, Session, Theme

RISK_LENS_EXPLANATIONS: dict[str, str] = {
    "desirability": "Does anyone want this? Tests whether the problem is real and whether users would adopt a solution.",
    "usability": "Can users figure it out? Tests whether the interaction or workflow is intuitive without friction.",
    "feasibility": "Can we build it? Tests technical, operational, or resource constraints on delivering this.",
    "viability": "Should we build it? Tests business model, pricing, revenue, or strategic fit.",
}


def render_assumption_matrix(assumptions: list[Assumption]) -> None:
    """Render assumptions as a sortable table with risk-level colour coding."""
    if not assumptions:
        return

    st.markdown("#### Assumption Risk Rankings")
    for a in sorted(assumptions, key=lambda x: x.risk_score, reverse=True):
        risk_emoji = (
            "🔴" if a.risk_score >= 20 else "🟡" if a.risk_score >= 12 else "🟢"
        )
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
    preview = question.original_text[:80] + (
        "…" if len(question.original_text) > 80 else ""
    )

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
    sessions: list[Session] | None = None,
) -> None:
    """Render the traceable chain: insight → theme → observation → session excerpt.

    3-level nested drill-down (A4):
      Level 1 — Insight expander: statement, strength, why_it_matters, supporting quotes
      Level 2 — Theme expander: label, session count, description, counterevidence
      Level 3 — Observation + Session expander: tagged observation + first 800 chars of raw notes

    The optional sessions arg enables the third level (raw notes excerpt).
    Without it, the chain still works but stops at the observation level.
    """
    st.markdown("### Evidence Chain")
    st.caption("Trace any claim in the decision record back to raw interview data.")

    theme_by_id = {t.id: t for t in themes}
    obs_by_id = {o.id: o for o in observations}
    session_by_id: dict[str, Session] = {s.id: s for s in (sessions or [])}

    for insight in insights:
        with st.expander(f"💡 {insight.statement}", expanded=False):
            col1, col2 = st.columns([1, 3])
            with col1:
                strength_colour = {
                    "high": "green",
                    "medium": "orange",
                    "low": "red",
                }.get(insight.evidence_strength, "grey")
                st.markdown(
                    f":{strength_colour}[**{insight.evidence_strength.upper()} evidence**]"
                )
                if insight.priority:
                    priority_colour = {
                        "critical": "red",
                        "high": "orange",
                        "medium": "blue",
                        "low": "grey",
                    }.get(insight.priority, "grey")
                    st.markdown(f":{priority_colour}[Priority: **{insight.priority}**]")
            with col2:
                if insight.implication:
                    st.markdown(f"**Implication:** {insight.implication}")

            if insight.why_it_matters:
                st.info(f"**Why it matters:** {insight.why_it_matters}")

            if insight.supporting_quotes:
                st.markdown("**Supporting quotes:**")
                for q in insight.supporting_quotes:
                    st.markdown(f'> *"{q}"*')

            if insight.frequency:
                st.caption(f"Frequency: {insight.frequency}")

            if insight.counterevidence:
                st.warning(f"**Counterevidence:** {insight.counterevidence}")

            # Level 2 — Themes
            if insight.theme_ids:
                st.markdown("---")
                st.markdown("**Themes contributing to this insight:**")
                for theme_id in insight.theme_ids:
                    theme = theme_by_id.get(theme_id)
                    if not theme:
                        continue

                    with st.expander(
                        f"🏷️ {theme.label} — {theme.session_count} sessions",
                        expanded=False,
                    ):
                        st.markdown(theme.description)
                        if (
                            theme.counterevidence
                            and theme.counterevidence.lower() != "none found"
                        ):
                            st.caption(f"Counterevidence: {theme.counterevidence}")

                        # Level 3 — Observations + optional session excerpt
                        for obs_id in theme.observation_ids[:5]:
                            obs = obs_by_id.get(obs_id)
                            if not obs:
                                continue

                            obs_preview = obs.content[:100] + (
                                "…" if len(obs.content) > 100 else ""
                            )
                            with st.expander(
                                f"📋 [{obs.type}] {obs_preview}",
                                expanded=False,
                            ):
                                st.markdown(
                                    f"**Type:** `{obs.type}` · **Session:** `{obs.session_id}`"
                                )
                                st.markdown(obs.content)

                                session = session_by_id.get(obs.session_id)
                                if session:
                                    with st.expander(
                                        f"📄 Raw notes — {session.participant_id}",
                                        expanded=False,
                                    ):
                                        excerpt = session.raw_notes[:800]
                                        if len(session.raw_notes) > 800:
                                            excerpt += (
                                                "\n\n_[truncated — 800 chars shown]_"
                                            )
                                        st.text(excerpt)


def render_progress_tracker(state) -> None:
    """Show workflow completion status in the sidebar.

    Three steps mirror the three capabilities. Each step is ticked once
    its primary output exists in state — deterministic, no LLM needed.
    """
    if not state:
        return

    scripts = state.get("scripts", [])
    script_reviewed = bool(scripts and any(s.questions for s in scripts))

    steps = [
        ("Assumption Map", bool(state.get("assumption_map_complete"))),
        ("Script Review", script_reviewed),
        ("Synthesis", bool(state.get("decision_record"))),
    ]

    st.sidebar.markdown("---")
    st.sidebar.markdown("**Workflow progress**")
    for label, done in steps:
        icon = "✅" if done else "⬜"
        st.sidebar.markdown(f"{icon} {label}")
