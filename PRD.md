# Product Requirements Document: Discovery Rigor Engine

**Author:** https://github.com/tomacot 
**Version:** 1.1 — Shipped
**Status:** Live at AWS ECS Fargate + ALB

---

## 1. Problem Statement

Product management teams routinely conduct user research that fails to produce decision-grade insights — not because they lack effort, but because they lack embedded process discipline. The failure pattern is consistent and well-documented:

- **Assumptions go untested.** Teams jump from a vague problem space directly into interviews without identifying which specific beliefs are riskiest and most in need of evidence.
- **Bias contaminates execution.** PMs write interview scripts containing leading questions ("How helpful would it be if…"), hypotheticals ("Would you use…"), and solution-selling language — then treat the resulting positive responses as validation.
- **Synthesis is where rigour collapses.** The step between "we did 10 interviews" and "here's what we learned" is typically a black box. Observations get mixed with interpretations, recency bias means the last two conversations dominate, and there is no traceable chain from raw evidence to coded themes to insights to decisions.

Existing AI-assisted PM tools and LLM prompts/skills handle the *planning and framing* layer well — problem framing, interview planning, opportunity-solution trees. But they effectively stop where the hardest parts begin. There is no tool that carries a PM through execution, synthesis, and decision-traceability with active guardrails at each stage.

### Who this is for

Product managers and product teams who conduct their own user research (without a dedicated UX researcher) and want to produce research that actually changes what they build.

### What success looks like

A PM can go from "here are my assumptions about this problem" to "here is a decision backed by traceable evidence, with a confidence score and explicit counterevidence" — and a stakeholder can follow the chain backwards from decision to raw data at any point.

---

## 2. Positioning

This tool occupies the **execution-to-decision layer** of the user research workflow:

```
[Problem Framing] → [Research Planning] → [ THIS TOOL ] → [Roadmap/Backlog]
   (Existing tools       (Existing tools     Assumption mapping
    handle this well)     handle this well)   Execution guardrails
                                              Structured synthesis
                                              Quality scoring
                                              Decision traceability
```

It is complementary to, not competitive with, existing framing and planning tools. A PM might use a problem-framing canvas to define *what* to research, then enter this tool to ensure the research itself is rigorous enough to trust.

---

## 3. MVP Scope — Prioritised Capability Areas

Of the seven capability areas identified in the research playbook, the MVP will build **three** that create the most compelling and demonstrable end-to-end flow:

### MVP capabilities (build for demo)

| # | Capability | Why it's in the MVP |
|---|-----------|-------------------|
| 1 | **Assumption Mapping & Prioritisation** | This is the entry point to everything. Without it, teams research the wrong things. It's visually demonstrable (2×2 matrix output), immediately useful, and showcases AI's ability to decompose vague hypotheses into testable beliefs. |
| 2 | **Interview Script Guardrails** | The clearest demonstration of the problem — paste in a real interview script and watch the agent flag leading questions, hypotheticals, and confirmation bias patterns in real time. The "before and after" makes the failure mode immediately tangible. |
| 3 | **Structured Synthesis with Decision Traceability** | This closes the loop. Taking raw interview notes through open coding → themes → insights → a decision record with a confidence score demonstrates the full chain that's missing in PM practice today. It also produces the most impressive artefact — a traceable decision document. |

### Deferred to roadmap (not in MVP)

| Capability | Why it's deferred |
|-----------|-----------------|
| Quality & Rigour Scoring | Partially included — the synthesis step produces a confidence score. A full standalone rubric across six dimensions is a v2 feature. |
| Research Repository / Knowledge Management | Requires persistent storage, search indexing, and tagging taxonomy. Important for teams but adds no demo value for a single-session walkthrough. |
| Ethics, Privacy & Consent Workflows | Critical for production but adds complexity without demo impact. Better as a "responsible AI" section in the README. |
| Full Method Recommender | The playbook describes matching decision types to research methods across a full taxonomy. Valuable but the MVP focuses on interview-based research, which is the most common PM scenario. |

---

## 4. Functional Requirements

### 4.1 Assumption Mapping & Prioritisation

**User story:** As a PM beginning a discovery cycle, I want to surface and rank my assumptions about a problem space so that I research the riskiest beliefs first rather than defaulting to whatever is easiest to test.

#### Flow

1. **Input:** The user provides a problem statement or hypothesis in natural language (e.g., "We believe that mid-market advertisers struggle to optimise creative assets across channels because they lack real-time performance feedback").
2. **Decomposition (LLM):** The agent decomposes the hypothesis into 5–10 discrete assumptions, categorised by risk lens:
   - Desirability/Value — "Advertisers consider this a top-3 pain point"
   - Usability — "They can interpret the feedback within their existing workflow"
   - Feasibility — "Real-time cross-channel data is accessible via existing APIs"
   - Viability — "They would pay for this vs. using free alternatives"
