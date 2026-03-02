"""
Prompt: Rewrite a Biased Interview Question

Used by: src/nodes/script_rewrite.py

Given a biased question and the specific issue types identified by the
analyse_bias node, the LLM produces a single de-biased rewrite. The rewrite
uses past-behaviour framing wherever possible because this is the most
reliable technique for reducing both hypothetical and leading bias.

The node only calls this prompt for questions with verdict "rewrite_needed".
Questions with verdict "warning" are flagged but not auto-rewritten, since
the PM may prefer to keep the original with awareness of the limitation.

Known failure modes:
- LLM occasionally produces a rewrite that is technically correct but loses
  the underlying research intent (asks about something different). The prompt
  explicitly requires preserving intent.
- For "solution_selling" questions, the LLM sometimes preserves an implicit
  solution reference. The prompt specifically calls this out.
"""

from pydantic import BaseModel


REWRITE_SYSTEM = (
    "You are an expert interview facilitator who rewrites biased research questions. "
    "You preserve the underlying research intent while eliminating bias patterns. "
    "Your rewrites always use past-behaviour framing and are open-ended."
)


class QuestionRewrite(BaseModel):
    """A de-biased rewrite of a single interview question."""

    rewrite: str  # De-biased, past-behaviour-framed alternative, ready to use


def get_rewrite_prompt(question: str, issue_types: list[str]) -> str:
    """Return the user prompt asking the LLM to rewrite a biased interview question.

    Takes the original question and the list of detected issue types so the
    LLM knows exactly which problems to correct in the rewrite.
    """
    issues_formatted = ", ".join(issue_types) if issue_types else "general bias"

    return f"""You are rewriting a biased interview question for a PM-led user research session.

ORIGINAL QUESTION (has issues):
"{question}"

DETECTED ISSUES:
{issues_formatted}

TASK:
Write ONE de-biased alternative that a researcher could use instead. The rewrite must fix all the issues listed above.

REWRITING PRINCIPLES:

Past-behaviour framing (use this technique):
- "Tell me about the last time you [action]..."
- "Walk me through the most recent time you [situation]..."
- "Describe a specific example of when [scenario]..."
- "What happened the last time [event]?"

Open-ended (the answer cannot be yes or no):
- Wrong: "Is this a problem for you?" → Right: "Tell me about a time when this caused a problem..."
- Wrong: "Do you use spreadsheets?" → Right: "Walk me through how you currently handle..."

No solution references:
- Remove ALL mentions of specific tools, features, or products you might build
- The question should be answerable by someone who has never heard of your company

No leading language:
- Remove emotional framing ("frustrating", "difficult", "easier")
- Remove embedded assumptions ("when you struggle with X" assumes they do struggle)
- Use neutral language that doesn't suggest what the correct answer is

Preserve the research intent:
- The rewrite must still probe the same underlying topic or behaviour
- Do not change what you are trying to learn — only change how you ask

Respond with a JSON object matching this schema:
{{
  "rewrite": "string — the complete rewritten question, ready to use in an interview"
}}"""
