"""
Script parse node.

Deterministic: splits raw interview script text into individual ScriptQuestion
dataclasses. No LLM needed — this is pure text parsing. Runs first in the
script-review sub-flow.
"""

from __future__ import annotations

import re
from dataclasses import replace

from src.state import Script, ScriptQuestion, StudyState

_NUMBERING_PATTERN = re.compile(r"^\d+[\.\)]\s*")


def _strip_numbering(line: str) -> str:
    """Remove leading question numbers like '1. ' or '2) ' from a line."""
    return _NUMBERING_PATTERN.sub("", line).strip()


def parse_questions(state: StudyState) -> dict:
    """Split script raw_text into ScriptQuestion list; return updated Script."""
    script: Script = state["scripts"][0]

    lines = [line for line in script.raw_text.splitlines() if line.strip()]

    questions = [
        ScriptQuestion(
            id=f"Q{i + 1}",
            original_text=_strip_numbering(line),
        )
        for i, line in enumerate(lines)
    ]

    updated_script = replace(script, questions=questions)
    return {"scripts": [updated_script]}
