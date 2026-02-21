"""PubMed literature search via NCBI E-utilities.

Free API, no key required (rate limited to 3 requests/second without key).
https://www.ncbi.nlm.nih.gov/books/NBK25497/
"""

import logging
import time
import xml.etree.ElementTree as ET

import requests

from models.schemas import LiteratureResult

logger = logging.getLogger(__name__)

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
ESUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
PUBMED_BASE_URL = "https://pubmed.ncbi.nlm.nih.gov"


def _build_query(conditions: list[str], drugs: list[str], keywords: list[str]) -> str:
    """Build a PubMed search query string."""
    parts = []
    for c in conditions:
        parts.append(f'"{c}"')
    for d in drugs:
        parts.append(f'"{d}"')
    for k in keywords:
        parts.append(k)

    query = " AND ".join(parts[:4]) if parts else ""
    if not query:
        return ""

    # Add filters for clinical relevance and recency
    query += " AND (clinical trial[pt] OR review[pt] OR meta-analysis[pt])"
    return query


def search_pubmed(
    conditions: list[str],
    drugs: list[str],
    keywords: list[str] = [],
    max_results: int = 10,
) -> list[LiteratureResult]:
    """Search PubMed for relevant medical literature.

    Prioritizes clinical trials, reviews, and meta-analyses.
    Sorted by relevance (PubMed's default ranking considers citation impact).

    Args:
        conditions: Medical conditions from the visit.
        drugs: Medications from the visit.
        keywords: Additional search terms.
        max_results: Maximum number of papers to return.

    Returns:
        List of LiteratureResult objects from PubMed.
    """
    query = _build_query(conditions, drugs, keywords)
    if not query:
        return []

    # Step 1: Search for PMIDs
    try:
        search_resp = requests.get(ESEARCH_URL, params={
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "sort": "relevance",
            "retmode": "json",
        }, timeout=10)
        search_resp.raise_for_status()
        search_data = search_resp.json()
    except requests.RequestException as e:
        logger.warning(f"PubMed search failed: {e}")
        return []

    pmids = search_data.get("esearchresult", {}).get("idlist", [])
    if not pmids:
        return []

    # Brief pause to respect rate limit (3 req/sec without API key)
    time.sleep(0.35)

    # Step 2: Fetch paper details
    try:
        summary_resp = requests.get(ESUMMARY_URL, params={
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "json",
        }, timeout=10)
        summary_resp.raise_for_status()
        summary_data = summary_resp.json()
    except requests.RequestException as e:
        logger.warning(f"PubMed summary fetch failed: {e}")
        return []

    # Step 2b: Get citation counts from PubMed Central cited-by links
    citation_counts = _fetch_citation_counts(pmids)

    results = []
    articles = summary_data.get("result", {})

    for pmid in pmids:
        article = articles.get(pmid)
        if not article or isinstance(article, str):
            continue

        title = article.get("title", "")
        # Extract authors
        authors = []
        for author in article.get("authors", []):
            name = author.get("name", "")
            if name:
                authors.append(name)

        # Publication info
        source = article.get("source", "")  # Journal name
        pub_date = article.get("pubdate", "")
        year = None
        if pub_date:
            try:
                year = int(pub_date.split()[0])
            except (ValueError, IndexError):
                pass

        # Get citation count from our lookup, fall back to pmcrefcount
        pmc_citations = citation_counts.get(pmid, 0)
        if pmc_citations == 0:
            pmc_citations = article.get("pmcrefcount", 0)
            if isinstance(pmc_citations, str):
                try:
                    pmc_citations = int(pmc_citations)
                except ValueError:
                    pmc_citations = 0

        # Build URL
        url = f"{PUBMED_BASE_URL}/{pmid}/"

        # Relevance explanation
        relevance = _generate_relevance(title, conditions, drugs)

        results.append(LiteratureResult(
            paper_id=f"pmid:{pmid}",
            title=title,
            authors=authors[:5],
            year=year,
            journal=source,
            abstract_snippet="",  # Would need separate efetch call for abstracts
            citation_count=pmc_citations,
            influential_citation_count=pmc_citations,
            url=url,
            relevance_explanation=f"[PubMed] {relevance}",
        ))

    # Sort by citation count descending, then year descending
    results.sort(key=lambda r: (r.citation_count, r.year or 0), reverse=True)

    return results


ELINK_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi"


def _fetch_citation_counts(pmids: list[str]) -> dict[str, int]:
    """Fetch 'cited by' counts for a list of PMIDs using elink.

    Uses PubMed Central's cited-by database to get how many papers cite each PMID.
    """
    if not pmids:
        return {}

    try:
        time.sleep(0.35)
        resp = requests.get(ELINK_URL, params={
            "dbfrom": "pubmed",
            "db": "pubmed",
            "id": ",".join(pmids),
            "cmd": "neighbor_count",
            "linkname": "pubmed_pubmed_citedin",
            "retmode": "json",
        }, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.warning(f"PubMed citation count fetch failed: {e}")
        return {}

    counts = {}
    linksets = data.get("linksets", [])
    for linkset in linksets:
        pmid = str(linkset.get("ids", [None])[0])
        for link_group in linkset.get("linksetdbs", []):
            if link_group.get("linkname") == "pubmed_pubmed_citedin":
                counts[pmid] = link_group.get("info", "0")
                # info is sometimes a count string
                try:
                    counts[pmid] = int(counts[pmid])
                except (ValueError, TypeError):
                    counts[pmid] = len(link_group.get("links", []))
    return counts


def _generate_relevance(title: str, conditions: list[str], drugs: list[str]) -> str:
    """Generate relevance explanation via string matching."""
    title_lower = title.lower()
    matched = []
    for c in conditions:
        if c.lower() in title_lower:
            matched.append(f"condition '{c}'")
    for d in drugs:
        if d.lower() in title_lower:
            matched.append(f"medication '{d}'")
    if matched:
        return f"Matches {', '.join(matched)}"
    return "Related to visit conditions"
