"""
Prompt: Categorise Each Assumption by Risk Lens

Used by: src/nodes/assumption_categorise.py

Asks the LLM to assign exactly one risk lens to each assumption from the
previous decomposition step. The four lenses come from the assumption
mapping framework used in product discovery (derived from the Lean Startup /
Four Fits model): desirability, usability, feasibility, viability.

Each tagging includes a one-sentence rationale so the PM understands why
the lens was chosen — critical for learning and for reviewing the output.

Known failure modes:
- LLM sometimes assigns "desirability" as a catch-all when "viability" or
  "usability" is more precise. The rationale field exposes this so the PM
  can override it in the Streamlit UI.
- LLM may return taggings in a different order than the input list. The
  assumption_id field is the join key — do not rely on list position.
"""

from pydantic import BaseModel


CATEGORISE_SYSTEM = (
    "You are an expert in the assumption mapping framework used in product discovery. "
    "You precisely classify assumptions by risk lens — desirability, usability, "
    "feasibility, or viability — and explain your reasoning clearly so PMs can "
    "review and override your classifications."
)


class LensTagging(BaseModel):
    """Risk lens classification for a single assumption."""

    assumption_id: str
    risk_lens: str  # desirability | usability | feasibility | viability
    rationale: str  # One sentence explaining why this lens was chosen


class CategorisedAssumptions(BaseModel):
    """LLM response: risk lens tags for all assumptions."""

    taggings: list[LensTagging]


def get_categorise_prompt(assumptions: list[dict]) -> str:
    """Return the user prompt asking the LLM to assign a risk lens to each assumption.

    Takes a list of {"id": str, "statement": str} dicts and returns taggings
    with rationale for PM review and potential override.
    """
    assumption_lines = "\n".join(
        f"- ID: {a['id']} | Statement: {a['statement']}" for a in assumptions
    )

    return f"""You are helping a PM classify research assumptions by risk lens before prioritising which to test.

ASSUMPTIONS TO CLASSIFY:
{assumption_lines}

RISK LENS DEFINITIONS:
Use exactly one of these four lenses per assumption:

- desirability: Does anyone want this? Is this the right problem to solve?
  Use this when the assumption is about whether users have the pain, need, or motivation.
  Example: "Mid-market advertisers find manual creative review a significant pain point"

- usability: Can users use it? Will they understand, adopt, and integrate it into their workflow?
  Use this when the assumption is about comprehension, adoption behaviour, or workflow fit.
  Example: "Advertisers can interpret cross-channel performance data without specialist training"

- feasibility: Can we build it? Does the technical or operational path exist?
  Use this when the assumption is about technical constraints, data availability, or build complexity.
  Example: "Creative asset metadata can be reliably extracted across major ad platforms via API"

- viability: Should we build it? Does it make business sense — pricing, competition, unit economics?
  Use this when the assumption is about willingness to pay, competitive positioning, or business model.
  Example: "Mid-market advertisers will pay a SaaS fee for automated creative optimisation"

RULES:
- Assign EXACTLY ONE lens per assumption — choose the most dominant risk type
- Write the rationale in one sentence explaining the assignment
- Return a tagging for every assumption ID provided — do not skip any

Respond with a JSON object matching this schema:
{{
  "taggings": [
    {{
      "assumption_id": "string — the ID from the input list",
      "risk_lens": "desirability | usability | feasibility | viability",
      "rationale": "string — one sentence explaining why this lens"
    }},
    ...
  ]
}}"""
