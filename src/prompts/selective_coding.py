"""
Prompt: Selective Coding — Generate Insight Statements from Themes

Used by: src/nodes/synthesis_selective.py

Selective coding is the third stage of qualitative synthesis. The LLM
receives the full set of themes and elevates them into insight statements —
what the research actually found, what it means for the product decision,
and how confident we can be in each finding.

Insights are findings, not recommendations. "Users manage creative manually
because they distrust automated suggestions" is an insight. "Build a manual
override layer" is a recommendation — that comes in the decision record.

The assumption_status field closes the loop from the first workflow step:
each insight either confirms, challenges, or leaves uncertain the assumption
it addresses. This is the mechanism that makes the tool produce a traceable
chain from hypothesis → assumption → evidence → insight → decision.

New fields (Synthesis.txt enrichment):
- supporting_quotes: extract verbatim quotes from the observation content
- frequency: "X out of Y participants" count
- why_it_matters: business/UX/strategy impact
- user_segments_affected: which participant types care most
- current_workarounds: how users solve this today
- potential_solutions: 2-3 directions to explore (not features)
- actionability: clear | fuzzy | needs_more_research
- priority: critical | high | medium | low

Known failure modes:
- LLM writes recommendations instead of findings in the statement field.
  The prompt explicitly distinguishes these and forbids recommendations here.
- evidence_strength is sometimes over-stated as "high" when session count
  doesn't support it. The prompt provides hard rules tied to session count.
- theme_indices that don't exist in the input list. The node validates these.
- supporting_quotes may be paraphrased instead of verbatim. The prompt
  instructs the LLM to use exact quotes from the observation content.
"""

from typing import Optional

from pydantic import BaseModel


SELECTIVE_CODING_SYSTEM = (
    "You are a qualitative research analyst performing selective coding — translating "
    "themes into structured insight statements. You write findings, not recommendations. "
    "You are honest about evidence strength and never overstate confidence. "
    "You extract verbatim quotes from the source material and give concrete, "
    "specific analysis rather than generic observations."
)


class InsightDraft(BaseModel):
    """A structured insight derived from one or more themes."""

    statement: str  # What we learned — a finding, not a recommendation
    evidence_strength: str  # high | medium | low
    theme_indices: list[int]  # 0-indexed positions in the themes list
    counterevidence: str  # What complicates or limits this insight
    implication: (
        str  # What this means for the product decision (not the decision itself)
    )
    assumption_id: Optional[str] = None  # Which assumption this insight addresses
    assumption_status: str  # confirmed | challenged | uncertain
    # Synthesis.txt enrichment
    supporting_quotes: list[str]  # Verbatim quotes pulled from observation content
    frequency: str  # "X out of Y participants mentioned this"
    why_it_matters: str  # Business/UX/strategy impact of this finding
    user_segments_affected: str  # Which participant types care most about this
    current_workarounds: str  # How users solve this problem today (if at all)
    potential_solutions: list[
        str
    ]  # 2-3 directions to explore (not prescriptive features)
    actionability: str  # clear | fuzzy | needs_more_research
    priority: str  # critical | high | medium | low


class SelectiveCodingResult(BaseModel):
    """LLM response: all insights generated from the theme set."""

    insights: list[InsightDraft]


