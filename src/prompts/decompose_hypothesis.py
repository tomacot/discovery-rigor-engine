"""
Prompt: Decompose Hypothesis into Assumptions

Used by: src/nodes/assumption_decompose.py

Asks the LLM to break a free-text PM hypothesis into 5-10 discrete,
falsifiable assumptions. Also estimates importance (1-5) and evidence level
(1-5) for each assumption, with a one-sentence rationale for each estimate.
These estimates seed the interactive rating sliders so users start from an
intelligent default rather than zero.

No risk lens tagging at this stage — that is handled by the next node
(categorise_risk_lens). The only job here is extraction + initial scoring.

Known failure modes:
- LLM sometimes generates compound assumptions ("Users do X and also Y").
  The prompt explicitly forbids compound statements.
- For very narrow hypotheses the LLM may stop at 3-4 assumptions. The
  node retries once if len(assumptions) < 5.
- LLM occasionally rates all assumptions as importance=5. The prompt
  anchors the scale with examples to counter this.
"""

from pydantic import BaseModel


DECOMPOSE_SYSTEM = (
    "You are a product research expert who helps PMs decompose hypotheses "
    "into discrete, testable assumptions before conducting user research. "
    "You are rigorous, specific, and never produce vague or compound statements. "
    "You estimate importance and evidence levels accurately and honestly."
)


class AssumptionDraft(BaseModel):
    """A single falsifiable belief extracted from a hypothesis, with score estimates."""

    statement: str  # Plain-language testable belief, one idea only
    estimated_importance: int  # 1-5: how critical to the hypothesis being true
    estimated_evidence_level: int  # 1-5: how much prior evidence exists for this
    importance_rationale: str  # One sentence: why this importance level
    evidence_rationale: str  # One sentence: why this evidence level


class DecomposedAssumptions(BaseModel):
    """LLM response: the full list of assumptions extracted from a hypothesis."""

    assumptions: list[AssumptionDraft]


def get_decompose_prompt(hypothesis: str) -> str:
    """Return the user prompt asking the LLM to decompose a hypothesis into assumptions.

    Instructs the LLM to extract 5-10 discrete, falsifiable beliefs — each
    covering exactly one idea — and estimate importance and evidence scores
    for each to seed the interactive rating step.
    """
    return f"""You are helping a PM prepare for user research by decomposing their hypothesis.

HYPOTHESIS:
{hypothesis}

TASK:
Break this hypothesis into 5-10 discrete, falsifiable assumptions. Each assumption is a single testable belief that the hypothesis depends on being true. For each assumption, also estimate its importance and current evidence level.

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

IMPORTANCE SCALE (estimated_importance):
Rate how critical this assumption is to the hypothesis being valid. If this assumption turns out to be false, does the entire idea collapse?
- 5 = Core to the hypothesis — if false, the whole idea collapses
- 4 = Very important — if false, significantly weakens the case
- 3 = Moderately important — if false, weakens but doesn't destroy the case
- 2 = Peripheral — if false, minor adjustment needed
- 1 = Nice-to-know — if false, minimal impact on the hypothesis

EVIDENCE LEVEL SCALE (estimated_evidence_level):
Rate how much prior evidence currently exists for this assumption being true. This is about existing knowledge, NOT what the research will reveal.
- 5 = Well-established — strong prior research, data, or industry consensus exists
- 4 = Reasonably evidenced — some data or research supports this
- 3 = Mixed — some evidence but also contradicting signals
- 2 = Thin — only anecdotal or weak evidence exists
- 1 = Pure assumption — no prior evidence, this is a genuine open question

RATIONALE GUIDANCE:
- importance_rationale: "Critical because [specific reason tied to this hypothesis]..."
- evidence_rationale: "Low evidence because [specific reason why this is unknown]..." or "Strong evidence from [specific source/fact]..."

Respond with a JSON object matching this schema:
{{
  "assumptions": [
    {{
      "statement": "string — one falsifiable belief",
      "estimated_importance": 1-5,
      "estimated_evidence_level": 1-5,
      "importance_rationale": "string — one sentence explaining the importance estimate",
      "evidence_rationale": "string — one sentence explaining the evidence estimate"
    }},
    ...
  ]
}}

Extract between 5 and 10 assumptions. If the hypothesis is narrow, surface the implicit beliefs it depends on."""