3. **Prioritisation (interactive):** For each assumption, the user rates two dimensions on a 1–5 scale:
   - **Importance:** If this assumption is wrong, does the whole idea collapse?
   - **Evidence level:** How much evidence do we currently have?
   - Sliders default to **LLM-estimated scores** (not zero) — the agent estimates both values during decomposition and provides a one-sentence rationale caption beneath each slider explaining the estimate. The user adjusts from an intelligent starting point rather than from scratch.
4. **Output:** A prioritised assumption map:
   - A ranked list with the "riskiest assumptions" (high importance + low evidence) at the top.
   - For **every** assumption (not just top 3): a specific research question grounded in the assumption's risk lens.
   - A text-based 2×2 matrix visualisation (Importance vs. Evidence).
   - A downloadable Markdown research script: all assumptions grouped by risk lens with their research questions, plus 5 general interview questions as a discussion guide.

#### Acceptance criteria

- [x] Given a free-text hypothesis, the agent produces at least 5 categorised assumptions without the user having to structure anything.
- [x] Each assumption is tagged with exactly one risk lens (desirability, usability, feasibility, viability).
- [x] The agent estimates importance and evidence_level scores during decomposition; sliders start at those estimates, not at zero.
- [x] A one-sentence rationale caption is shown beneath each slider explaining the LLM's estimate.
- [x] The user can adjust each assumption interactively (importance and evidence level).
- [x] The output ranks assumptions by risk (importance × inverse of evidence) and highlights the top 3.
- [x] A specific research question is generated for **every** assumption (not just top 3).
- [x] The full assumption map is downloadable as a Markdown research script with assumptions grouped by risk lens.
- [x] The full assumption map is stored in session state and passed downstream to the synthesis step.

---

### 4.2 Interview Script Guardrails

**User story:** As a PM preparing a discussion guide, I want the tool to review my interview questions and flag bias patterns so that I don't contaminate my research with leading, hypothetical, or solution-selling language.

#### Flow

1. **Input:** The user pastes or types a set of interview questions (plain text, one question per line or in a numbered list).
2. **Analysis (LLM):** The agent analyses each question against a bias taxonomy:
   - **Leading questions:** Contain embedded assumptions or emotionally loaded framing ("Don't you think…", "How frustrating is…", "How helpful would it be if…")
   - **Hypothetical questions:** Ask about imagined future behaviour rather than past behaviour ("Would you use…", "If we built…", "Could you imagine…")
   - **Solution-selling:** Introduce or describe a specific solution before understanding the problem ("What if there was a tool that…", "We're building X, would you…")
   - **Closed/binary questions:** Answerable with yes/no when an open question would yield richer data ("Is this a problem?", "Do you like…")
   - **Double-barrelled questions:** Ask about two things at once ("How do you handle X and Y?")
3. **Output per question:**
   - **Verdict:** Pass / Warning / Rewrite needed
   - **Issue type(s):** Which bias pattern(s) detected
   - **Explanation:** Plain-language explanation of why this is problematic
   - **Suggested rewrite:** A de-biased alternative question grounded in past behaviour
4. **Summary output:**
   - Script-level bias score (% of questions that passed clean)
   - Most common bias pattern in this script
   - The full rewritten script as a copyable block

#### Acceptance criteria

- [x] The agent correctly flags at least 80% of leading, hypothetical, and solution-selling patterns in a test set of 20 known-bad questions (provided as sample data).
- [x] Each flagged question includes a specific rewrite, not just a warning.
- [x] Rewrites consistently use past-behaviour framing ("Tell me about the last time…", "Walk me through…", "What did you try…").
- [x] Clean questions (genuinely open, past-behaviour-based) are not false-flagged at a rate above 15%.
- [x] The output includes a copyable "clean script" block with all rewrites applied.
- [x] The bias taxonomy is deterministic (rule-based pattern matching where possible, LLM for nuance) — not purely LLM-generated, to ensure consistency.
- [x] 5 example scripts are selectable from a dropdown to pre-fill the input without pasting.

---

### 4.3 Structured Synthesis with Decision Traceability

**User story:** As a PM who has completed several research sessions, I want the tool to guide me through a structured synthesis process so that I produce traceable insights grounded in evidence rather than jumping from raw notes to conclusions.

#### Flow

**Step 1 — Ingest raw data:**
The user provides raw interview notes by: (a) pasting text into the session form, (b) uploading `.txt` transcript files (participant ID auto-detected from filename — `P1.txt`, `p2_interview.txt`, `participant3.txt` are all handled), or (c) using a pre-loaded fixture study. The tool also receives the assumption map from capability 4.1 to anchor synthesis to the original research questions.

**Step 2 — Open coding (LLM-assisted):**
The agent reads each note block and extracts discrete observations, tagging each as:
- **Observation type:** Behaviour (what they did), Statement (what they said), Context (environmental/workflow detail)
- **Verbatim quote or paraphrase:** The specific data point
- **Session source:** Which interview it came from

The agent explicitly separates observation from interpretation — no conclusions at this stage.

