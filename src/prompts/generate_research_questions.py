"""
Prompt: Generate Research Questions for Top-Risk Assumptions

Used by: src/nodes/assumption_research_qs.py

For the top 3 riskiest assumptions (ranked by risk score from scoring.py),
the LLM generates one past-behaviour-framed research question per assumption.
These are ready-to-use interview questions, not topic areas.

The focus on past behaviour is deliberate: "Tell me about the last time you..."
yields concrete, specific answers. "Would you..." yields speculation.

Known failure modes:
- LLM sometimes generates questions that ask about opinions rather than
  past behaviour. The prompt explicitly contrasts good vs bad examples.
- Questions occasionally include solution references — the prompt forbids this.
"""

from pydantic import BaseModel


RESEARCH_QS_SYSTEM = (
    "You are a user research expert who writes past-behaviour-focused interview questions. "
    "You understand that the best research questions reveal what people actually do, "
    "not what they think they would do. You never ask hypothetical or leading questions."
)


class ResearchQuestion(BaseModel):
    """A single research question tied to one assumption."""

    assumption_id: str
    question: str  # Past-behaviour-framed, open-ended, solution-agnostic
    evidence_type: str  # e.g. "behavioural observation", "past-behaviour interview"


class ResearchQuestions(BaseModel):
    """LLM response: one research question per top-risk assumption."""

    questions: list[ResearchQuestion]


def get_research_questions_prompt(
    top_assumptions: list[dict],
    hypothesis: str,
) -> str:
    """Return the user prompt asking the LLM to write one research question per assumption.

    Takes the top 3 riskiest assumptions and the original hypothesis as context.
    Returns questions ready to include in an interview script.
    """
    assumption_lines = "\n".join(
        f"- ID: {a['id']} | Risk lens: {a['risk_lens']} | Statement: {a['statement']}"
        for a in top_assumptions
    )

    return f"""You are helping a PM write interview questions to test their riskiest research assumptions.

RESEARCH HYPOTHESIS:
{hypothesis}

TOP ASSUMPTIONS TO TEST (ranked by risk — address these in priority order):
{assumption_lines}

TASK:
Write one past-behaviour-framed research question for each assumption listed above. Each question should generate concrete evidence that either supports or challenges the assumption.

GOOD QUESTION PATTERNS (use these):
- "Tell me about the last time you [relevant action]..."
- "Walk me through how you [relevant process] in a recent campaign..."
- "Describe a specific instance where [relevant situation]..."
- "What happened the last time [relevant scenario]?"

BAD QUESTION PATTERNS (avoid these):
- "Would you use a tool that..." (hypothetical future behaviour)
- "Do you think it would be helpful if..." (opinion/speculation)
- "How helpful would it be to have..." (leading + hypothetical)
- "Is [problem] a pain point for you?" (closed, yes/no)
- Any question that mentions a solution, product, or feature

EVIDENCE TYPE GUIDANCE:
For each question, specify what kind of evidence it is designed to surface:
- "past-behaviour interview" — the participant recounts a real experience
- "behavioural observation" — the question surfaces what they actually do vs. say
- "workflow reconstruction" — the participant walks through a process step-by-step

RULES:
- One question per assumption — write the single best question, not multiple options
- The question must be answerable without knowing your product exists
- Open-ended — cannot be answered with yes/no
- Return a question for every assumption ID provided

Respond with a JSON object matching this schema:
{{
  "questions": [
    {{
      "assumption_id": "string — matches an assumption ID from the input",
      "question": "string — the full interview question, ready to use",
      "evidence_type": "string — what type of evidence this surfaces"
    }},
    ...
  ]
}}"""
