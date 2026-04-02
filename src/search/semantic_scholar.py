"""Semantic Scholar API search module."""

import time
import requests
from typing import Optional
from .base import BaseSearcher, PaperResult


class SemanticScholarSearcher(BaseSearcher):
    """Search papers via Semantic Scholar API."""

    source_name = "semantic_scholar"
    BASE_URL = "https://api.semanticscholar.org/graph/v1"
    SEARCH_URL = f"{BASE_URL}/paper/search"

    FIELDS = "title,abstract,authors,venue,year,citationCount,externalIds,url"

    def __init__(self, api_key: Optional[str] = None):
        self.session = requests.Session()
        if api_key:
            self.session.headers["x-api-key"] = api_key

    def search(self, keywords: list[str], venue_filter: list[str] = None,
               max_results: int = 20, year_from: int = None) -> list[PaperResult]:
        """Search Semantic Scholar for papers matching keywords with pagination."""
        results = []

        # Build multiple query variants for better coverage
        queries = self._build_query_variants(keywords)

        seen_ids = set()
        for i, query in enumerate(queries):
            if len(results) >= max_results:
                break
            if i > 0:
                time.sleep(2)  # Delay between query variants
            page_results = self._search_single_query(
                query, venue_filter, max_results - len(results), year_from, seen_ids
            )
            results.extend(page_results)

        return results[:max_results]

    def _build_query_variants(self, keywords: list[str]) -> list[str]:
        """Build multiple query strings for broader coverage.
        Uses overlapping combinations to maximize recall while keeping precision."""
        variants = []
        # Full query (top 5 keywords)
        if len(keywords) >= 2:
            variants.append(" ".join(keywords[:5]))
        # Shorter focused query (top 3)
        if len(keywords) >= 3:
            variants.append(" ".join(keywords[:3]))
        # Middle segment
        if len(keywords) >= 6:
            variants.append(" ".join(keywords[2:5]))
        if not variants:
            variants.append(" ".join(keywords))
        # Deduplicate
        seen = set()
        unique = []
        for v in variants:
            if v not in seen:
                seen.add(v)
                unique.append(v)
        return unique

    def _search_single_query(self, query: str, venue_filter, max_results, year_from, seen_ids):
        """Search with pagination for a single query string."""
        print(f"[SemanticScholar] Searching: '{query}'")
        results = []
        offset = 0
        per_page = min(100, max(max_results * 2, 50))

        while len(results) < max_results:
            params = {
                "query": query,
                "limit": per_page,
                "offset": offset,
                "fields": self.FIELDS,
            }
            if year_from:
                params["year"] = f"{year_from}-"

            data = None
            for attempt in range(3):
                try:
                    resp = self.session.get(self.SEARCH_URL, params=params, timeout=30)
                    if resp.status_code == 429:
                        wait = (attempt + 1) * 5
                        print(f"[SemanticScholar] Rate limited (429), waiting {wait}s... (attempt {attempt+1}/3)")
                        time.sleep(wait)
                        continue
                    resp.raise_for_status()
                    data = resp.json()
                    break
                except requests.RequestException as e:
                    print(f"[SemanticScholar] Search error: {e}")
                    if attempt < 2:
                        time.sleep(5)
                        continue
                    return results

            if data is None:
                break

            papers = data.get("data", [])
            if not papers:
                break

            for paper in papers:
                paper_id = paper.get("paperId", "")
                if paper_id in seen_ids:
                    continue
                seen_ids.add(paper_id)

                if not paper.get("abstract"):
                    continue

                # Post-filter by venue if specified
                if venue_filter:
                    paper_venue = (paper.get("venue") or "").lower()
                    if not any(v.lower() in paper_venue for v in venue_filter):
                        continue

                doi = None
                external_ids = paper.get("externalIds") or {}
                if "DOI" in external_ids:
                    doi = external_ids["DOI"]

                paper_url = paper.get("url") or ""
                if not paper_url and paper_id:
                    paper_url = f"https://www.semanticscholar.org/paper/{paper_id}"

                authors = []
                for a in (paper.get("authors") or []):
                    if a.get("name"):
                        authors.append(a["name"])

                results.append(PaperResult(
                    title=paper.get("title", ""),
                    abstract=paper.get("abstract", ""),
                    authors=authors,
                    venue=paper.get("venue", ""),
                    year=paper.get("year"),
                    citation_count=paper.get("citationCount"),
                    url=paper_url,
                    doi=doi,
                    source="semantic_scholar",
                ))

                if len(results) >= max_results:
                    break

            # Stop paginating if we got fewer than requested (no more pages)
            total = data.get("total", 0)
            offset += per_page
            if offset >= total or len(papers) < per_page:
                break

            time.sleep(1.5)  # Rate limiting between pages

        time.sleep(1)
        return results
