"""
Prompt: Axial Coding — Cluster Observations into Cross-Session Themes

Used by: src/nodes/synthesis_axial_coding.py

Axial coding is the second stage of qualitative synthesis. The LLM receives
all observations from all sessions and identifies recurring patterns — themes
— that appear across multiple participants. Single-source patterns are not
themes; they are data points waiting to be corroborated or contradicted.

The ≥2-session minimum is both a methodological rule and a product guardrail.
It prevents PMs from building strategy on one loud voice. The prompt enforces
this hard rule; the synthesis_axial_coding node validates it deterministically
after the LLM responds.

The counterevidence field is mandatory. "None found" is a valid value but the
LLM must actively consider it — not skip it. Research that only notices
confirming evidence is the primary failure mode this tool prevents.

Known failure modes:
- LLM creates too many micro-themes (one per observation). Prompt caps at 7
  and instructs to favour broader, meaningful groupings.
- LLM invents observation_indices that don't exist in the input. The node
  validates all indices after receiving the response.
- counterevidence field is sometimes set to "none found" without genuine
  consideration. The prompt includes an instruction to actively search for it.
"""

from typing import Optional

from pydantic import BaseModel


AXIAL_CODING_SYSTEM = (
    "You are a qualitative research analyst applying axial coding to extract cross-session patterns. "
    "You identify themes that are grounded in evidence from multiple participants, actively seek "
    "counterevidence, and never mistake a single participant's strong view for a pattern."
)


class ThemeDraft(BaseModel):
    """A cross-session pattern identified from clustered observations."""

    label: str  # Short theme name (3-6 words)
    description: str  # What this theme represents (1-2 sentences)
    observation_indices: list[int]  # 0-indexed positions in the observations list
    session_ids: list[str]  # Which sessions support this theme (must be ≥2 unique sessions)
    counterevidence: str  # Observations that contradict or complicate this theme, or "none found"
    assumption_id: Optional[str] = None  # Which assumption this theme most directly addresses


class AxialCodingResult(BaseModel):
    """LLM response: all themes identified across sessions."""

    themes: list[ThemeDraft]


def get_axial_coding_prompt(
    observations: list[dict],
    assumptions: list[dict],
) -> str:
    """Return the user prompt asking the LLM to cluster observations into cross-session themes.

    observations: list of {"index": int, "session_id": str, "type": str, "content": str}
    assumptions: list of {"id": str, "statement": str} — provided as context for theme-assumption linking
    """
    observation_lines = "\n".join(
        f"[{o['index']}] ({o['session_id']}, {o['type']}) {o['content']}"
        for o in observations
    )

    assumption_lines = "\n".join(
        f"- {a['id']}: {a['statement']}" for a in assumptions
    )

    return f"""You are performing axial coding on observations collected across multiple user research sessions.

OBSERVATIONS (format: [index] (session_id, type) content):
{observation_lines}

RESEARCH ASSUMPTIONS BEING TESTED:
{assumption_lines}

TASK:
Identify 3-7 themes that represent meaningful patterns across multiple participants. A theme is a recurring pattern, tension, or behaviour observed in more than one session.

THEME REQUIREMENTS:

Multi-session support (hard rule):
- Every theme MUST be supported by observations from ≥2 DIFFERENT session IDs
- A single participant saying something strongly does not make it a theme
- If a pattern only appears in one session, do not create a theme — note it as potential counterevidence for a related theme instead

Theme quality:
- 3-6 word label that describes the pattern, not the topic area
  Good: "Manual workarounds replace platform integrations" (describes behaviour)
  Bad: "Integration issues" (topic label, not a pattern)
- Description: 1-2 sentences explaining what the theme means and why it matters

Observation indices:
- observation_indices must be 0-based integer indices from the list above
- Only include observations that genuinely support this theme
- An observation can appear in multiple themes if it supports both

Counterevidence (mandatory — do not skip):
- Actively look for observations that complicate, contradict, or limit this theme
- Describe specific observations that push back against the pattern
- "none found" is acceptable but must be a considered conclusion, not a default
- Include the index numbers of counterevidence observations in your description

Assumption linkage (optional but encouraged):
- If a theme directly tests one of the listed assumptions, set assumption_id to the assumption's ID
- Leave as null if the theme is emergent and doesn't map cleanly to an assumption

GUIDANCE:
- Prefer broader, meaningful themes over micro-themes (3-7 total, not 15)
- Look for tensions and contradictions — these are often the most valuable findings
- Consider workflow themes, pain severity themes, workaround themes, and adoption barrier themes

Respond with a JSON object matching this schema:
{{
  "themes": [
    {{
      "label": "string — 3-6 word theme name",
      "description": "string — 1-2 sentences describing the pattern",
      "observation_indices": [0, 3, 7, ...],
      "session_ids": ["P1", "P3", ...],
      "counterevidence": "string — specific contradicting observations, or 'none found'",
      "assumption_id": "string or null"
    }},
    ...
  ]
}}"""
