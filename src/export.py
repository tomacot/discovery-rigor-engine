"""
Export helpers — format study data as Markdown documents for download.

format_decision_record_md(state) — full decision record with all insights, themes,
  confidence breakdown, and tiered next steps. Used by ui/synthesis.py.

format_research_script_md(state) — research question guide with all assumptions
  grouped by risk lens plus 5 general supplementary questions.
  Used by ui/assumption_map.py.

Design: pure functions, no Streamlit imports, no LLM calls. The output is a
  Markdown string that Streamlit's st.download_button() accepts directly.
"""

from __future__ import annotations

import re
from datetime import date

from src.state import StudyState


def _slug(text: str) -> str:
    """Convert text to a URL/filename-safe slug, max 50 chars."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")[:50]


def format_decision_record_md(state: StudyState) -> str:
    """Format the full decision record as a Markdown string for download."""
    dr = state["decision_record"]
    if not dr:
        return "# No decision record available\n\nRun synthesis first."

    today = date.today().isoformat()
    study_id = state["study_id"]
    hypothesis = state["hypothesis"]

    rec_emoji = {
        "pursue": "🟢",
        "pivot": "🟡",
        "park": "🔴",
        "need_more_evidence": "🔵",
    }.get(dr.recommendation, "❓")
    rec_label = {
        "pursue": "PURSUE",
        "pivot": "PIVOT",
        "park": "PARK",
        "need_more_evidence": "NEED MORE EVIDENCE",
    }.get(dr.recommendation, dr.recommendation.upper())

    lines: list[str] = [
        f"# Decision Record: {study_id}",
        f"**Date:** {today}  **Confidence score:** {dr.confidence_score}/100",
        "",
        "---",
        "## Hypothesis",
        hypothesis,
        "",
        "---",
        f"## Recommendation: {rec_emoji} {rec_label}",
        "",
    ]

    if dr.evidence_summary:
        lines += ["## Evidence Summary", "", dr.evidence_summary, ""]

    if dr.confidence_breakdown:
        lines += ["## Confidence Score Breakdown", ""]
        lines += ["| Component | Score |", "| --- | --- |"]
        for k, v in dr.confidence_breakdown.items():
            lines.append(f"| {k.replace('_', ' ').title()} | {v:.2f} |")
        lines += [
            "",
            "_Score is deterministic — computed from evidence strength, theme saturation, "
            "counterevidence coverage, and session diversity._",
            "",
        ]

    if dr.segment_specific_insights:
        lines += ["## Segment-Specific Insights", "", dr.segment_specific_insights, ""]

    if dr.contradictions_and_open_questions:
        lines += [
            "## Contradictions and Open Questions",
            "",
            dr.contradictions_and_open_questions,
            "",
        ]

    insights = state["insights"]
    if insights:
        lines += ["---", "", f"## Insights ({len(insights)})", ""]
        for ins in insights:
            strength_tag = f"[{ins.evidence_strength.upper()}]"
            status_label = {
                "confirmed": "confirmed",
                "challenged": "challenged",
                "uncertain": "uncertain",
            }.get(ins.assumption_status, ins.assumption_status)

            lines += [f"### {strength_tag} {ins.statement}", ""]

            if ins.frequency:
                lines.append(f"**Frequency:** {ins.frequency}  ")
            lines.append(f"**Assumption status:** {status_label}  ")
            lines.append(
                f"**Priority:** `{ins.priority}` | **Actionability:** `{ins.actionability}`"
            )
            lines.append("")

            if ins.why_it_matters:
                lines += [f"> **Why it matters:** {ins.why_it_matters}", ""]

            if ins.supporting_quotes:
                lines += ["**Supporting quotes:**", ""]
                for q in ins.supporting_quotes:
                    lines.append(f'> "{q}"')
                lines.append("")

            if ins.user_segments_affected:
                lines.append(
                    f"**User segments affected:** {ins.user_segments_affected}  "
                )
            if ins.current_workarounds:
                lines.append(f"**Current workarounds:** {ins.current_workarounds}  ")

            if ins.potential_solutions:
                lines += ["", "**Potential directions to explore:**"]
                for s in ins.potential_solutions:
                    lines.append(f"- {s}")
                lines.append("")

            lines += [
                f"**Counterevidence:** {ins.counterevidence}  ",
                f"**Implication:** {ins.implication}",
                "",
                "---",
                "",
            ]

    themes = state["themes"]
    if themes:
        lines += [f"## Themes ({len(themes)})", ""]
        for t in themes:
            lines += [
                f"### {t.label}",
                f"_{t.session_count} sessions_",
                "",
                t.description,
            ]
            if t.counterevidence:
                lines.append(f"_Counterevidence: {t.counterevidence}_")
            lines.append("")

    lines += ["---", "", "## Decision Detail", ""]
    if dr.remaining_risks:
        lines += ["### Remaining Risks", "", dr.remaining_risks, ""]
    if dr.descoped_items:
        lines += ["### Descoped Items", "", dr.descoped_items, ""]
    if dr.what_not_to_do:
        lines += ["### What NOT To Do", "", dr.what_not_to_do, ""]

    lines += ["---", "", "## Next Steps", ""]
    if dr.next_steps_immediate:
        lines += ["### Immediate (do now)", "", dr.next_steps_immediate, ""]
    if dr.next_steps_short_term:
        lines += ["### Short-term (next quarter)", "", dr.next_steps_short_term, ""]
    if dr.next_steps_long_term:
        lines += ["### Long-term (future strategy)", "", dr.next_steps_long_term, ""]
    elif dr.next_steps:
        lines += [dr.next_steps, ""]

    lines += ["", "---", "", "_Generated by Discovery Rigor Engine_"]
    return "\n".join(lines)


def format_research_script_md(state: StudyState) -> str:
    """Format all assumptions with research questions as a Markdown guide for download."""
    today = date.today().isoformat()
    study_id = state["study_id"]
    hypothesis = state["hypothesis"]
    assumptions = state["assumptions"]

    lines: list[str] = [
        f"# Research Script: {study_id}",
        f"**Date:** {today}",
        "",
        "## Research Hypothesis",
        hypothesis,
        "",
        "---",
        "",
        "## Research Questions by Risk Lens",
        "",
    ]

    lens_order = ["desirability", "viability", "usability", "feasibility"]
    by_lens: dict[str, list] = {lens: [] for lens in lens_order}
    other: list = []
    for a in sorted(assumptions, key=lambda x: x.risk_score, reverse=True):
        if a.risk_lens in by_lens:
            by_lens[a.risk_lens].append(a)
        else:
            other.append(a)

    for lens in lens_order:
        group = by_lens[lens]
        if not group:
            continue
        lines += [f"### {lens.capitalize()} Assumptions", ""]
        for a in group:
            risk_tag = (
                "HIGH RISK"
                if a.risk_score >= 20
                else "MEDIUM RISK"
                if a.risk_score >= 12
                else "LOW RISK"
            )
            lines += [
                f"**{a.statement}**  ",
                f"_Risk: `{risk_tag}` (score {a.risk_score:.0f}) · "
                f"Importance {a.importance}/5 · Evidence {a.evidence_level}/5_",
            ]
            if a.research_question:
                lines += ["", f"Research question: _{a.research_question}_"]
            lines.append("")

    if other:
        lines += ["### Other Assumptions", ""]
        for a in other:
            lines.append(f"- **{a.statement}**")
            if a.research_question:
                lines.append(f"  _{a.research_question}_")
        lines.append("")

    lines += [
        "---",
        "",
        "## Supplementary Interview Questions",
        "_These general questions apply across any discovery interview:_",
        "",
        "1. Walk me through a typical week in your role — what takes up most of your time?",
        "2. What tools do you use every day, and which ones do you find yourself working around rather than with?",
        "3. Tell me about the last time something in your workflow felt genuinely broken. What happened?",
        "4. If you could change one thing about how your team makes decisions about where to invest, what would it be?",
        "5. What would have to be true for you to trust a new tool enough to make it part of your standard process?",
        "",
        "---",
        "",
        "_Generated by Discovery Rigor Engine_",
    ]
    return "\n".join(lines)


def filename_for_decision_record(state: StudyState) -> str:
    """Return a safe filename like 'adtech-study-2026-03-02.md'."""
    today = date.today().isoformat()
    return f"{_slug(state['study_id'])}-{today}.md"


def filename_for_research_script(state: StudyState) -> str:
    """Return a safe filename like 'adtech-study-research-script-2026-03-02.md'."""
    today = date.today().isoformat()
    return f"{_slug(state['study_id'])}-research-script-{today}.md"