**Step 3 — Theme generation (axial coding):**
The agent clusters observations into candidate themes, requiring:
- Each theme is supported by observations from **at least 2 different sessions** (prevents single-source themes)
- Each theme includes a **counterevidence field** (observations that contradict or nuance the theme — or "none found" if genuinely absent)
- Each theme is linked back to a specific assumption from the assumption map where relevant

**Step 4 — Insight synthesis (selective coding):**
The agent generates insight statements from themes, each following the structure:
- **Insight:** [What we learned] — framed as a finding, not a recommendation
- **Evidence strength:** High / Medium / Low — based on: number of supporting sessions, consistency of pattern, presence/absence of counterevidence, observation type (behavioural > stated > hypothetical)
- **Supporting evidence:** Links to specific observations and themes
- **Counterevidence:** What complicates or limits this insight
- **Implication:** What this means for the product decision
- **Assumption addressed:** Which assumption from the map this informs, and whether it was confirmed, challenged, or remains uncertain
- **Supporting quotes:** Direct participant quotes extracted verbatim from session notes
- **Frequency:** How many of the N sessions mentioned this (e.g., "4 out of 5 participants")
- **Why it matters:** One sentence on business/UX/product impact
- **User segments affected:** Which participant types care most about this finding
- **Current workarounds:** How users are solving this today without a purpose-built tool
- **Potential solutions:** 2–3 solution directions to explore (not prescriptive features)
- **Priority:** Critical / High / Medium / Low
- **Actionability:** Clear / Fuzzy / Needs more research

**Step 5 — Decision record:**
The agent generates a structured decision record:
- **Decision question:** (from the original assumption map)
- **Recommendation:** Pursue / Pivot / Park / Need more evidence
- **Evidence summary:** Key insights with strength ratings
- **Confidence score:** Aggregate based on evidence strength, theme saturation, counterevidence coverage, and sample diversity
- **What we de-scoped:** Assumptions not addressed and why
- **Remaining risks:** What could still be wrong
- **Tiered next steps:** Immediate (do now) / Short-term (next quarter) / Long-term (future strategy) — each with suggested owners
- **What NOT to do:** Ideas explicitly invalidated by the research
- **Segment-specific insights:** How findings differ between participant segments
- **Contradictions and open questions:** Where participants disagreed and what the research still cannot answer

#### Acceptance criteria

- [x] Session notes can be entered via text paste, `.txt` file upload, or pre-loaded fixture — all three paths produce identical session objects in state.
- [x] Given raw notes from at least 2 sessions, the agent produces coded observations with type tags and session source attribution.
- [x] No observation is tagged as both "observation" and "interpretation" — the separation is enforced.
- [x] Themes require support from ≥2 sessions; single-source themes are flagged as "emerging, not confirmed."
- [x] Every theme includes a counterevidence field (populated or explicitly marked "none found").
- [x] Insight statements include all required fields: statement, evidence_strength, supporting_quotes, frequency, why_it_matters, user_segments_affected, current_workarounds, potential_solutions, priority, actionability, counterevidence, implication, assumption_status.
- [x] Decision record includes tiered next steps (immediate / short-term / long-term), what_not_to_do, segment_specific_insights, and contradictions_and_open_questions.
- [x] The decision record includes a confidence score with a transparent breakdown of how it was calculated.
- [x] Results are displayed across three tabs: Decision, Insights, Evidence Chain.
- [x] Evidence Chain tab provides 3-level nested drill-down: Insight → Theme → Observation → Session excerpt.
- [x] Node-level progress is shown via `st.status()` during synthesis (5 steps visible).
- [x] A stakeholder can trace backwards: Decision → Insight → Theme → Observation → Raw note + Session source.
- [x] The full synthesis output is exportable as a Markdown decision record.

---

## 5. Data Model

### Core entities and relationships

