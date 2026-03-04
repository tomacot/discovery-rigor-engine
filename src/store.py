"""
Data store for studies — in-memory (default) or DynamoDB (when USE_DYNAMODB=true).

The StudyStore interface is shared between both backends:
  create_study, get_study, save_study, load_fixture, load_from_dict, list_studies

Toggle the backend via environment variable:
  USE_DYNAMODB=false  (default) → in-memory dict, zero infrastructure
  USE_DYNAMODB=true             → DynamoDB table (provisioned by CDK)

Use get_store() as the factory — callers should never instantiate StudyStore or
DynamoStudyStore directly. This keeps the backend swap transparent.

Why in-memory for local dev: zero setup friction. The DynamoDB backend requires
AWS credentials and a provisioned table. The in-memory backend requires neither.

How Streamlit interacts with this: the store is instantiated once in _init_session()
in ui/home.py and stored in st.session_state so it persists across Streamlit reruns
within a browser session.
"""

from __future__ import annotations

import json
import os
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
                importance_rationale=a.get("importance_rationale", ""),
                evidence_rationale=a.get("evidence_rationale", ""),
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
                summary=ses.get("summary", ""),
            )
            for ses in data.get("sessions", [])
        ]

        return state

    def load_from_dict(self, data: dict) -> StudyState:
        """
        Deserialise a raw dict (e.g. from an uploaded JSON file) into a StudyState.

        Uses the same deserialization logic as load_fixture() but accepts a pre-parsed
        dict instead of reading from disk. This lets the home page accept file uploads.
        """
        study_id = data.get("study_id", f"upload-{id(data)}")
        hypothesis = data.get("hypothesis", "")
        state = self.create_study(study_id, hypothesis)

        state["assumptions"] = [
            Assumption(
                id=a["id"],
                statement=a["statement"],
                risk_lens=a.get("risk_lens", ""),
                importance=a.get("importance", 0),
                evidence_level=a.get("evidence_level", 0),
                risk_score=a.get("risk_score", 0.0),
                status=a.get("status", "untested"),
                research_question=a.get("research_question", ""),
                importance_rationale=a.get("importance_rationale", ""),
                evidence_rationale=a.get("evidence_rationale", ""),
            )
            for a in data.get("assumptions", [])
        ]

        state["scripts"] = [
            Script(
                id=s["id"],
                study_id=s.get("study_id", study_id),
                raw_text=s["raw_text"],
                clean_text=s.get("clean_text", ""),
                bias_score=s.get("bias_score", 0.0),
                questions=[],
            )
            for s in data.get("scripts", [])
        ]

        state["sessions"] = [
            Session(
                id=ses["id"],
                study_id=ses.get("study_id", study_id),
                participant_id=ses["participant_id"],
                raw_notes=ses["raw_notes"],
                summary=ses.get("summary", ""),
            )
            for ses in data.get("sessions", [])
        ]

        return state

    def list_studies(self) -> list[str]:
        """Return all study IDs currently in the store."""
        return list(self._studies.keys())


def _serialise(obj: object) -> object:
    """JSON default serialiser for dataclasses and other non-JSON-native types."""
    import dataclasses

    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return dataclasses.asdict(obj)
    return str(obj)


class DynamoStudyStore:
    """
    DynamoDB-backed store. Activated when USE_DYNAMODB=true.

    Data model:
      Partition key: study_id (string)
      Attribute: state (string) — full StudyState serialised as JSON

    Why delegate construction to StudyStore: the deserialisation logic for
    Assumption, Script, and Session dataclasses lives in StudyStore.load_from_dict().
    Reusing it avoids duplicating that logic here.
    """

    def __init__(self, table_name: str) -> None:
        import boto3

        self._table = boto3.resource("dynamodb").Table(table_name)
        self._mem = StudyStore()  # delegate for construction and deserialisation

    def create_study(self, study_id: str, hypothesis: str) -> StudyState:
        """Create a new study in-memory, then persist it to DynamoDB."""
        state = self._mem.create_study(study_id, hypothesis)
        self.save_study(state)
        return state

    def get_study(self, study_id: str) -> Optional[StudyState]:
        """Retrieve a study from DynamoDB, or None if not found."""
        response = self._table.get_item(Key={"study_id": study_id})
        if "Item" not in response:
            return None
        raw = json.loads(response["Item"]["state"])
        return self._mem.load_from_dict(raw)

    def save_study(self, state: StudyState) -> None:
        """Persist the full StudyState to DynamoDB as a JSON blob."""
        self._table.put_item(
            Item={
                "study_id": state["study_id"],
                "state": json.dumps(state, default=_serialise),
            }
        )

    def load_fixture(self, fixture_name: str = "adtech_study") -> StudyState:
        """Load from local fixture file, then persist to DynamoDB."""
        state = self._mem.load_fixture(fixture_name)
        self.save_study(state)
        return state

    def load_from_dict(self, data: dict) -> StudyState:
        """Deserialise from a dict, then persist to DynamoDB."""
        state = self._mem.load_from_dict(data)
        self.save_study(state)
        return state

    def list_studies(self) -> list[str]:
        """Return all study IDs via a DynamoDB Scan (projection only)."""
        response = self._table.scan(ProjectionExpression="study_id")
        return [item["study_id"] for item in response.get("Items", [])]


def get_store() -> StudyStore | DynamoStudyStore:
    """
    Return the appropriate store backend based on the USE_DYNAMODB environment variable.

    USE_DYNAMODB=true  → DynamoStudyStore (requires AWS credentials + provisioned table)
    USE_DYNAMODB=false → StudyStore (in-memory, no infrastructure)

    The DYNAMODB_TABLE env var overrides the default table name. This is set
    automatically by CDK on the ECS task definition.
    """
    if os.getenv("USE_DYNAMODB", "false").lower() == "true":
        table_name = os.getenv("DYNAMODB_TABLE", "discovery-rigor-studies")
        return DynamoStudyStore(table_name)
    return StudyStore()
