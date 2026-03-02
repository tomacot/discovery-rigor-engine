"""
Prompt: Open Coding — Extract Discrete Observations from Session Notes

Used by: src/nodes/synthesis_open_coding.py

Open coding is the first stage of qualitative synthesis. The LLM reads raw
interview notes for one session and extracts discrete, atomic observations —
things the participant said, did, or the context they described. No
interpretation, no pattern-matching, no conclusions at this stage.

The strict separation of observation from interpretation is the core quality
guarantee of this tool. If interpretation slips in at this stage, it
contaminates every downstream node. The `is_interpretation` field is a
self-check: the LLM must flag any items that are interpretations. The node
filters these out before passing observations to axial coding.

Known failure modes:
- LLM conflates observation with interpretation (e.g. "participant seems
  frustrated" instead of "participant said 'I just give up and do it manually'").
  The prompt gives explicit before/after examples.
- LLM extracts too few observations from dense notes. Prompt instructs
  to err on the side of more extractions.
"""

from pydantic import BaseModel


OPEN_CODING_SYSTEM = (
    "You are a qualitative research analyst applying open coding to raw interview notes. "
    "You extract only what is observable — what was said, done, or present — never "
    "what it means. Your observations are the raw material for later synthesis."
)


class ObservationItem(BaseModel):
    """A single discrete observation extracted from session notes."""

    type: str  # behaviour | statement | context
    content: str  # Verbatim quote or close paraphrase — no interpretation
    is_interpretation: bool = False  # Must always be False at this stage


class OpenCodingResult(BaseModel):
    """LLM response: all observations extracted from one session."""

    observations: list[ObservationItem]


def get_open_coding_prompt(raw_notes: str, participant_id: str) -> str:
    """Return the user prompt asking the LLM to extract observations from raw session notes.

    Processes one session at a time. The participant_id is included so
    observations can be traced back to their source session.
    """
    return f"""You are performing open coding on raw interview notes from a user research session.

PARTICIPANT: {participant_id}

RAW NOTES:
{raw_notes}

TASK:
Extract every discrete observation from these notes. An observation is something that happened, was said, or was present — not what it means.

OBSERVATION TYPES — use exactly one per item:

- behaviour: What the participant actually does or did (observable actions, habits, workarounds)
  Example: "Participant uses a shared Google Sheet to track which assets go to which channels"
  Example: "Participant manually checks each ad platform separately rather than using a dashboard"

- statement: What the participant said, in their own words or a close paraphrase
  Example: "Participant said: 'I spend about two hours every Monday just pulling screenshots'"
  Example: "Participant described their approval process as 'a game of email tennis'"

- context: Details about their environment, role, tools, team size, or situation
  Example: "Participant manages campaigns across Facebook, Google, and two programmatic DSPs"
  Example: "Team has one dedicated designer shared across three campaign managers"

CRITICAL RULE — Observations vs Interpretations:
- OBSERVATION: "Participant said the approval process takes 3 days on average" ✓
- INTERPRETATION: "Participant finds the approval process frustrating" ✗ (you inferred this)
- OBSERVATION: "Participant said 'it's honestly pretty painful'" ✓ (their words, quoted)
- INTERPRETATION: "The team lacks proper tooling" ✗ (conclusion, not observation)

Set is_interpretation to False for every item. If you find yourself writing an interpretation,
rephrase it as the underlying observable behaviour or statement that led you to that interpretation.

GUIDANCE:
- Extract more rather than fewer — synthesis will filter, but cannot create data you missed
- Each observation should be one discrete data point, not a summary of multiple things
- Preserve participant language where possible — exact quotes are more valuable than paraphrases

Respond with a JSON object matching this schema:
{{
  "observations": [
    {{
      "type": "behaviour | statement | context",
      "content": "string — the observation, verbatim or close paraphrase",
      "is_interpretation": false
    }},
    ...
  ]
}}"""
