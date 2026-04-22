"""
LangGraph analysis pipeline.

Defines the StateGraph with 4 sequential nodes:
  parse_documents → compute_ats → compute_score → generate_recommendations
"""

from langgraph.graph import END, START, StateGraph

from app.agents.nodes.ats import compute_ats_node
from app.agents.nodes.parser import parse_documents
from app.agents.nodes.recommender import generate_recommendations_node
from app.agents.nodes.scorer import compute_score_node
from app.agents.state import AnalyseState
from app.core.logging import get_logger

logger = get_logger(__name__)


def build_analyse_graph() -> StateGraph:
    """
    Builds and compiles the LangGraph analysis pipeline.

    Graph structure:
        START
          ↓
        parse_documents      — validates and normalizes text
          ↓
        compute_ats          — keyword extraction + ATS score
          ↓
        compute_score        — LLM semantic scoring
          ↓
        generate_recommendations  — LLM recommendation generation
          ↓
        END

    Returns:
        Compiled LangGraph StateGraph ready for execution.
    """
    graph = StateGraph(AnalyseState)

    # Register nodes
    graph.add_node("parse_documents", parse_documents)
    graph.add_node("compute_ats", compute_ats_node)
    graph.add_node("compute_score", compute_score_node)
    graph.add_node("generate_recommendations", generate_recommendations_node)

    # Define edges (sequential pipeline)
    graph.add_edge(START, "parse_documents")
    graph.add_edge("parse_documents", "compute_ats")
    graph.add_edge("compute_ats", "compute_score")
    graph.add_edge("compute_score", "generate_recommendations")
    graph.add_edge("generate_recommendations", END)

    compiled = graph.compile()
    logger.info("LangGraph analysis pipeline compiled successfully")
    return compiled


# Singleton graph instance
analyse_graph = build_analyse_graph()
