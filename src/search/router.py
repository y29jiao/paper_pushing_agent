"""Router that selects and orchestrates search sources based on profile configuration."""

from typing import Optional
from .base import PaperResult
from .semantic_scholar import SemanticScholarSearcher
from .openreview import OpenReviewSearcher
from .openalex import OpenAlexSearcher


# Venues that exist on OpenReview
OPENREVIEW_VENUES = {"ICLR", "NeurIPS", "ICML", "ACL", "EMNLP", "CVPR", "KDD", "AAAI"}

# Venue groups that indicate journal-heavy (not conference) profiles
JOURNAL_VENUE_GROUPS = {"construction"}


class SearchRouter:
    """Routes search requests to appropriate sources based on profile type."""

    def __init__(self):
        self.semantic_scholar = SemanticScholarSearcher()
        self.openreview = OpenReviewSearcher()
        self.openalex = OpenAlexSearcher()

    def search(
        self,
        keywords: list[str],
        sources: list[str],
        venue_filter_name: str,
        venue_list: list[str],
        max_results: int = 20,
        year_from: Optional[int] = None,
    ) -> list[PaperResult]:
        """
        Search across multiple sources with smart priority ordering.

        Args:
            keywords: Search keywords from GPT parsing
            sources: List of source names enabled for this profile
            venue_filter_name: Name of the venue group (e.g., "top_ai", "construction")
            venue_list: Actual list of venue/journal names
            max_results: Maximum total results desired
            year_from: Only return papers from this year onward
        """
        all_results = []
        seen_titles = set()  # for dedup across sources

        # Determine source priority based on profile type
        ordered_sources = self._get_source_priority(sources, venue_filter_name)
        print(f"[Router] Source priority: {ordered_sources}")

        # Search ALL sources to maximize coverage, don't stop early
        for source_name in ordered_sources:
            print(f"[Router] Trying {source_name} (have {len(all_results)} so far)...")
            # Each source gets the full max_results budget
            fetch_count = max_results

            papers = self._search_source(
                source_name, keywords, venue_list, fetch_count, year_from
            )
            print(f"[Router] {source_name} returned {len(papers)} papers")

            # Deduplicate against already collected results
            for paper in papers:
                norm_title = paper.title.lower().strip()
                if norm_title not in seen_titles:
                    seen_titles.add(norm_title)
                    all_results.append(paper)

        print(f"[Router] Total unique papers: {len(all_results)}")
        return all_results[:max_results]

    def _get_source_priority(self, sources: list[str], venue_filter_name: str) -> list[str]:
        """
        Determine source search order based on profile type.

        - Journal-heavy profiles (construction): OpenAlex first (precise source filtering)
        - AI conference profiles: Semantic Scholar first, then OpenReview
        - Generic: Semantic Scholar first
        """
        if venue_filter_name in JOURNAL_VENUE_GROUPS:
            priority = ["openalex", "semantic_scholar", "openreview"]
        elif venue_filter_name == "top_ai":
            priority = ["semantic_scholar", "openreview", "openalex"]
        else:
            priority = ["semantic_scholar", "openalex", "openreview"]

        # Only include sources that are enabled for this profile
        return [s for s in priority if s in sources]

    def _search_source(
        self,
        source_name: str,
        keywords: list[str],
        venue_list: list[str],
        max_results: int,
        year_from: Optional[int],
    ) -> list[PaperResult]:
        """Execute search on a specific source."""
        try:
            if source_name == "semantic_scholar":
                return self.semantic_scholar.search(
                    keywords, venue_filter=venue_list,
                    max_results=max_results, year_from=year_from
                )
            elif source_name == "openreview":
                # Only pass AI conference venues to OpenReview
                or_venues = [v for v in venue_list if v.upper() in OPENREVIEW_VENUES]
                if not or_venues and venue_list:
                    # This profile's venues aren't on OpenReview, skip
                    return []
                return self.openreview.search(
                    keywords, venue_filter=or_venues or None,
                    max_results=max_results, year_from=year_from
                )
            elif source_name == "openalex":
                return self.openalex.search(
                    keywords, venue_filter=venue_list,
                    max_results=max_results, year_from=year_from
                )
        except Exception as e:
            print(f"[Router] Error searching {source_name}: {e}")

        return []
