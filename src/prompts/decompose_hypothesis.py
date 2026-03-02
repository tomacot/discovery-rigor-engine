"""
Prompt: Decompose Hypothesis into Assumptions

Used by: src/nodes/assumption_decompose.py

Asks the LLM to break a free-text PM hypothesis into 5-10 discrete,
falsifiable assumptions. No risk lens tagging at this stage — that is
handled by the next node (categorise_risk_lens). The only job here is
extraction: find the embedded beliefs, separate them, and make each one
individually testable.

Known failure modes:
- LLM sometimes generates compound assumptions ("Users do X and also Y").
  The prompt explicitly forbids compound statements.
- For very narrow hypotheses the LLM may stop at 3-4 assumptions. The
  node retries once if len(assumptions) < 5.
"""

from pydantic import BaseModel


DECOMPOSE_SYSTEM = (
    "You are a product research expert who helps PMs decompose hypotheses "
    "into discrete, testable assumptions before conducting user research. "
    "You are rigorous, specific, and never produce vague or compound statements."
)


class AssumptionDraft(BaseModel):
    """A single falsifiable belief extracted from a hypothesis."""

    statement: str  # Plain-language testable belief, one idea only


class DecomposedAssumptions(BaseModel):
    """LLM response: the full list of assumptions extracted from a hypothesis."""

    assumptions: list[AssumptionDraft]


def get_decompose_prompt(hypothesis: str) -> str:
    """Return the user prompt asking the LLM to decompose a hypothesis into assumptions.

    Instructs the LLM to extract 5-10 discrete, falsifiable beliefs — each
    covering exactly one idea — without tagging risk lenses yet.
    """
    return f"""You are helping a PM prepare for user research by decomposing their hypothesis.

HYPOTHESIS:
{hypothesis}

TASK:
Break this hypothesis into 5-10 discrete, falsifiable assumptions. Each assumption is a single testable belief that the hypothesis depends on being true.

RULES:
- Each assumption must be independently testable (if this one turns out to be false, it materially changes the outcome)
- Each assumption covers EXACTLY ONE idea — no compound statements joined by "and" or "but"
- Write in plain language as a declarative statement, not a question
- Do NOT tag risk lenses at this stage — that comes next
- Do NOT include assumptions that are trivially obvious or unstated background facts

GOOD EXAMPLES:
- "Mid-market advertisers manage creative assets across 3 or more channels simultaneously"
- "Creative inconsistency across channels is a source of measurable campaign underperformance"
- "Current manual workflows for creative review take more than 2 hours per campaign cycle"

BAD EXAMPLES (avoid these patterns):
- "Users want the feature and will pay for it" (compound — two separate beliefs)
- "Advertising is important to businesses" (trivially true, not a testable belief about this problem)
- "Would users find it useful?" (question, not a declarative assumption)

Respond with a JSON object matching this schema:
{{
  "assumptions": [
    {{"statement": "string — one falsifiable belief"}},
    ...
  ]
}}

Extract between 5 and 10 assumptions. If the hypothesis is narrow, surface the implicit beliefs it depends on."""
