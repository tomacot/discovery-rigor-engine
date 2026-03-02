"""
LangGraph StateGraph definition.

Wires the three sub-flows (Assumption Mapping, Script Review, Synthesis) into a
single compilable graph. Each sub-flow branches from START via a conditional edge
driven by the `current_flow` field in StudyState.

Why the graph is split into two assumption-mapping phases:
  Phase 1 (decompose → categorise) ends at END so Streamlit can render the
  categorised assumptions and let the user rate them. Phase 2 (score →
  research questions) is invoked separately after the user submits ratings.
  This is simpler than LangGraph's interrupt mechanism — the human-in-the-loop
  step lives entirely in Streamlit widgets, not in the graph.

This file only wires nodes together. No business logic lives here.
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from src.nodes.assumption_categorise import categorise_risk_lens
from src.nodes.assumption_decompose import decompose_hypothesis
from src.nodes.assumption_research_qs import generate_research_questions
from src.nodes.assumption_score import compute_risk_scores
from src.nodes.router import route_to_flow
from src.nodes.script_analyse_bias import analyse_bias
from src.nodes.script_assemble import assemble_clean_script
from src.nodes.script_parse import parse_questions
from src.nodes.script_rewrite import rewrite_questions
from src.nodes.synthesis_axial_coding import axial_coding
from src.nodes.synthesis_decision import decision_record_node
from src.nodes.synthesis_ingest import ingest_notes
from src.nodes.synthesis_open_coding import open_coding
from src.nodes.synthesis_selective import selective_coding
from src.state import StudyState


def build_graph():
    """
    Build and return the compiled LangGraph StateGraph.

    Call once per Streamlit session and store in st.session_state — compilation
    validates the graph structure and is not cheap to repeat on every rerun.
    """
    graph = StateGraph(StudyState)

    # --- Register all nodes ---
    graph.add_node("decompose_hypothesis", decompose_hypothesis)
    graph.add_node("categorise_risk_lens", categorise_risk_lens)
    graph.add_node("compute_risk_scores", compute_risk_scores)
    graph.add_node("generate_research_questions", generate_research_questions)
    graph.add_node("parse_questions", parse_questions)
    graph.add_node("analyse_bias", analyse_bias)
    graph.add_node("rewrite_questions", rewrite_questions)
    graph.add_node("assemble_clean_script", assemble_clean_script)
    graph.add_node("ingest_notes", ingest_notes)
    graph.add_node("open_coding", open_coding)
    graph.add_node("axial_coding", axial_coding)
    graph.add_node("selective_coding", selective_coding)
    graph.add_node("decision_record_node", decision_record_node)

    # --- Route from START based on current_flow ---
    # route_to_flow(state) -> node name to execute first
    graph.add_conditional_edges(START, route_to_flow)

    # --- Assumption Mapping Phase 1 ---
    # decompose → categorise → END (user rates in Streamlit before phase 2)
    graph.add_edge("decompose_hypothesis", "categorise_risk_lens")
    graph.add_edge("categorise_risk_lens", END)

    # --- Assumption Mapping Phase 2 ---
    # score → research questions → END
    graph.add_edge("compute_risk_scores", "generate_research_questions")
    graph.add_edge("generate_research_questions", END)

    # --- Script Review ---
    # parse → analyse → rewrite → assemble → END
    graph.add_edge("parse_questions", "analyse_bias")
    graph.add_edge("analyse_bias", "rewrite_questions")
    graph.add_edge("rewrite_questions", "assemble_clean_script")
    graph.add_edge("assemble_clean_script", END)

    # --- Synthesis ---
    # ingest → open coding → axial coding → selective coding → decision → END
    graph.add_edge("ingest_notes", "open_coding")
    graph.add_edge("open_coding", "axial_coding")
    graph.add_edge("axial_coding", "selective_coding")
    graph.add_edge("selective_coding", "decision_record_node")
    graph.add_edge("decision_record_node", END)

    return graph.compile()
