"""
Scorer node — computes semantic matching scores using the LLM.

Uses the configured AI provider to semantically evaluate:
- Technical skills match
- Experience relevance
- Computes a weighted global score
"""

import json

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.state import AnalyseState
from app.core.logging import get_logger
from app.services.provider_service import ProviderService

logger = get_logger(__name__)

SCORER_SYSTEM_PROMPT = """You are an expert HR analyst and ATS specialist.
Your task is to analyze the match between a CV and a job offer.

Respond ONLY with a valid JSON object in this exact format:
{
    "score_competences": <integer 0-100>,
    "score_experience": <integer 0-100>,
    "reasoning": {
        "competences": "<brief explanation>",
        "experience": "<brief explanation>"
    }
}

Scoring guidelines:
- score_competences: How well the technical skills in the CV match the job requirements
- score_experience: How relevant the years and type of experience are to the role
- 0 = no match, 50 = partial match, 80+ = strong match, 100 = perfect match
"""


def _build_scorer_prompt(cv_text: str, job_text: str, language: str) -> str:
    lang_instruction = "Analyze in French." if language == "fr" else "Analyze in English."
    return (
        f"{lang_instruction}\n\n"
        f"=== JOB OFFER ===\n{job_text[:3000]}\n\n"
        f"=== CANDIDATE CV ===\n{cv_text[:3000]}"
    )


def compute_global_score(
    score_ats: int,
    score_competences: int,
    score_experience: int,
) -> int:
    """
    Computes a weighted global matching score.

    Weights:
    - ATS score:       30%
    - Competences:     45%
    - Experience:      25%

    Args:
        score_ats:          ATS keyword match score (0-100).
        score_competences:  Technical skills score (0-100).
        score_experience:   Experience relevance score (0-100).

    Returns:
        Weighted global score as integer 0-100.
    """
    return int(round(
        score_ats * 0.30
        + score_competences * 0.45
        + score_experience * 0.25
    ))


async def compute_score_node(state: AnalyseState) -> dict:
    """
    LangGraph node: uses LLM to compute semantic scores.

    Calls the configured AI provider to semantically evaluate
    skill and experience alignment. Falls back to ATS-based scoring
    if the LLM call fails.

    Args:
        state: Pipeline state with cv/job text, provider, model, api_key.

    Returns:
        State updates: competence score, experience score, global score, SSE event.
    """
    try:
        llm = ProviderService.get_llm(
            provider=state["provider"],
            model=state["model"],
            api_key=state["api_key"],
        )

        messages = [
            SystemMessage(content=SCORER_SYSTEM_PROMPT),
            HumanMessage(
                content=_build_scorer_prompt(
                    state["cv_text"],
                    state["job_text"],
                    state.get("language", "fr"),
                )
            ),
        ]
        raw_content = None
        for chunk in llm.stream(messages):
            raw_content = chunk if raw_content is None else raw_content + chunk

        json_content = raw_content.text.replace("```json", "").replace("```", "")

        # Parse JSON from LLM response
        parsed = json.loads(json_content)
        score_competences = int(parsed.get("score_competences", 70))
        score_experience = int(parsed.get("score_experience", 70))

    except Exception as exc:
        logger.warning(
            "Scorer LLM call failed — using fallback scoring",
            exc_info=exc,
            extra={"provider": state.get("provider"), "model": state.get("model")},
        )
        # Fallback: derive competences from ATS, experience from partial ATS
        score_competences = min(state.get("score_ats", 60) + 10, 100)
        score_experience = max(state.get("score_ats", 60) - 5, 0)

    score_global = compute_global_score(
        score_ats=state.get("score_ats", 0),
        score_competences=score_competences,
        score_experience=score_experience,
    )

    progress_event = {
        "type": "progress",
        "step": "scoring",
        "progress": 65,
        "data": {
            "score_global": score_global,
            "score_competences": score_competences,
            "score_experience": score_experience,
        },
    }

    logger.info(
        "Scorer node executed",
        extra={
            "score_global": score_global,
            "score_competences": score_competences,
            "score_experience": score_experience,
        },
    )

    return {
        "score_competences": score_competences,
        "score_experience": score_experience,
        "score_global": score_global,
        "stream_events": state.get("stream_events", []) + [progress_event],
    }
