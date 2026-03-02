"""
Synthesis open coding node.

LLM node: extracts discrete, tagged observations from each session's raw notes.
One LLM call per session. Produces the Observation list that feeds axial coding.
is_interpretation is enforced as False — interpretive leaps are blocked at this stage.
"""

from __future__ import annotations

from src.llm import call_llm_structured
from src.prompts.open_coding import (
    OPEN_CODING_SYSTEM,
    OpenCodingResult,
    get_open_coding_prompt,
)
from src.state import Observation, Session, StudyState


def _code_session(session: Session, start_index: int) -> list[Observation]:
    """Extract observations from one session; IDs start at start_index."""
    prompt = get_open_coding_prompt(session.raw_notes, session.participant_id)
    result: OpenCodingResult = call_llm_structured(
        prompt, OpenCodingResult, OPEN_CODING_SYSTEM
    )
    return [
        Observation(
            id=f"OBS{start_index + i}",
            session_id=session.id,
            type=item.type,
            content=item.content,
            is_interpretation=False,  # Enforced: no interpretations at open coding
        )
        for i, item in enumerate(result.observations)
    ]


def open_coding(state: StudyState) -> dict:
    """Run open coding on every session; return flat list of Observations."""
    observations: list[Observation] = []
    counter = 1

    for session in state["sessions"]:
        new_obs = _code_session(session, counter)
        observations.extend(new_obs)
        counter += len(new_obs)

    return {"observations": observations}