```
┌─────────────────┐
│  Study           │  The top-level container for a research cycle
│─────────────────│
│  id              │
│  title           │
│  hypothesis      │  Free-text problem statement / hypothesis
│  created_at      │
│  status          │  active | synthesised | decided
└────────┬────────┘
         │ 1:many
         ▼
┌─────────────────┐
│  Assumption      │  A discrete testable belief extracted from the hypothesis
│─────────────────│
│  id              │
│  study_id (FK)   │
│  statement       │  The assumption in plain language
│  risk_lens       │  desirability | usability | feasibility | viability
│  importance      │  1-5 (starts at LLM estimate; user-adjusted)
│  evidence_level  │  1-5 (starts at LLM estimate; user-adjusted)
│  importance_rationale│ One-sentence LLM rationale for the importance estimate
│  evidence_rationale│  One-sentence LLM rationale for the evidence estimate
│  risk_score      │  Computed: importance × (6 - evidence_level)
│  status          │  untested | confirmed | challenged | uncertain
│  research_question│ Generated research question for this assumption (all, not just top 3)
└────────┬────────┘
         │ 1:many (addressed by)
         ▼
┌─────────────────┐
│  Script          │  An interview discussion guide submitted for review
│─────────────────│
│  id              │
│  study_id (FK)   │
│  raw_text        │  The original script as submitted
│  clean_text      │  The de-biased rewrite
│  bias_score      │  % of questions that passed clean
│  created_at      │
└────────┬────────┘
         │ 1:many
         ▼
┌─────────────────┐
│  ScriptQuestion  │  Individual question extracted from a script
│─────────────────│
│  id              │
│  script_id (FK)  │
│  original_text   │  The question as written
│  verdict         │  pass | warning | rewrite_needed
│  issue_types[]   │  leading | hypothetical | solution_selling | closed | double_barrelled
│  explanation     │  Why this question is problematic
│  rewrite         │  Suggested de-biased alternative
└─────────────────┘

┌─────────────────┐
│  Session         │  A single research session (interview, observation, etc.)
│─────────────────│
│  id              │
│  study_id (FK)   │
│  participant_id  │  Anonymised label (e.g., "P1", "P2")
│  raw_notes       │  Full text of session notes
│  created_at      │
└────────┬────────┘
         │ 1:many
         ▼
┌─────────────────┐
│  Observation     │  A discrete, coded data point extracted from session notes
│─────────────────│
│  id              │
│  session_id (FK) │
│  type            │  behaviour | statement | context
│  content         │  The observation (verbatim quote or paraphrase)
│  is_interpretation│ Boolean — enforced as false at this stage
└────────┬────────┘
         │ many:many (via ThemeObservation join)
         ▼
┌─────────────────┐
│  Theme           │  A pattern identified across multiple observations
│─────────────────│
│  id              │
│  study_id (FK)   │
│  label           │  Short theme name
│  description     │  What this theme represents
│  session_count   │  Number of distinct sessions supporting this theme
│  counterevidence │  Observations or data that contradict/nuance this theme
│  assumption_id   │  FK to the assumption this theme addresses (nullable)
│  confidence      │  emerging | moderate | strong
└────────┬────────┘
         │ many:many (via InsightTheme join)
         ▼
┌─────────────────┐
│  Insight         │  A finding derived from one or more themes
│─────────────────│
│  id              │
│  study_id (FK)   │
│  statement       │  The insight in plain language
│  evidence_strength│ high | medium | low
│  counterevidence │  What complicates or limits this insight
│  implication     │  What this means for the product decision
│  assumption_id   │  FK to assumption addressed (nullable)
│  assumption_status│ confirmed | challenged | uncertain
│  supporting_quotes│ list[str] — verbatim quotes from session notes
│  frequency       │  "N out of M participants mentioned this"
│  why_it_matters  │  One sentence: business/UX/product impact
│  user_segments_affected│ Which participant types are most affected
│  current_workarounds│ How users solve this today without a purpose-built tool
│  potential_solutions│ list[str] — 2-3 solution directions to explore
│  priority        │  critical | high | medium | low
│  actionability   │  clear | fuzzy | needs_more_research
└────────┬────────┘
         │ many:1
         ▼
┌─────────────────┐
│  DecisionRecord  │  The final output — a traceable decision
│─────────────────│
│  id              │
│  study_id (FK)   │
│  question        │  The decision question being answered
│  recommendation  │  pursue | pivot | park | need_more_evidence
│  evidence_summary│  Narrative summary of key evidence
│  confidence_score│  0-100, computed from evidence strength + saturation + coverage
│  confidence_breakdown│ dict — per-component score breakdown (shown in UI)
│  descoped_items  │  What was not addressed and why
│  remaining_risks │  What could still be wrong
│  next_steps      │  Legacy field — kept for backwards compatibility
│  next_steps_immediate│ Actions to take now (with suggested owners)
│  next_steps_short_term│ Next quarter — validation, further exploration
│  next_steps_long_term│ Bigger strategic opportunities
│  what_not_to_do  │  Ideas explicitly invalidated by the research
│  segment_specific_insights│ How findings differ between participant segments
│  contradictions_and_open_questions│ Where participants disagreed; what the research can't yet answer
│  created_at      │
└─────────────────┘

Join tables:
  ThemeObservation  (theme_id, observation_id)
  InsightTheme      (insight_id, theme_id)
```

### Storage approach

For local development and demo, all data lives in **in-memory Python dictionaries** managed by a simple `StudyStore` class. No database required for local runs. The deployed AWS version provisions a DynamoDB table (wired in for v2 production hardening).

Sample data is loaded from **JSON fixture files** in `data/` so anyone can clone and run the demo with realistic mock data pre-loaded.

The demo ships with **7 fixture files**:

