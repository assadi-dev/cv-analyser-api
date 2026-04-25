"""
Recommender node — generates personalized AI recommendations.

Uses the LLM to produce actionable, prioritized recommendations
based on the analysis results.
"""

from typing import Literal
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field
from langchain_core.output_parsers import JsonOutputParser
from app.agents.state import AnalyseState
from app.core.logging import get_logger
from app.services.provider_service import ProviderService
from langchain_core.prompts import ChatPromptTemplate

logger = get_logger(__name__)


class Recommendation(BaseModel):
    type: Literal["warning", "success", "info"] = Field(..., description="Type of recommendation")
    title: str = Field(..., description="Title of recommendation")
    description: str = Field(..., description="Description of recommendation")
    impact: Literal["high", "medium", "low"] = Field(..., description="Impact of recommendation")


RECOMMENDER_SYSTEM_PROMPT = """You are an expert career coach and CV optimization specialist.
Based on the CV-job match analysis, generate clear, actionable recommendations.

Respond ONLY with a valid JSON array of recommendation objects:
[
   {{
        "type": "warning|success|info",
        "title": "<short title (max 60 chars)>",
        "description": "<actionable explanation (max 200 chars)>",
        "impact": "high|medium|low"
    }}
]

Rules:
- "warning": something missing or needing improvement
- "success": a strong point to highlight
- "info": a neutral tip or suggestion
- Sort by impact: high → medium → low
- Maximum 5 recommendations
- Be specific and actionable, not generic
"""


def _build_recommender_prompt(state: AnalyseState, language: str) -> str:
    lang = "French" if language == "fr" else "English"
    missing = ", ".join(state.get("keywords_missing", [])[:10])
    return (
        f"Generate recommendations in {lang}.\n\n"
        f"=== ANALYSIS RESULTS ===\n"
        f"Global score: {state.get('score_global', 0)}/100\n"
        f"ATS score: {state.get('score_ats', 0)}/100\n"
        f"Skills score: {state.get('score_competences', 0)}/100\n"
        f"Experience score: {state.get('score_experience', 0)}/100\n\n"
        f"Missing keywords: {missing or 'None'}\n\n"
        f"=== JOB OFFER (excerpt) ===\n{state.get('job_text', '')[:1500]}\n\n"
        f"=== CV (excerpt) ===\n{state.get('cv_text', '')[:1500]}"
    )


_FALLBACK_RECOMMENDATIONS: list[dict] = [
    {
        "type": "info",
        "title": "Add missing keywords",
        "description": "Include the keywords identified as missing to improve your ATS score.",
        "impact": "high",
    },
    {
        "type": "info",
        "title": "Quantify your achievements",
        "description": "Add numbers and metrics to your experience descriptions.",
        "impact": "medium",
    },
]


async def generate_recommendations_node(state: AnalyseState) -> dict:
    """
    LangGraph node: generates AI-powered recommendations.

    Args:
        state: Full pipeline state with all computed scores and keywords.

    Returns:
        State updates: recommendations list + SSE progress and result events.
    """
    language = state.get("language", "fr")

    try:
        parser = JsonOutputParser(pydantic_object=Recommendation)

        llm = ProviderService.get_llm(
            provider=state["provider"],
            model=state["model"],
            api_key=state["api_key"],
        )

        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=RECOMMENDER_SYSTEM_PROMPT),
            HumanMessage(content="{input}"),
        ])

        chain = prompt | llm | parser

        response = await chain.ainvoke({"input": _build_recommender_prompt(state, language)})

        recommandations: list[dict] = response

    except Exception as exc:
        logger.warning(
            "Recommender LLM call failed — using fallback recommendations",
            exc_info=exc,
        )
        recommandations = _FALLBACK_RECOMMENDATIONS

    # Progress event
    progress_event = {
        "type": "progress",
        "step": "recommendations",
        "progress": 90,
        "data": {"count": len(recommandations)},
    }

    # Final result event
    result_event = {
        "type": "result",
        "score_global": state.get("score_global", 0),
        "score_ats": state.get("score_ats", 0),
        "score_competences": state.get("score_competences", 0),
        "score_experience": state.get("score_experience", 0),
        "keywords_found": state.get("keywords_found", []),
        "keywords_missing": state.get("keywords_missing", []),
        "recommandations": recommandations,
    }

    logger.info(
        "Recommender node executed",
        extra={"recommendations_count": len(recommandations)},
    )

    return {
        "recommandations": recommandations,
        "stream_events": state.get("stream_events", []) + [progress_event, result_event],
    }
