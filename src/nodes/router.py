"""
Entry router node.

This is a conditional-edge function, not a state-modifying node.
LangGraph calls it to decide which node to execute next based on current_flow.
"""

from __future__ import annotations

from src.state import StudyState

# Maps the user-selected flow to the first node in that sub-flow.
_FLOW_TO_FIRST_NODE: dict[str, str] = {
    "assumption_mapping_phase1": "decompose_hypothesis",
    "assumption_mapping_phase2": "compute_risk_scores",
    "script_review": "parse_questions",
    "synthesis": "ingest_notes",
}


def route_to_flow(state: StudyState) -> str:
    """Return the name of the first node for the current_flow value."""
    flow = state["current_flow"]
    if flow not in _FLOW_TO_FIRST_NODE:
        raise ValueError(
            f"Unknown current_flow: '{flow}'. "
            f"Expected one of: {list(_FLOW_TO_FIRST_NODE)}"
        )
    return _FLOW_TO_FIRST_NODE[flow]
