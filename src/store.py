"""
In-memory data store for studies.

All state lives in a dict keyed by study_id. Sample data is loaded from JSON
fixture files in data/. Nothing is persisted between Python process restarts.

Why in-memory for now: The AWS migration will replace this with DynamoDB, but
building against a simple dict first lets us develop and test all application
logic before introducing infrastructure dependencies. The store interface
(create_study, get_study, load_fixture) stays the same when we swap backends.

How Streamlit interacts with this: The store is instantiated once and stored
in st.session_state so it persists across Streamlit reruns within a session.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from src.state import (
    Assumption,
    Script,
    Session,
    StudyState,
)

# Fixture files live in data/ at the project root
FIXTURE_DIR = Path(__file__).parent.parent / "data"


class StudyStore:
    """In-memory store managing all study state."""

    def __init__(self) -> None:
        self._studies: dict[str, StudyState] = {}

    def create_study(self, study_id: str, hypothesis: str) -> StudyState:
        """Create a new empty study and return its initial state."""
        state: StudyState = {
            "study_id": study_id,
            "hypothesis": hypothesis,
            "status": "active",
            "assumptions": [],
            "assumption_map_complete": False,
            "scripts": [],
            "sessions": [],
            "observations": [],
            "themes": [],
            "insights": [],
            "decision_record": None,
            "current_flow": "",
            "messages": [],
        }
        self._studies[study_id] = state
        return state

    def get_study(self, study_id: str) -> Optional[StudyState]:
        """Retrieve a study by ID, or None if not found."""
        return self._studies.get(study_id)

    def save_study(self, state: StudyState) -> None:
        """Write an updated state back to the store after a graph run."""
        self._studies[state["study_id"]] = state

    def load_fixture(self, fixture_name: str = "adtech_study") -> StudyState:
        """
        Load a study from a JSON fixture file and deserialise into domain objects.

        fixture_name is the stem of the JSON file in data/ (e.g., "adtech_study").

        Why explicit deserialisation rather than dict unpacking: the domain
        dataclasses validate field types at construction time and give proper
        IDE autocompletion. A raw dict would silently accept the wrong shape.
        """
        path = FIXTURE_DIR / f"{fixture_name}.json"
        with open(path) as f:
            data = json.load(f)

        study_id = data.get("study_id", fixture_name)
        hypothesis = data.get("hypothesis", "")
        state = self.create_study(study_id, hypothesis)

        state["assumptions"] = [
            Assumption(
                id=a["id"],
                statement=a["statement"],
                risk_lens=a["risk_lens"],
                importance=a.get("importance", 0),
                evidence_level=a.get("evidence_level", 0),
                risk_score=a.get("risk_score", 0.0),
                status=a.get("status", "untested"),
                research_question=a.get("research_question", ""),
            )
            for a in data.get("assumptions", [])
        ]

        state["scripts"] = [
            Script(
                id=s["id"],
                study_id=s["study_id"],
                raw_text=s["raw_text"],
                clean_text=s.get("clean_text", ""),
                bias_score=s.get("bias_score", 0.0),
                questions=[],  # Populated later by the script_parse node
            )
            for s in data.get("scripts", [])
        ]

        state["sessions"] = [
            Session(
                id=ses["id"],
                study_id=ses["study_id"],
                participant_id=ses["participant_id"],
                raw_notes=ses["raw_notes"],
            )
            for ses in data.get("sessions", [])
        ]

        return state

    def list_studies(self) -> list[str]:
        """Return all study IDs currently in the store."""
        return list(self._studies.keys())
