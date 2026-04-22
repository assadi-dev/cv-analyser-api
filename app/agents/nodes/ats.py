"""
ATS node — computes the ATS compatibility score.

Extracts keywords from the job offer and measures how many
appear in the candidate's CV, producing an ATS score (0-100).
"""

import re
from collections import Counter

from app.agents.state import AnalyseState
from app.core.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Stopwords (French + English)
# ---------------------------------------------------------------------------

STOPWORDS: frozenset[str] = frozenset({
    # French
    "le", "la", "les", "de", "du", "des", "un", "une", "et", "en", "au",
    "aux", "par", "pour", "sur", "avec", "dans", "est", "sont", "être",
    "avoir", "vous", "nous", "ils", "elles", "que", "qui", "une", "ce",
    "se", "si", "ou", "mais", "donc", "or", "ni", "car", "à", "l", "d",
    # English
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "is", "are", "be", "have", "has", "will", "can", "do",
    "this", "that", "it", "as", "by", "from", "we", "you", "they", "our",
})


def extract_keywords(text: str, top_n: int = 40) -> list[str]:
    """
    Extracts the most relevant keywords from a text.

    - Lowercases and tokenizes
    - Removes stopwords and short tokens (< 3 chars)
    - Returns top N by frequency

    Args:
        text:  Input text to extract keywords from.
        top_n: Maximum number of keywords to return.

    Returns:
        List of keywords sorted by frequency (most common first).
    """
    # Tokenize: keep alphanumeric words and common tech terms (e.g. "C++", "Node.js")
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9+#._-]{2,}", text.lower())
    # Remove stopwords
    filtered = [t for t in tokens if t not in STOPWORDS and len(t) >= 3]
    # Count and return top N
    counter = Counter(filtered)
    return [word for word, _ in counter.most_common(top_n)]


def compute_ats_score(cv_keywords: list[str], job_keywords: list[str]) -> tuple[int, list[str], list[str]]:
    """
    Computes ATS compatibility score by comparing keyword sets.

    The ATS score measures what fraction of job offer keywords
    appear in the CV.

    Args:
        cv_keywords:  Keywords extracted from the CV.
        job_keywords: Keywords extracted from the job offer.

    Returns:
        Tuple of (score, keywords_found, keywords_missing):
        - score:           Integer 0-100
        - keywords_found:  Job keywords present in CV
        - keywords_missing: Job keywords absent from CV
    """
    if not job_keywords:
        return 0, [], []

    cv_set = set(cv_keywords)
    job_set = set(job_keywords)

    found = sorted(job_set & cv_set)
    missing = sorted(job_set - cv_set)

    score = int(round(len(found) / len(job_set) * 100))
    return min(score, 100), found, missing


def compute_ats_node(state: AnalyseState) -> dict:
    """
    LangGraph node: extracts keywords and computes the ATS score.

    Args:
        state: Pipeline state with cv_text and job_text.

    Returns:
        State updates: job/cv keywords, ATS score, found/missing keywords, SSE event.
    """
    cv_keywords = extract_keywords(state["cv_text"])
    job_keywords = extract_keywords(state["job_text"])

    score, found, missing = compute_ats_score(cv_keywords, job_keywords)

    progress_event = {
        "type": "progress",
        "step": "ats",
        "progress": 35,
        "data": {
            "score_ats": score,
            "keywords_found_count": len(found),
            "keywords_missing_count": len(missing),
        },
    }

    logger.info(
        "ATS node executed",
        extra={
            "score_ats": score,
            "found": len(found),
            "missing": len(missing),
        },
    )

    return {
        "job_keywords": job_keywords,
        "cv_keywords": cv_keywords,
        "score_ats": score,
        "keywords_found": found,
        "keywords_missing": missing[:15],  # Limit to top 15 missing keywords
        "stream_events": state.get("stream_events", []) + [progress_event],
    }
