"""
Synthesis ingest node.

Deterministic: normalises raw session notes (trims whitespace, validates non-empty).
Acts as a gatekeeper before the LLM-heavy coding pipeline begins.
Logs a warning message for any session with empty notes instead of failing hard.
"""

from __future__ import annotations

from src.state import Session, StudyState


def ingest_notes(state: StudyState) -> dict:
    """Trim and validate raw_notes on each session; log warnings for empty sessions."""
    sessions: list[Session] = state["sessions"]
    existing_messages: list[str] = list(state.get("messages", []))
    warnings: list[str] = []

    normalised: list[Session] = []
    for session in sessions:
        stripped = session.raw_notes.strip()
        if not stripped:
            warnings.append(
                f"Session {session.id} (participant {session.participant_id}) "
                "has empty raw_notes and will be skipped in coding."
            )
        else:
            # Dataclass is already correct type; re-assign stripped notes
            normalised.append(
                Session(
                    id=session.id,
                    study_id=session.study_id,
                    participant_id=session.participant_id,
                    raw_notes=stripped,
                )
            )

    return {
        "sessions": normalised,
        "messages": existing_messages + warnings,
    }
