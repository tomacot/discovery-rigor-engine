"""
Script assemble node.

Deterministic: builds the clean script text (using rewrites where available)
and computes the bias_score as the fraction of questions that passed clean.
Runs last in the script-review sub-flow.
"""

from __future__ import annotations

from dataclasses import replace

from src.state import Script, ScriptQuestion, StudyState


def _clean_text_for(question: ScriptQuestion) -> str:
    """Return rewrite if flagged and rewritten, otherwise the original text."""
    if question.verdict == "rewrite_needed" and question.rewrite:
        return question.rewrite
    return question.original_text


def assemble_clean_script(state: StudyState) -> dict:
    """Build clean_text numbered list and compute bias_score; return updated Script."""
    script: Script = state["scripts"][0]
    questions = script.questions

    numbered_lines = [
        f"{i + 1}. {_clean_text_for(q)}" for i, q in enumerate(questions)
    ]
    clean_text = "\n".join(numbered_lines)

    pass_count = sum(1 for q in questions if q.verdict == "pass")
    bias_score = pass_count / len(questions) if questions else 0.0

    updated_script = replace(script, clean_text=clean_text, bias_score=bias_score)
    return {"scripts": [updated_script]}
