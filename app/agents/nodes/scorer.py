"""
Scorer node — computes semantic matching scores using the LLM.

Uses the configured AI provider to semantically evaluate:
- Technical skills match
- Experience relevance
- Computes a weighted global score
"""

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

from app.agents.state import AnalyseState
from app.core.logging import get_logger
from app.services.provider_service import ProviderService

logger = get_logger(__name__)

class ScoreReasoning(BaseModel):
    competences: str = Field(..., description="Brief explanation of the competence score")
    experience: str = Field(..., description="Brief explanation of the experience score")

class ScoreResult(BaseModel):
    score_competences: int = Field(default=70, ge=0, le=100, description="Technical skills score (0-100)" )
    score_experience: int = Field(default=70, ge=0, le=100, description="Experience relevance score (0-100)")
    reasoning: ScoreReasoning = Field(..., description="Reasoning behind the scores")

def _build_scorer_system_prompt(language: str) -> str:
    lang = "French" if language == "fr" else "English"
    return f"""You are an expert HR analyst and ATS specialist.
Your task is to analyze the match between a CV and a job offer.
IMPORTANT: All text values in the JSON (reasoning fields) MUST be written in {lang}.

Respond ONLY with a valid JSON object in this exact format:
{{
    "score_competences": <integer 0-100>,
    "score_experience": <integer 0-100>,
    "reasoning": {{
        "competences": "<brief explanation in {lang}>",
        "experience": "<brief explanation in {lang}>"
    }}
}}

Scoring guidelines:
- score_competences: How well the technical skills in the CV match the job requirements
- score_experience: How relevant the years and type of experience are to the role
- 0 = no match, 50 = partial match, 80+ = strong match, 100 = perfect match"""


def _build_scorer_prompt(cv_text: str, job_text: str) -> str:
    return (
        f"=== JOB OFFER ===\n{job_text}\n\n"
        f"=== CANDIDATE CV ===\n{cv_text}"
    )


def _coerce_score(value: object) -> int | None:
    """
    Converts an LLM-provided score into a clamped 0-100 integer.

    LLMs sometimes answer with "85", 85.0, or the literal schema placeholder
    "<integer 0-100>". Anything that is not a number is rejected so the caller
    can fall back instead of silently scoring 0.

    Args:
        value: Raw value taken from the parsed JSON response.

    Returns:
        Integer in 0-100, or None if the value is not a usable number.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return None
    try:
        score = round(float(value))
    except ValueError:
        return None
    return max(0, min(100, score))


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
    return round(
        score_ats * 0.30
        + score_competences * 0.45
        + score_experience * 0.25
    )


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

        parser = JsonOutputParser(pydantic_object=ScoreResult)

        language = state.get("language", "fr")

        # The messages are built directly rather than through ChatPromptTemplate:
        # from_messages() treats SystemMessage/HumanMessage instances as literal
        # messages, so a "{input}" placeholder would be sent to the LLM verbatim
        # instead of being replaced by the CV. Building them here also avoids
        # having to brace-escape CV text that may legitimately contain "{".
        messages = [
            SystemMessage(content=_build_scorer_system_prompt(language)),
            HumanMessage(content=_build_scorer_prompt(state["cv_text"], state["job_text"])),
        ]

        chain = llm | parser
        response = await chain.ainvoke(messages)

        score_competences = _coerce_score(response.get("score_competences"))
        score_experience = _coerce_score(response.get("score_experience"))

        if score_competences is None or score_experience is None:
            raise ValueError(f"LLM returned unusable scores: {response!r}")

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
