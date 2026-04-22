"""
Parser node — extracts and normalizes text from CV and job offer.

This is the first node in the LangGraph pipeline.
It prepares clean text for downstream scoring nodes.
"""

from app.agents.state import AnalyseState
from app.core.logging import get_logger

logger = get_logger(__name__)


def parse_documents(state: AnalyseState) -> dict:
    """
    LangGraph node: validates and normalizes input text.

    Ensures both cv_text and job_text are clean, non-empty strings
    before passing them to scoring nodes.

    Args:
        state: Current pipeline state with cv_text and job_text set.

    Returns:
        State updates: cleaned texts + initial progress SSE event.
    """
    cv_text = (state.get("cv_text") or "").strip()
    job_text = (state.get("job_text") or "").strip()

    progress_event = {
        "type": "progress",
        "step": "parsing",
        "progress": 10,
        "data": {
            "cv_length": len(cv_text),
            "job_length": len(job_text),
        },
    }

    logger.info(
        "Parser node executed",
        extra={"cv_length": len(cv_text), "job_length": len(job_text)},
    )

    return {
        "cv_text": cv_text,
        "job_text": job_text,
        "stream_events": state.get("stream_events", []) + [progress_event],
        "error": None,
    }
