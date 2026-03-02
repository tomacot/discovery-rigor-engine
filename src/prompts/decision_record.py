"""
Prompt: Decision Record — Narrative Synthesis for the Final Output

Used by: src/nodes/synthesis_decision.py

The decision record is the final output of the synthesis flow. It answers
the product decision question the PM started with. This prompt generates
the narrative sections — the recommendation, evidence summary, descoped
items, remaining risks, and next steps.

The confidence score (0-100) is NOT generated here. It is computed
deterministically in src/scoring.py from evidence strength, theme
saturation, counterevidence coverage, and session diversity. This
separation is intentional: the score is auditable and reproducible,
while the narrative requires judgment.

The four recommendation values map directly to product workflow outcomes:
- pursue: move to delivery planning
- pivot: reframe the hypothesis and re-research
- park: put in backlog, research higher-priority opportunities first
- need_more_evidence: design a follow-up study

Known failure modes:
- LLM sometimes writes "pursue with caveats" or similar hedged variants
  instead of the four valid values. The prompt is explicit that only the
  four values are valid, no modifications.
- evidence_summary sometimes reads as a bullet list restatement of the
  insights rather than a synthesised narrative. The prompt asks for 2-3
  paragraphs of connected narrative, not a list.
"""

from pydantic import BaseModel


DECISION_RECORD_SYSTEM = (
    "You are a product research analyst synthesising user research findings into a decision record. "
    "You write clear, evidence-grounded narratives that help PMs make confident product decisions. "
    "You are honest about uncertainty and do not oversell weak evidence."
)


class DecisionNarrative(BaseModel):
    """The narrative sections of the decision record (confidence score is separate)."""

    question: str  # The decision question being answered
    recommendation: str  # pursue | pivot | park | need_more_evidence
    evidence_summary: str  # 2-3 paragraph narrative of key findings
    descoped_items: str  # Assumptions not addressed and why they matter
    remaining_risks: str  # What could still be wrong, despite the evidence
    next_steps: str  # Recommended follow-up research or experiments


def get_decision_record_prompt(
    insights: list[dict],
    assumptions: list[dict],
    hypothesis: str,
) -> str:
    """Return the user prompt asking the LLM to write the decision record narrative.

    insights: list of {"statement": str, "evidence_strength": str, "implication": str, "assumption_status": str}
    assumptions: list of {"id": str, "statement": str, "status": str}
    hypothesis: the original research hypothesis
    """
    insight_lines = "\n".join(
        f"- [{i['evidence_strength'].upper()}] {i['statement']}\n"
        f"  Implication: {i['implication']}\n"
        f"  Assumption status: {i['assumption_status']}"
        for i in insights
    )

    assumption_lines = "\n".join(
        f"- {a['id']} [{a['status']}]: {a['statement']}" for a in assumptions
    )

    return f"""You are writing the decision record for a completed user research study.

RESEARCH HYPOTHESIS:
{hypothesis}

INSIGHTS (format: [STRENGTH] statement / implication / assumption status):
{insight_lines}

ASSUMPTION OUTCOMES:
{assumption_lines}

TASK:
Write the narrative sections of the decision record. This is the document the PM uses to explain their product decision to stakeholders.

RECOMMENDATION — choose exactly one:
- pursue: The evidence strongly supports moving forward with this direction. The core assumptions hold.
- pivot: The evidence reveals a materially different opportunity or direction. The current hypothesis is significantly off.
- park: Insufficient evidence to decide, OR the opportunity is lower priority than the evidence suggests compared to alternatives.
- need_more_evidence: The signal is promising but the research is too thin or contradictory to act on. More sessions needed.

Use EXACTLY one of these four values — no modifications, no "pursue with caveats", no hybrid answers.

SECTION GUIDANCE:

question (1 sentence):
Reframe the hypothesis as the product decision question this research was answering.
Example: "Should we invest in an automated cross-channel creative management tool for mid-market advertisers?"

evidence_summary (2-3 paragraphs of connected narrative):
Synthesise the key findings into a coherent story. Do NOT list the insights — weave them together.
Start with the strongest signal. Address counterevidence honestly. Connect findings to the hypothesis.
Write for a VP of Product who wants to understand the research without reading every insight.

descoped_items (1-2 paragraphs):
Which assumptions were NOT addressed by this research? Why does that matter for the decision?
Be honest about gaps — unaddressed assumptions are remaining risks.

remaining_risks (1-2 paragraphs):
What could still be wrong, even if you recommend pursue or pivot?
What would change your recommendation if it turned out to be true?
Include both evidence-based risks and unaddressed assumptions.

next_steps (bullet points or short paragraphs):
Concrete recommended actions. May include: follow-up research questions, experiments to run,
stakeholder reviews needed, or assumptions to test before committing to delivery.

Respond with a JSON object matching this schema:
{{
  "question": "string — the decision question",
  "recommendation": "pursue | pivot | park | need_more_evidence",
  "evidence_summary": "string — 2-3 paragraph synthesised narrative",
  "descoped_items": "string — gaps in research coverage and why they matter",
  "remaining_risks": "string — what could still invalidate this direction",
  "next_steps": "string — recommended follow-up actions"
}}"""
