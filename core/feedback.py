"""Clinician feedback loop logic."""

import logging
import re

from models.schemas import FeedbackItem, FeedbackAnalytics, BoostedKeyword
from models.database import (
    save_feedback as db_save_feedback,
    get_feedback as db_get_feedback,
    get_feedback_analytics as db_get_feedback_analytics,
    get_boosted_keywords as db_get_boosted_keywords,
    update_keyword_boost,
)

logger = logging.getLogger(__name__)

# Stop words to filter out when extracting keywords from paper titles
STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "this", "that", "it", "its", "as", "if", "not", "no", "so", "than",
    "we", "our", "their", "study", "review", "analysis", "using", "based",
    "new", "novel", "case", "report", "systematic", "meta",
}


def _extract_keywords_from_title(title: str) -> list[str]:
    """Extract meaningful keywords from a paper or item title."""
    words = re.findall(r"[a-zA-Z]+", title.lower())
    keywords = [w for w in words if w not in STOP_WORDS and len(w) >= 3]
    return keywords


def submit_feedback(feedback: FeedbackItem) -> int:
    """Submit clinician feedback and update keyword boost if applicable.

    Args:
        feedback: The feedback item to save.

    Returns:
        The feedback ID.
    """
    feedback_id = db_save_feedback(feedback)

    # Update keyword boost for literature relevance feedback
    if feedback.feedback_type == "literature_relevance":
        keywords = _extract_keywords_from_title(feedback.item_value)
        if keywords:
            positive = feedback.rating == "relevant"
            update_keyword_boost(keywords, positive)
            logger.info(
                f"Updated keyword boost for {len(keywords)} keywords "
                f"(positive={positive}): {keywords[:5]}"
            )

    return feedback_id


def get_feedback_for_visit(visit_id: int) -> list[FeedbackItem]:
    """Get all feedback entries for a specific visit."""
    return db_get_feedback(visit_id)


def get_feedback_analytics() -> FeedbackAnalytics:
    """Get aggregated feedback analytics."""
    return db_get_feedback_analytics()


def get_boosted_keywords() -> list[BoostedKeyword]:
    """Get keywords with positive feedback boost scores."""
    return db_get_boosted_keywords(min_score=0.0)
