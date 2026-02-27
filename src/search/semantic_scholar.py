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
        """Search Semantic Scholar for papers matching keywords."""
        query = " ".join(keywords)
        params = {
            "query": query,
            "limit": min(max_results * 3, 100),  # fetch extra for post-filtering
            "fields": self.FIELDS,
        }
        if year_from:
            params["year"] = f"{year_from}-"

        results = []
        try:
            resp = self.session.get(self.SEARCH_URL, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            print(f"[SemanticScholar] Search error: {e}")
            return results

        papers = data.get("data", [])

        for paper in papers:
            if not paper.get("abstract"):
                continue

            # Post-filter by venue if specified
            if venue_filter:
                paper_venue = (paper.get("venue") or "").lower()
                if not any(v.lower() in paper_venue for v in venue_filter):
                    # Also check against the paper title for conference proceedings
                    continue

            doi = None
            external_ids = paper.get("externalIds") or {}
            if "DOI" in external_ids:
                doi = external_ids["DOI"]

            paper_url = paper.get("url") or ""
            if not paper_url and paper.get("paperId"):
                paper_url = f"https://www.semanticscholar.org/paper/{paper['paperId']}"

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

        # Rate limiting: S2 allows 100 req/5min without key
        time.sleep(1)
        return results