| Filename | Study ID | Topic |
|----------|----------|-------|
| `adtech_study.json` | `adtech-creative-optimisation` | Mid-market advertisers managing creative assets across channels — the primary walkthrough fixture |
| `audience_segmentation.json` | `audience-segmentation-automation` | Over-reliance on broad demographic targeting due to lack of accessible self-serve segmentation tooling |
| `attribution_modelling.json` | `attribution-modelling-gaps` | Systematic over-investment in last-click search because multi-touch attribution is inaccessible at mid-market scale |
| `campaign_pacing.json` | `campaign-pacing-optimisation` | Manual pacing adjustments causing 15–20% efficiency loss because DSP reallocation tools aren't suited to non-specialists |
| `creative_testing.json` | `creative-testing-scale` | Fewer than 3 creative variants per campaign because A/B test setup and analysis overhead outweighs perceived benefit |
| `frequency_management.json` | `cross-channel-frequency` | Unknowing audience saturation from display + social + video because no tool unifies frequency capping across DSPs |
| `empty_study.json` | — | Blank template for users entering their own hypothesis from scratch |

Each non-empty fixture includes: 8–10 pre-rated assumptions across all 4 risk lenses, 1 interview script (mix of clean and biased questions), and 5 mock sessions (P1–P5) with rich narrative notes including at least 1–2 sceptical participants. Users can also upload their own study JSON via the home page file uploader.

---

## 6. Agentic Architecture

### Technology stack

| Component | Choice | Rationale                                                                                                                                                                                                                                                                 |
|----------|--------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Orchestration | **LangGraph** | PM has direct experience from AWS tutorial; graph-based state management maps naturally to the multi-step research workflow; well-suited to human-in-the-loop patterns at the interactive rating step.                                                                    |
| LLM | **Claude Sonnet 4 (via AWS Bedrock)** | Best reasoning for structured analysis tasks; IAM-authenticated so no API key to manage; consistent with the AWS deployment. Model ID: `us.anthropic.claude-sonnet-4-20250514-v1:0` (cross-region inference profile — required for Claude 4). Swappable via `src/llm.py`. |
| UI | **Streamlit** | Fast to build, handles the interactive rating step cleanly, and renders visual outputs (assumption maps, traceable synthesis chains) well. Not a CLI — outputs need to be seen, not read in a terminal.                                                                   |
| Language | **Python 3.11+** | LangGraph native; Streamlit native; readable for both technical and non-technical contributors.                                                                                                                                                                           |
| Storage | **In-memory locally / DynamoDB deployed** | Local run has zero setup friction; deployed version uses DynamoDB for cross-session persistence. Fixture JSON files (`data/`) for sample data locally; S3 in production.                                                                                                  |
| Hosting | **ECS Fargate + ALB** | App Runner does not support WebSocket connections, which Streamlit requires. ALB natively supports WebSocket upgrades. Single `cdk deploy` provisions all AWS resources.                                                                                                  |

### LangGraph graph structure

The system is a single LangGraph `StateGraph` with conditional branching based on which capability the user is invoking. The shared state object (`StudyState`) carries the full study context across nodes.

```
                    ┌─────────────────┐
                    │   Entry Router   │  Determines which workflow to run
                    │   (deterministic)│  based on user selection
                    └───────┬─────────┘
                            │
              ┌─────────────┼──────────────┐
              ▼             ▼              ▼
   ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐
   │  Assumption   │ │   Script     │ │    Synthesis      │
   │  Mapping Flow │ │   Review Flow│ │    Flow           │
   └──────┬───────┘ └──────┬───────┘ └──────┬───────────┘
          │                │                │
          ▼                ▼                ▼
   ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐
   │  Decompose    │ │  Parse       │ │  Ingest Notes     │
   │  Hypothesis   │ │  Questions   │ │  (deterministic)  │
   │  (LLM)        │ │ (deterministic)│ └──────┬───────────┘
   └──────┬───────┘ └──────┬───────┘        │
          │                │                ▼
          ▼                ▼         ┌──────────────────┐
   ┌──────────────┐ ┌──────────────┐ │  Open Coding      │
   │  Categorise   │ │  Analyse     │ │  (LLM)            │
   │  by Risk Lens │ │  Each Q for  │ │  Extract           │
   │  (LLM)        │ │  Bias (LLM)  │ │  observations      │
   └──────┬───────┘ └──────┬───────┘ └──────┬───────────┘
          │                │                │
          ▼                ▼                ▼
   ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐
   │  Interactive   │ │  Generate    │ │  Axial Coding     │
   │  Rating        │ │  Rewrites   │ │  (LLM)            │
   │ (human-in-loop)│ │  (LLM)      │ │  Cluster to themes │
   └──────┬───────┘ └──────┬───────┘ │  + counterevidence │
          │                │         └──────┬───────────┘
          ▼                ▼                │
   ┌──────────────┐ ┌──────────────┐        ▼
   │  Compute      │ │  Assemble    │ ┌──────────────────┐
   │  Risk Scores  │ │  Clean Script│ │  Selective Coding  │
   │  + Generate   │ │  + Summary   │ │  (LLM)            │
   │  Research Qs  │ │ (deterministic)│ │  Generate insights │
   │  (LLM + calc) │ └──────────────┘ └──────┬───────────┘
   └──────┬───────┘                          │
          │                                  ▼
          ▼                          ┌──────────────────┐
   ┌──────────────┐                  │  Decision Record   │
   │  Output       │                  │  (LLM + calc)      │
   │  Assumption   │                  │  Generate decision  │
   │  Map          │                  │  + confidence score │
   │ (deterministic)│                  └──────────────────┘
   └──────────────┘
```

