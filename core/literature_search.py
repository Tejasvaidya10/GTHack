"""Literature retrieval from Semantic Scholar + PubMed with feedback-boosted keywords."""

import logging
import time

import requests

from models.schemas import LiteratureResult, BoostedKeyword
from models.database import get_boosted_keywords
from core.pubmed_search import search_pubmed
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
    """Search PubMed (primary) + Semantic Scholar for relevant published research.

    PubMed is searched first as the gold standard for medical literature.
    Semantic Scholar supplements with broader coverage and citation metrics.
    Results are merged, deduplicated, and sorted with PubMed results
    prioritized over Semantic Scholar at equal citation counts.

    Args:
        conditions: List of medical conditions from the visit.
        drugs: List of medications from the visit.
        keywords: Additional search keywords.

    Returns:
        List of LiteratureResult objects sorted by citation count.
    """
    all_results = []

    # --- Source 1: PubMed (gold standard for medical literature) ---
    try:
        pubmed_results = search_pubmed(conditions, drugs, keywords, max_results=15)
        all_results.extend(pubmed_results)
        logger.info(f"PubMed returned {len(pubmed_results)} results")
    except Exception as e:
        logger.warning(f"PubMed search failed: {e}")

    # --- Source 2: Semantic Scholar (broader + citation metrics) ---
    # Get boosted keywords from feedback history
    try:
        boosted = get_boosted_keywords(min_score=0.5)
    except Exception:
        boosted = []

    query = _build_search_query(conditions, drugs, keywords, boosted)
    if not query:
        # If no query but we have PubMed results, return those
        if all_results:
            all_results.sort(key=lambda r: (r.citation_count, r.year or 0), reverse=True)
            return all_results
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
                    logger.warning("Semantic Scholar rate limited on retry, skipping")
                    data = {"data": []}
                    break
            response.raise_for_status()
            data = response.json()
            break
        except requests.RequestException as e:
            logger.warning(f"Semantic Scholar API error: {e}")
            data = {"data": []}
            break
    else:
        data = {"data": []}

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

    # Add Semantic Scholar results with [Semantic Scholar] tag
    for r in results:
        r.relevance_explanation = f"[Semantic Scholar] {r.relevance_explanation}"
    all_results.extend(results)
    logger.info(f"Semantic Scholar returned {len(results)} results")

    # Deduplicate by title similarity — PubMed results come first in all_results
    # so they win ties (first occurrence kept)
    seen_titles = set()
    deduped = []
    for r in all_results:
        title_key = r.title.lower().strip().rstrip(".")
        if title_key not in seen_titles:
            seen_titles.add(title_key)
            deduped.append(r)

    # Sort: citation count (desc), PubMed first at equal counts, then year (desc)
    def _sort_key(r):
        is_pubmed = 1 if r.relevance_explanation.startswith("[PubMed]") else 0
        return (r.citation_count, is_pubmed, r.year or 0)

    deduped.sort(key=_sort_key, reverse=True)

    return deduped[:15]  # Return top 15 across both sources
