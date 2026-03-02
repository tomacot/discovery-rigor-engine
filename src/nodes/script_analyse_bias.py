"""
Script analyse bias node.

LLM node: analyses each parsed question for bias patterns (leading, hypothetical,
solution-selling, closed, double-barrelled). One LLM call per question.
Runs after parse_questions.
"""

from __future__ import annotations

from dataclasses import replace

from src.llm import call_llm_structured
from src.prompts.analyse_bias import (
    ANALYSE_BIAS_SYSTEM,
    BiasAnalysis,
    get_analyse_bias_prompt,
)
from src.state import Script, ScriptQuestion, StudyState


def _analyse_one(question: ScriptQuestion) -> ScriptQuestion:
    """Run bias analysis on a single question and return an updated copy."""
    prompt = get_analyse_bias_prompt(question.original_text)
    result: BiasAnalysis = call_llm_structured(
        prompt, BiasAnalysis, ANALYSE_BIAS_SYSTEM
    )
    return replace(
        question,
        verdict=result.verdict,
        issue_types=result.issue_types,
        explanation=result.explanation,
    )


def analyse_bias(state: StudyState) -> dict:
    """Analyse every script question for bias; return Script with verdicts populated."""
    script: Script = state["scripts"][0]
    analysed = [_analyse_one(q) for q in script.questions]
    updated_script = replace(script, questions=analysed)
    return {"scripts": [updated_script]}