### Node specifications

| Node | Type | Input | Output | Notes |
|------|------|-------|--------|-------|
| `entry_router` | Deterministic | User's menu selection | Routes to one of three sub-flows | Simple conditional edge |
| `decompose_hypothesis` | LLM call | Free-text hypothesis | List of 5-10 assumption objects | Structured output with JSON schema |
| `categorise_risk_lens` | LLM call | Assumption list | Same list with risk_lens tags | Could merge with decompose; separated for clarity and debuggability |
| `interactive_rating` | Human-in-the-loop | Assumption list | Same list with importance + evidence scores | Streamlit widget; user rates each assumption |
| `compute_risk_scores` | Deterministic + LLM | Rated assumptions | Ranked list + research questions for **all** assumptions | Risk score is arithmetic; research questions are LLM-generated for every assumption |
| `output_assumption_map` | Deterministic | Ranked assumptions | Formatted display (table + 2×2 matrix) | Streamlit rendering |
| `parse_questions` | Deterministic | Raw script text | List of individual question strings | Regex/split logic |
| `analyse_bias` | LLM call | Individual question + bias taxonomy | Verdict + issue types + explanation | One LLM call per question (can batch) |
| `generate_rewrites` | LLM call | Flagged question + issue type | De-biased rewrite | Separate from analysis for cleaner prompts |
| `assemble_clean_script` | Deterministic | All questions with verdicts/rewrites | Clean script block + summary stats | String assembly |
| `ingest_notes` | Deterministic | Raw session notes (text blocks) | Session objects in state | Parsing and ID assignment |
| `open_coding` | LLM call | Session notes + assumption map context | List of tagged observations | The heaviest LLM call; processes each session |
| `axial_coding` | LLM call | All observations across sessions | Candidate themes with session counts + counterevidence | Clustering with minimum 2-session threshold |
| `selective_coding` | LLM call | Themes + assumption map | Insight statements following template | Structured output |
| `decision_record` | LLM + deterministic | Insights + assumption map | Decision record with confidence score | Score calculation is deterministic; narrative is LLM |

### State management

The `StudyState` is a TypedDict (LangGraph convention) that accumulates data as the user moves through the workflow:

```python
class StudyState(TypedDict):
    # Study metadata
    study_id: str
    hypothesis: str
    status: str  # active | synthesised | decided

    # Assumption mapping
    assumptions: list[Assumption]
    assumption_map_complete: bool

    # Script review
    scripts: list[Script]
    script_questions: list[ScriptQuestion]

    # Synthesis
    sessions: list[Session]
    observations: list[Observation]
    themes: list[Theme]
    insights: list[Insight]
    decision_record: Optional[DecisionRecord]

    # Flow control
    current_flow: str  # assumption_mapping | script_review | synthesis
    messages: list[str]  # User-facing messages / status updates
```

### Where LLM calls happen vs. deterministic logic

| LLM calls (require reasoning) | Deterministic (no LLM needed) |
|-------------------------------|------------------------------|
| Decomposing hypothesis into assumptions | Routing between flows |
| Categorising assumptions by risk lens | Computing risk scores (importance × inverse evidence) |
| Generating research questions for top assumptions | Parsing script text into individual questions |
| Analysing each question for bias patterns | Assembling clean script from rewrites |
| Generating de-biased rewrites | Ingesting and splitting raw session notes |
| Extracting observations from session notes (open coding) | Enforcing 2-session minimum for themes |
| Clustering observations into themes (axial coding) | Computing confidence scores |
| Generating insight statements (selective coding) | Rendering outputs in Streamlit |
| Writing decision record narrative | Exporting to markdown |

**Design principle:** Every LLM output is structured (JSON schema or clear template) so it can be validated deterministically before being stored in state. If the LLM returns malformed output, the node retries once with a corrective prompt, then fails with a clear error rather than passing garbage downstream.

---

## 7. Product Decisions

### What's in and why

| Decision | Rationale |
|---------|-----------|
| **Three capabilities, not seven** | A weekend-scoped demo needs to be completable end-to-end. Three capabilities that chain together (map assumptions → review script → synthesise findings) tell a coherent story. Seven half-built features tell none. |
| **Streamlit over CLI** | The outputs of this tool are visual — assumption maps, bias-annotated scripts, traceable synthesis chains. A CLI would force users to imagine what these look like. Streamlit lets them see it. |
| **In-memory locally, DynamoDB deployed** | Local run has zero setup friction — `pip install → streamlit run → working demo` in under 2 minutes. Deployed version uses DynamoDB so user state persists across sessions. No local database infra required. |
| **6 pre-loaded adtech sample studies** | The demo must work without requiring a user to create data. Six complete fixtures (each with assumptions, script, and 5 sessions) let anyone explore the full workflow immediately. Users can also upload their own study JSON. |
| **LangGraph over simple function chaining** | The tool could be built as sequential function calls. LangGraph adds complexity — but it's complexity that demonstrates understanding of agentic architecture, human-in-the-loop patterns, and state management. The architecture is the point. |
| **Hybrid LLM + deterministic** | Pure LLM would be non-reproducible. Pure rules would be brittle. The design uses LLM for reasoning tasks (decomposition, coding, synthesis) and deterministic logic for scoring, routing, and validation. This is a deliberate product decision about reliability vs. flexibility. |
| **Claude as primary LLM** | Strong reasoning capability for structured analysis tasks. Every LLM node uses a thin wrapper so switching providers requires changing one config, not refactoring code. |

