"""
LangGraph analysis state definition.

AnalyseState is the shared mutable state that flows through all agent nodes.
Each node reads from it, performs work, and returns updates to merge back.
"""

from typing import Any, TypedDict


class AnalyseState(TypedDict):
    """
    Shared state for the CV analysis LangGraph pipeline.

    Fields are populated progressively as the graph executes.
    Each node only updates the fields it is responsible for.
    """

    # -------------------------------------------------------------------------
    # Input (set before graph execution)
    # -------------------------------------------------------------------------

    analyse_id: str | None
    """
    Id of the Analyse row this run writes to. Used to retrieve the analyse in
    the database from within a node.

    Kept as str and not UUID: nodes may copy it into stream_events, which the
    router serialises with json.dumps — a UUID would raise there.
    """

    cv_text: str
    """Raw text extracted from the candidate's CV."""

    job_text: str
    """Raw job offer description text."""

    provider: str
    """AI provider name (e.g. 'openai', 'anthropic')."""

    model: str
    """AI model name (e.g. 'gpt-4o', 'claude-3-5-sonnet')."""

    api_key: str
    """Decrypted API key for the provider."""

    language: str
    """Analysis language: 'fr' or 'en'."""

    recommendation_detail: str
    """Level of detail: 'concise' or 'detailed'."""

    # -------------------------------------------------------------------------
    # Intermediate results (populated by agent nodes)
    # -------------------------------------------------------------------------
    job_keywords: list[str]
    """Keywords extracted from the job offer — used by the ATS node."""

    cv_keywords: list[str]
    """Keywords extracted from the CV — used by the ATS node."""

    score_ats: int
    """ATS compatibility score (0-100)."""

    score_competences: int
    """Technical skills matching score (0-100)."""

    score_experience: int
    """Experience relevance score (0-100)."""

    score_global: int
    """Weighted overall matching score (0-100)."""

    keywords_found: list[str]
    """Job offer keywords that appear in the CV."""

    keywords_missing: list[str]
    """Job offer keywords that are absent from the CV."""

    recommandations: list[dict[str, Any]]
    """
    List of AI-generated recommendations.
    Each item: { "type": "warning|success|info", "title": str, "description": str }
    """

    # -------------------------------------------------------------------------
    # Streaming events (accumulated during execution)
    # -------------------------------------------------------------------------
    stream_events: list[dict[str, Any]]
    """
    SSE events emitted during graph execution.
    Consumed by the streaming service to send to the client.
    Each event: { "type": "progress", "step": str, "progress": int, "data": dict }
    """

    # -------------------------------------------------------------------------
    # Error tracking
    # -------------------------------------------------------------------------
    error: str | None
    """Non-None if a node encountered a recoverable error."""
