"""
Script rewrite node.

LLM node: generates de-biased rewrites for questions flagged as 'rewrite_needed'.
Only calls the LLM for flagged questions — clean questions are passed through unchanged.
Runs after analyse_bias.
"""

from __future__ import annotations

from dataclasses import replace

from src.llm import call_llm_structured
from src.prompts.rewrite_question import (
    REWRITE_SYSTEM,
    QuestionRewrite,
    get_rewrite_prompt,
)
from src.state import Script, ScriptQuestion, StudyState


def _rewrite_one(question: ScriptQuestion) -> ScriptQuestion:
    """Generate a de-biased rewrite for a single flagged question."""
    prompt = get_rewrite_prompt(question.original_text, question.issue_types)
    result: QuestionRewrite = call_llm_structured(
        prompt, QuestionRewrite, REWRITE_SYSTEM
    )
    return replace(question, rewrite=result.rewrite)


def rewrite_questions(state: StudyState) -> dict:
    """Rewrite only flagged questions; merge back with unchanged questions."""
    script: Script = state["scripts"][0]

    updated_questions = [
        _rewrite_one(q) if q.verdict == "rewrite_needed" else q
        for q in script.questions
    ]

    updated_script = replace(script, questions=updated_questions)
    return {"scripts": [updated_script]}