### What's out and why

| Decision | Rationale |
|---------|-----------|
| **No persistent database** | No benefit for single-session local use. Revisit in v2 for repository feature. |
| **No multi-user / team features** | Weekend scope. The tool models a single PM's workflow, not team collaboration. |
| **Transcript upload (.txt only)** | `.txt` file upload is supported in v1.1 for synthesis sessions — upload one file per participant, filename is used to auto-detect the participant ID. Richer formats (docx, PDF, audio transcription) remain a v2 feature. |
| **No real-time interview companion** | The playbook describes an execution assistant that runs *during* interviews. This is architecturally different (streaming, real-time, voice) and is a separate product. The MVP reviews scripts *before* interviews and synthesises notes *after*. |
| **No ethics/consent workflow** | Important for production but adds screens without adding demo impact. Addressed in README as a roadmap item with design rationale. |
| **No survey or quant method support** | MVP focuses on qualitative interview research, the most common PM scenario. Quant support requires different data models and analysis logic. |

### Risks accepted

| Risk | Mitigation |
|------|-----------|
| LLM hallucination in synthesis — the agent could generate themes or insights not grounded in the actual notes | Every insight requires linked observation IDs. The UI shows the chain. Any claim can be verified. |
| Bias detection has false positives/negatives | The test set of 20 known-bad questions provides a measurable baseline. The README will state the accuracy transparently. |
| Demo feels like "just a wrapper around an LLM" | The deterministic scoring, structured data model, enforced quality gates (2-session minimum, counterevidence fields), and traceable chain are all non-LLM value. The README "Product Decisions" section makes this explicit. |

---

## 8. Future Roadmap

### v2 — Research Quality Platform

| Capability | Description | Effort |
|-----------|-------------|--------|
| **Full Quality Rubric** | Standalone scoring across 6 dimensions (decision clarity, signal strength, participant relevance, bias control, actionability, efficiency) with 1-5 anchored scales. Auto-generated after study completion. | Medium |
| **Research Repository** | Persistent storage (SQLite or Supabase) with tagging taxonomy (decision type, segment, journey step, feature area, geography). Duplicate-detection alerts when a new study overlaps with an existing one. | Large |
| **Method Recommender** | Given a decision type and risk lens, recommend the optimal research method(s) from the full taxonomy (contextual inquiry, diary studies, usability tests, surveys, A/B tests, etc.) with heuristic sample sizes and time/cost estimates. | Medium |
| **Ethics & Consent Module** | GDPR-aware consent script generator, data minimisation checklist, special category data warnings, and regulated-context playbooks (healthcare, fintech, children). | Medium |
| **Rich File Upload & Transcription** | `.txt` transcript upload is already supported (v1.1). v2 extends to .docx, .pdf, and audio files. Audio transcription via Whisper. | Medium |

### v3 — Team & Integration

| Capability | Description | Effort |
|-----------|-------------|--------|
| **Multi-user collaboration** | Shared studies, role-based access (PM, researcher, stakeholder viewer), comment threads on insights. | Large |
| **Tool integrations** | Export to Jira/Linear (decision records as tickets), Notion (synthesis docs), Figma (insight annotations). | Medium |
| **Real-time interview companion** | Live transcription + bias detection during interviews. Different architecture (streaming, WebSocket). | Large |
| **Automated saturation detection** | After each new session is coded, calculate whether new themes are still emerging or the study has reached theoretical saturation. Advise "stop — you have enough data" or "continue — here's what's still thin." | Medium |

---

## 9. README Outline

The repository README should follow this structure to function as a product document:

