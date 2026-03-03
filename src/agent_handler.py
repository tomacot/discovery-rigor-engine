"""
Bedrock AgentCore Runtime entry point.

AgentCore Runtime requires a single handler function it calls to invoke the agent.
This file is the glue between AgentCore and LangGraph — no business logic lives here.

Invocation contract:
  Input:  {"flow": str, "study_state": dict}
  Output: dict (updated StudyState)

The "flow" field maps to current_flow in StudyState:
  - "assumption_mapping_phase1"
  - "assumption_mapping_phase2"
  - "script_review"
  - "synthesis"

Why a separate entry point:
  AgentCore Runtime needs a well-defined handler signature to manage the agent
  lifecycle. Keeping this in its own file means the handler is testable in
  isolation and the LangGraph graph (src/graph.py) is unchanged.

Why the graph is rebuilt per invocation:
  AgentCore Runtime manages session state externally (via the DynamoDB store).
  The graph itself is stateless — it's a routing + execution definition. Rebuilding
  it per invocation is cheap (no network calls) and avoids shared mutable state
  between concurrent invocations.
"""

from __future__ import annotations

import logging

from src.graph import build_graph
from src.state import StudyState

logger = logging.getLogger(__name__)


def handler(input: dict, context: dict) -> dict:
    """
    AgentCore Runtime handler — invoke the LangGraph graph for a given flow.

    Args:
        input: Dict containing:
            - flow (str): Which sub-flow to run (e.g., "script_review")
            - study_state (dict): Current StudyState as a plain dict
        context: AgentCore Runtime context (session ID, invocation metadata, etc.)

    Returns:
        Updated StudyState as a plain dict.
    """
    flow = input.get("flow")
    raw_state = input.get("study_state", {})

    if not flow:
        raise ValueError("'flow' is required in handler input")
    if not raw_state:
        raise ValueError("'study_state' is required in handler input")

    logger.info(
        "AgentCore handler invoked: flow=%s study_id=%s",
        flow,
        raw_state.get("study_id"),
    )

    # Inject the flow into state so the router can branch correctly
    state: StudyState = {**raw_state, "current_flow": flow}  # type: ignore[assignment, typeddict-item]

    graph = build_graph()
    result: StudyState = graph.invoke(state)

    logger.info(
        "AgentCore handler complete: flow=%s study_id=%s",
        flow,
        result.get("study_id"),
    )

    # Return as plain dict — AgentCore serialises to DynamoDB
    return dict(result)
