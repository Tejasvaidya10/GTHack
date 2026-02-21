"""Semantic Scholar literature retrieval with feedback-boosted keywords."""

import logging
import time

import requests

from models.schemas import LiteratureResult, BoostedKeyword
from models.database import get_boosted_keywords
from app.config import SEMANTIC_SCHOLAR_API

logger = logging.getLogger(__name__)

# Common stop words to filter from relevance matching
STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "can", "this", "that", "these", "those",
    "it", "its", "not", "no", "as", "if", "than", "so", "very",
}


def _build_search_query(
    conditions: list[str],
    drugs: list[str],
    keywords: list[str],
    boosted: list[BoostedKeyword],
) -> str:
    """Build a search query string, incorporating boosted keywords."""
    parts = []

    # Add high-scoring boosted keywords first
    for bk in boosted:
        if bk.boost_score >= 0.6 and bk.keyword not in parts:
            parts.append(bk.keyword)

    parts.extend(conditions)
    parts.extend(drugs)
    parts.extend(keywords)

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for p in parts:
        p_lower = p.lower().strip()
        if p_lower and p_lower not in seen:
            seen.add(p_lower)
            unique.append(p)

    query = " ".join(unique[:8])  # Limit query length
    if not query:
        return ""

    # Add "treatment" if only conditions are provided
    if conditions and not drugs and "treatment" not in query.lower():
        query += " treatment"

    return query


def _generate_relevance_explanation(
    paper_title: str,
    paper_abstract: str,
    conditions: list[str],
    drugs: list[str],
) -> str:
    """Generate relevance explanation via simple string matching."""
    title_lower = paper_title.lower()
    abstract_lower = (paper_abstract or "").lower()
    combined = title_lower + " " + abstract_lower

    matched = []
    for condition in conditions:
        if condition.lower() in combined:
            matched.append(f"condition '{condition}'")
    for drug in drugs:
        if drug.lower() in combined:
            matched.append(f"medication '{drug}'")

    if matched:
        return f"Matches extracted {', '.join(matched)}"
    return "Related to visit topics based on search query"


def search_literature(
    conditions: list[str],
    drugs: list[str],
    keywords: list[str] = [],
) -> list[LiteratureResult]:
    """Search Semantic Scholar for relevant published research.

    Incorporates boosted keywords from feedback history to improve results.

    Args:
        conditions: List of medical conditions from the visit.
        drugs: List of medications from the visit.
        keywords: Additional search keywords.

    Returns:
        List of LiteratureResult objects sorted by influential citations.
    """
    # Get boosted keywords from feedback history
    try:
        boosted = get_boosted_keywords(min_score=0.5)
    except Exception:
        boosted = []

    query = _build_search_query(conditions, drugs, keywords, boosted)
    if not query:
        return []

    params = {
        "query": query,
        "limit": 10,
        "fields": "title,abstract,url,year,citationCount,influentialCitationCount,authors,journal",
    }

    for attempt in range(2):
        try:
            response = requests.get(
                SEMANTIC_SCHOLAR_API,
                params=params,
                timeout=15,
            )
            if response.status_code == 429:
                if attempt == 0:
                    logger.warning("Semantic Scholar rate limited, retrying in 1s...")
                    time.sleep(1)
                    continue
                else:
                    logger.warning("Semantic Scholar rate limited on retry, returning empty")
                    return []
            response.raise_for_status()
            data = response.json()
            break
        except requests.RequestException as e:
            logger.warning(f"Semantic Scholar API error: {e}")
            return []
    else:
        return []

    papers = data.get("data", [])
    results = []

    for paper in papers:
        paper_id = paper.get("paperId", "")
        title = paper.get("title", "")
        abstract = paper.get("abstract", "") or ""
        year = paper.get("year")
        citation_count = paper.get("citationCount", 0) or 0
        influential_count = paper.get("influentialCitationCount", 0) or 0

        # Extract authors
        authors = []
        for author in paper.get("authors", []) or []:
            name = author.get("name", "")
            if name:
                authors.append(name)

        # Journal
        journal_info = paper.get("journal")
        journal = journal_info.get("name", "") if isinstance(journal_info, dict) else None

        # URL
        url = paper.get("url", "")
        if not url and paper_id:
            url = f"https://www.semanticscholar.org/paper/{paper_id}"

        # Abstract snippet (first 200 chars)
        abstract_snippet = abstract[:200] + "..." if len(abstract) > 200 else abstract

        relevance = _generate_relevance_explanation(title, abstract, conditions, drugs)

        results.append(LiteratureResult(
            paper_id=paper_id,
            title=title,
            authors=authors[:5],  # Limit authors
            year=year,
            journal=journal,
            abstract_snippet=abstract_snippet,
            citation_count=citation_count,
            influential_citation_count=influential_count,
            url=url,
            relevance_explanation=relevance,
        ))

    # Sort by influential citation count (desc), then year (desc)
    results.sort(
        key=lambda r: (r.influential_citation_count, r.year or 0),
        reverse=True,
    )

    return results
