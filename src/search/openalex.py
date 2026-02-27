"""OpenAlex API search module."""

import time
import requests
from typing import Optional
from .base import BaseSearcher, PaperResult


class OpenAlexSearcher(BaseSearcher):
    """Search papers via OpenAlex API."""

    source_name = "openalex"
    BASE_URL = "https://api.openalex.org"

    # Known OpenAlex source IDs for construction journals
    # These can be looked up at https://api.openalex.org/sources?search=<journal_name>
    KNOWN_SOURCES = {
        "Automation in Construction": "S125754415",
        "Advanced Engineering Informatics": "S15332861",
        "Journal of Computing in Civil Engineering": "S110711780",
        "Building and Environment": "S42283751",
        "Journal of Construction Engineering and Management": "S188872164",
        "Engineering Structures": "S162162647",
    }

    def __init__(self, email: str = "yusenjiao@gmail.com"):
        """Initialize with a polite pool email for higher rate limits."""
        self.email = email
        self.session = requests.Session()
        self.session.headers["User-Agent"] = f"PaperAgent/1.0 (mailto:{email})"

    def search(self, keywords: list[str], venue_filter: list[str] = None,
               max_results: int = 20, year_from: int = None) -> list[PaperResult]:
        """Search OpenAlex for papers matching keywords."""
        # OpenAlex works best with short queries — use top 3 keywords max
        short_keywords = keywords[:3]
        query = " ".join(short_keywords)
        print(f"[OpenAlex] Searching: '{query}' (from {len(keywords)} keywords)")
        results = []

        # Build filter string
        filters = [f"default.search:{query}"]

        if year_from:
            filters.append(f"from_publication_date:{year_from}-01-01")

        # If venue filter maps to known source IDs, use precise filtering
        source_ids = []
        if venue_filter:
            for v in venue_filter:
                # Check exact match in known sources
                for journal_name, src_id in self.KNOWN_SOURCES.items():
                    if v.lower() in journal_name.lower() or journal_name.lower() in v.lower():
                        source_ids.append(src_id)
                        break

            if source_ids:
                source_filter = "|".join(source_ids)
                filters.append(f"primary_location.source.id:{source_filter}")

        filter_str = ",".join(filters)

        params = {
            "filter": filter_str,
            "per_page": min(max_results * 2, 50),
            "sort": "cited_by_count:desc",
            "mailto": self.email,
        }

        try:
            resp = self.session.get(f"{self.BASE_URL}/works", params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            print(f"[OpenAlex] API returned {len(data.get('results', []))} works")
        except requests.RequestException as e:
            print(f"[OpenAlex] Search error: {e}")
            return results

        works = data.get("results", [])

        for work in works:
            # Reconstruct abstract from inverted index
            abstract = self._reconstruct_abstract(work.get("abstract_inverted_index"))
            if not abstract:
                continue

            title = work.get("title", "")
            if not title:
                continue

            # Post-filter by venue name if no source IDs were found
            if venue_filter and not source_ids:
                source_name = ""
                primary_loc = work.get("primary_location") or {}
                source = primary_loc.get("source") or {}
                source_name = (source.get("display_name") or "").lower()
                if not any(v.lower() in source_name for v in venue_filter):
                    continue

            # Extract venue
            venue = ""
            primary_loc = work.get("primary_location") or {}
            source_info = primary_loc.get("source") or {}
            venue = source_info.get("display_name", "")

            # Extract authors
            authors = []
            for authorship in (work.get("authorships") or [])[:10]:
                author = authorship.get("author") or {}
                name = author.get("display_name")
                if name:
                    authors.append(name)

            # Build URL: prefer DOI, fallback to OpenAlex
            doi = work.get("doi") or ""
            url = doi if doi else (work.get("id") or "")

            # Extract year
            year = work.get("publication_year")

            results.append(PaperResult(
                title=title,
                abstract=abstract,
                authors=authors,
                venue=venue,
                year=year,
                citation_count=work.get("cited_by_count"),
                url=url,
                doi=doi.replace("https://doi.org/", "") if doi else None,
                source="openalex",
            ))

            if len(results) >= max_results:
                break

        time.sleep(0.5)
        return results

    @staticmethod
    def _reconstruct_abstract(inverted_index: Optional[dict]) -> str:
        """Reconstruct abstract from OpenAlex inverted index format."""
        if not inverted_index:
            return ""

        # inverted_index: {"word": [pos1, pos2], ...}
        word_positions = []
        for word, positions in inverted_index.items():
            for pos in positions:
                word_positions.append((pos, word))

        word_positions.sort(key=lambda x: x[0])
        return " ".join(word for _, word in word_positions)

    def lookup_source_id(self, journal_name: str) -> Optional[str]:
        """Look up an OpenAlex source ID by journal name. Useful for adding new journals."""
        try:
            resp = self.session.get(
                f"{self.BASE_URL}/sources",
                params={"search": journal_name, "per_page": 1, "mailto": self.email},
                timeout=15,
            )
            resp.raise_for_status()
            results = resp.json().get("results", [])
            if results:
                # Return just the ID part (e.g., "S125754415")
                full_id = results[0].get("id", "")
                return full_id.split("/")[-1] if "/" in full_id else full_id
        except requests.RequestException:
            pass
        return None
