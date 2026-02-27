"""OpenReview API search module."""

import time
import requests
from typing import Optional
from .base import BaseSearcher, PaperResult


class OpenReviewSearcher(BaseSearcher):
    """Search papers via OpenReview API v2."""

    source_name = "openreview"
    BASE_URL = "https://api2.openreview.net"

    # Mapping of short venue names to OpenReview venue IDs
    VENUE_MAP = {
        "ICLR": "ICLR.cc",
        "NeurIPS": "NeurIPS.cc",
        "ICML": "ICML.cc",
        "ACL": "aclweb.org/ACL",
        "EMNLP": "aclweb.org/EMNLP",
        "CVPR": "thecvf.com/CVPR",
        "KDD": "KDD.org",
        "AAAI": "AAAI.org",
    }

    def search(self, keywords: list[str], venue_filter: list[str] = None,
               max_results: int = 20, year_from: int = None) -> list[PaperResult]:
        """Search OpenReview for papers matching keywords."""
        query = " ".join(keywords)
        results = []

        # Determine which venues to search
        venues_to_search = []
        if venue_filter:
            for v in venue_filter:
                v_upper = v.upper().strip()
                for short_name, or_id in self.VENUE_MAP.items():
                    if short_name.upper() == v_upper or v_upper in or_id.upper():
                        venues_to_search.append((short_name, or_id))
                        break
        else:
            # Search all mapped venues
            venues_to_search = list(self.VENUE_MAP.items())

        for short_name, venue_id in venues_to_search:
            try:
                params = {
                    "term": query,
                    "limit": min(max_results, 50),
                    "content": "all",
                }

                # Search notes endpoint
                resp = requests.get(
                    f"{self.BASE_URL}/notes/search",
                    params=params,
                    timeout=30,
                )

                if resp.status_code != 200:
                    # Fallback: try the notes endpoint with different params
                    params2 = {
                        "term": query,
                        "source": "forum",
                        "limit": min(max_results, 50),
                    }
                    resp = requests.get(
                        f"{self.BASE_URL}/notes/search",
                        params=params2,
                        timeout=30,
                    )
                    if resp.status_code != 200:
                        print(f"[OpenReview] Search failed for {short_name}: {resp.status_code}")
                        continue

                data = resp.json()
                notes = data.get("notes", [])

                for note in notes:
                    content = note.get("content", {})

                    title = content.get("title", {})
                    if isinstance(title, dict):
                        title = title.get("value", "")

                    abstract = content.get("abstract", {})
                    if isinstance(abstract, dict):
                        abstract = abstract.get("value", "")

                    if not title or not abstract:
                        continue

                    # Check if this note belongs to a relevant venue
                    invitation = note.get("invitation", "") or ""
                    note_venue = content.get("venue", {})
                    if isinstance(note_venue, dict):
                        note_venue = note_venue.get("value", "")

                    # Filter by venue if we have specific venues
                    if venue_filter:
                        venue_match = any(
                            vid.lower() in invitation.lower() or
                            vid.lower() in str(note_venue).lower()
                            for _, vid in venues_to_search
                        )
                        if not venue_match:
                            continue

                    # Extract authors
                    authors_data = content.get("authors", {})
                    if isinstance(authors_data, dict):
                        authors = authors_data.get("value", [])
                    elif isinstance(authors_data, list):
                        authors = authors_data
                    else:
                        authors = []

                    # Extract rating/score if available
                    score = None
                    rating = content.get("rating", {})
                    if isinstance(rating, dict):
                        try:
                            score = float(rating.get("value", 0))
                        except (ValueError, TypeError):
                            pass

                    # Build URL
                    forum_id = note.get("forum") or note.get("id", "")
                    url = f"https://openreview.net/forum?id={forum_id}" if forum_id else ""

                    # Determine display venue
                    display_venue = str(note_venue) if note_venue else short_name

                    results.append(PaperResult(
                        title=title,
                        abstract=abstract,
                        authors=authors if isinstance(authors, list) else [],
                        venue=display_venue,
                        year=_extract_year(note),
                        url=url,
                        source="openreview",
                        score=score,
                    ))

                time.sleep(0.5)  # Rate limiting between venue searches

            except requests.RequestException as e:
                print(f"[OpenReview] Error searching {short_name}: {e}")
                continue

            if len(results) >= max_results:
                break

        return results[:max_results]


def _extract_year(note: dict) -> Optional[int]:
    """Extract year from an OpenReview note."""
    # Try cdate (creation date) in milliseconds
    cdate = note.get("cdate")
    if cdate and isinstance(cdate, (int, float)):
        from datetime import datetime
        try:
            dt = datetime.fromtimestamp(cdate / 1000)
            return dt.year
        except (ValueError, OSError):
            pass

    # Try from invitation string (often contains year)
    invitation = note.get("invitation", "")
    import re
    year_match = re.search(r"20[12]\d", invitation)
    if year_match:
        return int(year_match.group())

    return None
