"""
Core data models and LangGraph state definition.

All domain entities (Assumption, Observation, Theme, Insight, etc.) are defined here
as dataclasses. The StudyState TypedDict is the single state object that flows through
the LangGraph graph.

Why dataclasses (not Pydantic): These are domain objects for internal use. Pydantic is
reserved for LLM response validation in src/prompts/ where we need schema enforcement.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, TypedDict


# --- Domain entities ---


@dataclass
class Assumption:
    """A discrete, testable belief extracted from a hypothesis."""

    id: str
    statement: str
    risk_lens: str  # desirability | usability | feasibility | viability
    importance: int = 0  # 1-5, user-rated
    evidence_level: int = 0  # 1-5, user-rated
    risk_score: float = 0.0  # Computed: importance × (6 - evidence_level)
    status: str = "untested"  # untested | confirmed | challenged | uncertain
    research_question: str = ""


@dataclass
class ScriptQuestion:
    """A single question extracted from an interview script, with bias analysis."""

    id: str
    original_text: str
    verdict: str = ""  # pass | warning | rewrite_needed
    issue_types: list[str] = field(default_factory=list)  # leading, hypothetical, etc.
    explanation: str = ""
    rewrite: str = ""


@dataclass
class Script:
    """An interview discussion guide submitted for review."""

    id: str
    study_id: str
    raw_text: str
    clean_text: str = ""
    bias_score: float = 0.0  # % of questions that passed clean
    questions: list[ScriptQuestion] = field(default_factory=list)


@dataclass
class Session:
    """A single research session (interview, observation, etc.)."""

    id: str
    study_id: str
    participant_id: str  # Anonymised: P1, P2, etc.
    raw_notes: str


@dataclass
class Observation:
    """A discrete, coded data point extracted from session notes."""

    id: str
    session_id: str
    type: str  # behaviour | statement | context
    content: str
    is_interpretation: bool = False  # Enforced as False at open coding stage


@dataclass
class Theme:
    """A pattern identified across multiple observations."""

    id: str
    study_id: str
    label: str
    description: str
    observation_ids: list[str] = field(default_factory=list)
    session_count: int = 0
    counterevidence: str = "none found"
    assumption_id: Optional[str] = None
    confidence: str = "emerging"  # emerging | moderate | strong


@dataclass
class Insight:
    """A finding derived from one or more themes."""

    id: str
    study_id: str
    statement: str
    evidence_strength: str = "low"  # high | medium | low
    theme_ids: list[str] = field(default_factory=list)
    counterevidence: str = ""
    implication: str = ""
    assumption_id: Optional[str] = None
    assumption_status: str = "uncertain"  # confirmed | challenged | uncertain


@dataclass
class DecisionRecord:
    """The final output — a traceable decision with confidence score."""

    id: str
    study_id: str
    question: str
    recommendation: str  # pursue | pivot | park | need_more_evidence
    evidence_summary: str
    confidence_score: int = 0  # 0-100, deterministic
    confidence_breakdown: dict[str, float] = field(default_factory=dict)
    descoped_items: str = ""
    remaining_risks: str = ""
    next_steps: str = ""


# --- LangGraph state ---


class StudyState(TypedDict):
    """
    The single state object for the LangGraph graph.

    Accumulates data as the user moves through workflows.
    Each node reads from and writes to this state.
    """

    # Study metadata
    study_id: str
    hypothesis: str
    status: str  # active | synthesised | decided

    # Assumption mapping
    assumptions: list[Assumption]
    assumption_map_complete: bool

    # Script review
    scripts: list[Script]

    # Synthesis
    sessions: list[Session]
    observations: list[Observation]
    themes: list[Theme]
    insights: list[Insight]
    decision_record: Optional[DecisionRecord]

    # Flow control
    current_flow: str  # assumption_mapping | script_review | synthesis
    messages: list[str]
