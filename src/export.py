"""
Export helpers — format study data as Markdown documents for download.

format_decision_record_md(state) — full decision record with all insights, themes,
  confidence breakdown, and tiered next steps. Used by ui/synthesis.py.

format_research_script_md(state) — 7-section interview guide with assumptions slotted
  by risk lens, inline interviewer tips, and timing estimates.
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
    """Format all assumptions as a 7-section interview guide for download.

    Sections map assumptions to research methodology phases:
      Sections 1-2: Fixed setup and workflow grounding (no assumptions)
      Section 3: Desirability assumptions — problem validation
      Section 4: Usability assumptions — friction and workarounds
      Section 5: Concept fit — viability + feasibility assumptions
      Sections 6-7: Fixed prioritisation and wrap-up (no assumptions)

    Assumptions within each section are sorted by risk_score descending so the
    most critical questions come first.
    """
    today = date.today().isoformat()
    study_id = state["study_id"]
    hypothesis = state["hypothesis"]
    assumptions = state["assumptions"]
    session_count = len(state.get("sessions", []))

    # Bucket assumptions by risk lens, sorted by risk score descending
    by_lens: dict[str, list] = {
        "desirability": [],
        "usability": [],
        "viability": [],
        "feasibility": [],
    }
    for a in sorted(assumptions, key=lambda x: x.risk_score, reverse=True):
        if a.risk_lens in by_lens:
            by_lens[a.risk_lens].append(a)

    def _assumption_block(a) -> list[str]:
        """Format one assumption as a research question block."""
        risk_tag = (
            "HIGH RISK"
            if a.risk_score >= 20
            else "MEDIUM RISK"
            if a.risk_score >= 12
            else "LOW RISK"
        )
        block = [
            f"**Assumption:** {a.statement}  ",
            f"_Risk: `{risk_tag}` (score {a.risk_score:.0f}) · "
            f"Importance {a.importance}/5 · Evidence {a.evidence_level}/5_",
        ]
        if a.research_question:
            block += ["", f"**Ask:** _{a.research_question}_"]
        block.append("")
        return block

    lines: list[str] = [
        f"# Interview Guide: {study_id}",
        f"**Date:** {today}  |  "
        f"**Duration:** 60–90 min  |  "
        f"**Sessions completed:** {session_count}",
        "",
        "## Research Hypothesis",
        f"_{hypothesis}_",
        "",
        "---",
        "",
        # ── Section 1: Intro & Setup ──────────────────────────────────────────
        "## Section 1: Intro & Setup (~5 min)",
        "",
        "> **Interviewer note:** Introduce yourself and the research purpose. "
        "Make clear you are studying the problem space, not testing a solution. "
        "Obtain recording consent before starting.",
        "",
        "- \"Thanks for making the time. We're doing research to understand [topic area] — "
        "specifically the workflows and pain points your team deals with. "
        "I'll be asking about your experience, not evaluating any product. "
        'Is it OK if I record this for note-taking purposes?"',
        '- "Can you briefly describe your role and what a typical week looks like for you?"',
        '- "How long have you been in this role, and what did you do before?"',
        "",
        "---",
        "",
        # ── Section 2: Workflow Grounding ─────────────────────────────────────
        "## Section 2: Workflow Grounding (~10 min)",
        "",
        "> **Interviewer note:** Establish current-state before probing pain. "
        "Listen for tools, handoffs, time sinks, and who else is involved. "
        "Do not assume any particular workflow — let them show you theirs.",
        "",
        '- "Walk me through how you currently handle [workflow area]. '
        'Start from the beginning of a typical cycle."',
        '- "What tools are involved at each stage?"',
        '- "Where do handoffs happen — who else touches this process?"',
        '- "Which part of this takes the most time or causes the most friction?"',
        "",
        "---",
        "",
        # ── Section 3: Desirability ───────────────────────────────────────────
        "## Section 3: Desirability — Problem Validation (~15 min)",
        "",
        "> **Interviewer note:** Stay in past behaviour — ask about specific "
        "incidents, not general opinions. "
        'Use "tell me about the last time" rather than hypotheticals. '
        "If they give a vague answer, probe: "
        '"Can you walk me through a specific example of that?"',
        "",
    ]

    if by_lens["desirability"]:
        for a in by_lens["desirability"]:
            lines += _assumption_block(a)
    else:
        lines += [
            '- "Tell me about the last time [problem area] caused a real issue for your team. '
            'What happened?"',
            '- "How often does this come up, and what\'s the downstream impact when it does?"',
            "",
        ]

    lines += [
        "---",
        "",
        # ── Section 4: Usability ──────────────────────────────────────────────
        "## Section 4: Friction & Workarounds (~10 min)",
        "",
        "> **Interviewer note:** Probe for workarounds — they reveal unmet needs more "
        "reliably than stated preferences. "
        "Don't accept \"it's fine\" — ask what they do when it isn't. "
        "Time spent on workarounds is a proxy for pain severity.",
        "",
    ]

    if by_lens["usability"]:
        for a in by_lens["usability"]:
            lines += _assumption_block(a)
    else:
        lines += [
            '- "What do you do when [problem] happens — what\'s your workaround?"',
            '- "How much time per week does that workaround take?"',
            "",
        ]

    lines += [
        '- "What would you have to stop doing if you had to reduce time spent on this by half?"',
        "",
        "---",
        "",
        # ── Section 5: Concept Fit ────────────────────────────────────────────
        "## Section 5: Concept Fit (~10 min)",
        "",
        "> **Interviewer note:** This section tests viability and feasibility — "
        "budget authority, integration constraints, and strategic fit. "
        "Focus on constraints and decision-making process, not feature preferences. "
        "Do not pitch a solution; probe whether the space is investable.",
        "",
    ]

    for a in by_lens["viability"] + by_lens["feasibility"]:
        lines += _assumption_block(a)

    if not by_lens["viability"] and not by_lens["feasibility"]:
        lines += [
            '- "Who owns the budget for tooling in this space? '
            'What would it take to get a new solution approved?"',
            '- "What does your current vendor contract situation look like — '
            'are you locked in anywhere?"',
            "",
        ]

    lines += [
        "---",
        "",
        # ── Section 6: Prioritisation ─────────────────────────────────────────
        "## Section 6: Prioritisation (~5 min)",
        "",
        "> **Interviewer note:** Force-rank to distinguish real priorities from "
        "polite agreement. "
        "Most participants will say everything matters — push them to choose.",
        "",
        "- \"Of all the challenges we've discussed today, which is the single most "
        'important one to solve for your team right now?"',
        '- "If you could fix one thing in your workflow tomorrow — just one — what would it be?"',
        '- "What would success look like 6 months from now if this problem were solved?"',
        "",
        "---",
        "",
        # ── Section 7: Wrap-Up ────────────────────────────────────────────────
        "## Section 7: Wrap-Up (~5 min)",
        "",
        "> **Interviewer note:** Leave space for surprises — the most important "
        "insight sometimes comes in the last two minutes. "
        "Always ask for referrals; a warm introduction to a peer takes 10 seconds "
        "and can unlock your next interview.",
        "",
        '- "Is there anything important we haven\'t covered that you think I should know?"',
        '- "Is there anyone else on your team — or someone you know at another company — '
        'who deals with these challenges? Could you introduce us?"',
        "- \"What's the one thing you'd want a product team to understand about your "
        "day-to-day that most people outside your role don't get?\"",
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