```markdown
# Discovery Rigor Engine
> An agentic tool that brings process discipline to PM-led user research —
> from assumption mapping through synthesis to traceable decisions.

## The Problem
[2-3 paragraphs: PM-led research fails from lack of process, not lack of effort.
Key failure modes. Why existing tools stop at planning.]

## The Solution
[What this tool does. The three capability areas. Where it sits in the workflow.
Include the positioning diagram.]

## Demo
[Screenshot or GIF of the tool running with sample data.
"Clone → install → run in 2 minutes" instructions.]

## How It Works
### Architecture
[Architecture diagram — the LangGraph flow chart above, rendered as an image.]
[Brief explanation of which nodes use LLM vs. deterministic logic and why.]

### Data Model
[Simplified entity diagram. Explain the traceability chain:
Decision → Insight → Theme → Observation → Raw note.]

## Product Decisions
[The full "What's in and why / What's out and why" table from section 7.]

## Sample Walkthrough
[Step-by-step narrative of using the tool with the adtech fixture data:
1. Load the sample study
2. View the assumption map
3. Paste the sample script → see bias flags → get clean rewrite
4. Run synthesis on mock interview notes
5. Read the decision record with confidence score
6. Trace a decision back to raw evidence]

## Roadmap
[v2 and v3 tables from section 8.]

## Tech Stack
[Table from section 6.]

## Setup & Run
```bash
git clone ...
cd discovery-rigor-engine
pip install -r requirements.txt
# Configure AWS credentials (Bedrock is the LLM provider)
aws configure
# Enable Claude Sonnet 4 model access in AWS Bedrock console (us-east-1) first
streamlit run app.py
```

## Deploy
```bash
cd infrastructure/
pip install -r requirements.txt
cdk bootstrap && cdk deploy
# Outputs the public ALB URL
```

## About
[Brief bio. PM with adtech background. Link to other projects.]
```

---

## 10. Sample Data Specification

All fixtures are realistic enough that someone familiar with digital advertising immediately recognises the scenario. The primary fixture is documented below; the other five follow the same structure.

### Primary Study: "Creative Asset Optimisation for Mid-Market Advertisers"

**Hypothesis:** "We believe mid-market advertisers (50-500 employees) waste significant time manually adapting creative assets across channels (Meta, Google, TikTok, programmatic) because they lack automated tools that provide real-time performance feedback at the creative level, leading to suboptimal ad performance and inefficient use of media budgets."

**Pre-built assumptions (10):**
1. Mid-market advertisers manage creative across 3+ channels simultaneously (desirability)
2. Manual creative adaptation is a top-3 workflow pain point (desirability)
3. Existing tools (Canva, Adobe, platform-native) don't solve cross-channel optimisation (desirability)
4. Advertisers can interpret creative-level performance data without analyst support (usability)
5. Real-time cross-channel creative data is technically accessible via platform APIs (feasibility)
6. Creative teams would trust AI-generated optimisation recommendations (usability)
7. Advertisers would pay $500-2000/mo for this capability (viability)
8. This doesn't cannibalise existing analytics products in their stack (viability)
9. Creative performance attribution is accurate enough to be actionable (feasibility)
10. Legal/brand compliance review doesn't block automated creative changes (viability)

**Sample interview script (with deliberate bias problems):**
- "Don't you find it frustrating to manage creative assets across multiple channels?" (leading)
- "Would you use a tool that automatically optimised your creatives?" (hypothetical + solution-selling)
- "How helpful would AI-powered creative recommendations be for your team?" (leading)
- "Tell me about the last time you launched a campaign across multiple channels." (clean)
- "Walk me through how you currently decide which creative to use on which channel." (clean)
- "If we built a dashboard that showed real-time creative performance, would you pay for it?" (hypothetical + solution-selling)
- "Is creative optimisation a problem for your team?" (closed/binary)
- "What tools do you currently use for creative management, and how do you measure their effectiveness?" (double-barrelled)
- "Describe the last time a creative asset underperformed. What happened?" (clean)
- "How much time per week does your team spend on creative adaptation?" (clean)

**5 mock interview sessions** with realistic notes covering:
- P1: Marketing Director at a DTC brand, heavy Meta/Google user, frustrated with manual process
- P2: Media Buyer at an agency, uses platform-native tools, sceptical of automation
- P3: Creative Operations Lead, manages 200+ assets/month, workaround-heavy workflow
- P4: Growth Marketer at a B2B SaaS company, minimal creative resources, relies on templates
- P5: Brand Manager, concerned about brand consistency across automated changes

Each session should include a mix of supporting evidence, counterevidence, and nuance — not uniformly positive. P2 and P5 in particular should challenge the hypothesis.

---

## 11. Success Metrics

| Metric | Target | How to measure |
|--------|--------|---------------|
| **Time to demo (live)** | Zero — click the live URL | User hits the ALB URL directly, no setup required |
| **Time to demo (local)** | < 5 minutes from clone to running Streamlit app | Requires AWS credentials configured; test on a clean machine |
| **End-to-end walkthrough** | A user can complete the full flow (assumption map → script review → synthesis → decision record) in < 15 minutes using sample data | Timed user test |
| **Bias detection accuracy** | ≥ 80% true positive rate on the 20-question test set; ≤ 15% false positive rate on clean questions | Automated test script |
| **Traceability completeness** | 100% of insights link to ≥1 observation; 100% of themes link to ≥2 sessions; decision record references all insights | Automated validation check |
| **README completeness** | README includes: problem statement, positioning diagram, product decisions table, architecture diagram, roadmap, sample walkthrough | Checklist review |
| **Code readability** | No function longer than 50 lines; every LLM prompt is in a separate, readable template file; no clever abstractions — straightforward sequential logic | Code review |

---

*End of PRD. Ready for development.*
