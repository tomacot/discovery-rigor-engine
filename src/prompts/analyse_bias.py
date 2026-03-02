"""
Prompt: Analyse an Interview Question for Bias Patterns

Used by: src/nodes/script_analyse_bias.py

For each question in a submitted interview script, the LLM checks for
five common bias patterns that corrupt qualitative research data. This is
the detection stage — rewrites are handled by a separate node/prompt.

The prompt deliberately provides precise definitions and examples because
"leading question" is used loosely in everyday speech. The LLM needs to
apply the research methodology definition, not the colloquial one.

Known failure modes:
- LLM occasionally marks neutral professional phrasing as "leading" when
  it isn't — the prompt includes a false-positive check instruction.
- "double_barrelled" is the most-missed pattern; the prompt gives two
  clear examples to anchor the LLM's recognition.
- Borderline cases are correctly handled with "warning" rather than forcing
  a binary pass/fail — this is intentional and preserves PM judgment.
"""

from pydantic import BaseModel


ANALYSE_BIAS_SYSTEM = (
    "You are an expert in interview research methodology who reviews discussion guides "
    "for PM-led user research. You apply precise definitions of bias patterns — not "
    "colloquial usage — and you only flag genuine problems, not stylistic preferences."
)


class BiasAnalysis(BaseModel):
    """Bias analysis result for a single interview question."""

    verdict: str  # pass | warning | rewrite_needed
    issue_types: list[str]  # subset of: leading, hypothetical, solution_selling, closed, double_barrelled
    explanation: str  # Plain-language explanation of the problem (or confirmation it's clean)


def get_analyse_bias_prompt(question: str) -> str:
    """Return the user prompt asking the LLM to analyse one interview question for bias.

    Analyses against five named bias patterns and returns a verdict with
    explanation — used by the script review flow to annotate each question.
    """
    return f"""You are reviewing an interview question from a PM-led user research script.

QUESTION TO ANALYSE:
"{question}"

BIAS TAXONOMY — check for these five patterns:

1. leading
   The question embeds an assumption, frames the topic emotionally, or nudges toward a particular answer.
   Examples: "Don't you find it frustrating when...", "How helpful would it be if...", "Wouldn't it be easier to..."
   Note: Professional, neutral phrasing is NOT leading. Only flag if the question steers the respondent.

2. hypothetical
   The question asks about imagined or future behaviour rather than actual past experience.
   Examples: "Would you use a tool that...", "If we built...", "Could you imagine...", "What would you do if..."
   Note: Questions about real past experience ("Have you ever had to...") are not hypothetical even if they use "if".

3. solution_selling
   The question introduces or implies a specific solution, product, or feature before understanding the problem.
   Examples: "What if there was an automated tool that...", "We're building X — how would that change your workflow?"

4. closed
   The question can be answered with yes/no or a single word when an open-ended answer would yield much richer data.
   Examples: "Is this a problem for you?", "Do you use spreadsheets?", "Are you satisfied with your current process?"
   Note: Demographic or screening questions that are intentionally closed are fine — only flag research questions.

5. double_barrelled
   The question asks about two distinct things at once, making it unclear which the respondent is answering.
   Examples: "How do you manage creative approvals and track performance across channels?",
             "Do you prefer automation or does your team handle it manually?"

VERDICT RULES:
- pass: No significant bias issues. The question is ready to use as-is.
- warning: Minor issue present — usable with care, but could be improved.
- rewrite_needed: One or more issues that would materially corrupt the data. Should be rewritten before use.

IMPORTANT: Do not over-flag. A question with neutral, professional phrasing that happens to be somewhat direct
is NOT biased. Only mark "warning" or "rewrite_needed" if the issue would genuinely affect participant responses.

Respond with a JSON object matching this schema:
{{
  "verdict": "pass | warning | rewrite_needed",
  "issue_types": ["list of issue types from the taxonomy above, empty list if verdict is pass"],
  "explanation": "string — plain-language explanation. If pass, briefly confirm why it's clean. If flagged, explain the specific problem and how it would affect participant responses."
}}"""
