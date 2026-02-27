"""Base class for paper search sources."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PaperResult:
    """Unified paper result from any search source."""
    title: str
    abstract: str
    authors: list[str] = field(default_factory=list)
    venue: str = ""
    year: Optional[int] = None
    citation_count: Optional[int] = None
    url: str = ""
    doi: Optional[str] = None
    source: str = ""  # which search engine found it
    score: Optional[float] = None  # review score if available (OpenReview)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "abstract": self.abstract,
            "authors": self.authors,
            "venue": self.venue,
            "year": self.year,
            "citation_count": self.citation_count,
            "url": self.url,
            "doi": self.doi,
            "source": self.source,
            "score": self.score,
        }


class BaseSearcher:
    """Base class for paper search sources."""

    source_name: str = "base"

    def search(self, keywords: list[str], venue_filter: list[str] = None,
               max_results: int = 20, year_from: int = None) -> list[PaperResult]:
        """Search for papers. Override in subclasses."""
        raise NotImplementedError