def get_selective_coding_prompt(
    themes: list[dict],
    assumptions: list[dict],
    hypothesis: str,
) -> str:
    """Return the user prompt asking the LLM to generate insight statements from themes.

    themes: list of {"index": int, "label": str, "description": str, "counterevidence": str}
    assumptions: list of {"id": str, "statement": str, "risk_lens": str}
    hypothesis: the original research hypothesis for context
    """
    theme_lines = "\n".join(
        f"[{t['index']}] {t['label']}: {t['description']} "
        f"(counterevidence: {t['counterevidence']})"
        for t in themes
    )

    assumption_lines = "\n".join(
        f"- {a['id']} ({a['risk_lens']}): {a['statement']}" for a in assumptions
    )

    return f"""You are performing selective coding to generate insight statements from user research themes.

RESEARCH HYPOTHESIS:
{hypothesis}

ASSUMPTIONS BEING TESTED:
{assumption_lines}

THEMES (format: [index] label: description (counterevidence)):
{theme_lines}

TASK:
Generate one insight statement per major finding. Each insight translates one or more themes into a clear, evidence-rich statement of what the research found.

INSIGHT VS RECOMMENDATION:
An insight is a finding about the world. A recommendation is an action to take.
- Insight (correct): "Mid-market advertisers lack a single source of truth for creative performance, leading to repeated asset duplication across campaigns"
- Recommendation (wrong here): "Build a unified asset library with cross-campaign tagging"
Write insights. Save recommendations for the decision record.

EVIDENCE STRENGTH RULES (apply these strictly):
- high: Pattern appears in 3 or more sessions with consistent evidence and minimal counterevidence
- medium: Pattern appears in 2 sessions, OR appears in 3+ sessions but with notable counterevidence
- low: Pattern appears in only 1 session, is based on speculative data, or has heavy counterevidence

COUNTEREVIDENCE (required):
- Every insight must acknowledge what complicates or limits it
- A finding with significant counterevidence should be medium or low strength, not high

IMPLICATION (required):
- What does this finding mean for the product decision? (Not what to build — what to consider)

SUPPORTING QUOTES:
- Extract 1-3 verbatim quotes from the observation content provided in the themes
- Use exact words if they appear in the theme description or counterevidence
- Format as plain strings: "exact quote text here"
- If no verbatim quotes are available, use empty list

FREQUENCY:
- Count how many participants/sessions this finding appeared in
- Format: "X out of Y participants mentioned this" or "Observed in X of Y sessions"

WHY IT MATTERS:
- Explain the business, UX, or product strategy impact of this finding in 1-2 sentences
- Be specific: what does this mean for the opportunity, the user experience, or the business model?

USER SEGMENTS AFFECTED:
- Which participant types (by role, company size, or behaviour pattern) care most about this?
- Who is most and least affected by this finding?

CURRENT WORKAROUNDS:
- How do users solve this problem today, even imperfectly?
- What tools, processes, or manual steps are they using?
- "None evident from the data" is acceptable if there is no evidence of workarounds

POTENTIAL SOLUTIONS (2-3 directions):
- Suggest 2-3 directions to explore — these are approaches, NOT specific features
- Good: "automated alert when creative performance drops below threshold" — directional
- Bad: "add a notification bell icon to the dashboard" — too prescriptive

PRIORITY AND ACTIONABILITY:
- priority: How urgently does this finding need to be addressed?
  critical = must address before building anything
  high = should address in first version
  medium = important but not blocking
  low = nice-to-have consideration
- actionability: How clear is the path from this insight to a product action?
  clear = obvious what to build or change
  fuzzy = direction known but specifics unclear
  needs_more_research = more investigation needed before acting

ASSUMPTION STATUS:
For each insight, identify which assumption it most directly addresses (if any) and set:
- confirmed: The evidence clearly supports the assumption being true
- challenged: The evidence suggests the assumption is false or overstated
- uncertain: The evidence is mixed, partial, or addresses a related but different question

Respond with a JSON object matching this schema:
{{
  "insights": [
    {{
      "statement": "string — what the research found (finding, not recommendation)",
      "evidence_strength": "high | medium | low",
      "theme_indices": [0, 2, ...],
      "counterevidence": "string — what complicates or limits this insight",
      "implication": "string — what this means for the product decision",
      "assumption_id": "string or null",
      "assumption_status": "confirmed | challenged | uncertain",
      "supporting_quotes": ["verbatim quote text", ...],
      "frequency": "string — X out of Y participants",
      "why_it_matters": "string — business/UX/strategy impact",
      "user_segments_affected": "string — which participant types care most",
      "current_workarounds": "string — how users solve this today",
      "potential_solutions": ["direction 1", "direction 2"],
      "actionability": "clear | fuzzy | needs_more_research",
      "priority": "critical | high | medium | low"
    }},
    ...
  ]
}}"""
