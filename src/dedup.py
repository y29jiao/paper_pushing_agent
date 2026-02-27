"""Deduplication logic for papers across sources and against history."""

from src.search.base import PaperResult
from src.utils import title_hash


def dedup_results(papers: list[PaperResult], history: dict) -> list[PaperResult]:
    """
    Remove duplicates from search results.

    1. Cross-source dedup (same paper found by multiple sources)
    2. History dedup (papers already pushed before)

    When deduping across sources, prefer:
    OpenReview URL > DOI URL > Semantic Scholar URL
    """
    # Build set of previously pushed title hashes
    pushed_hashes = {p["title_hash"] for p in history.get("pushed_papers", [])}
    pushed_dois = {p.get("doi") for p in history.get("pushed_papers", []) if p.get("doi")}

    # Source priority for URL selection
    source_priority = {"openreview": 0, "openalex": 1, "semantic_scholar": 2}

    # Group by normalized title
    title_groups: dict[str, list[PaperResult]] = {}
    for paper in papers:
        th = title_hash(paper.title)
        if th not in title_groups:
            title_groups[th] = []
        title_groups[th].append(paper)

    deduped = []
    for th, group in title_groups.items():
        # Skip if already pushed
        if th in pushed_hashes:
            continue

        # Check DOI-based dedup
        paper_doi = None
        for p in group:
            if p.doi:
                paper_doi = p.doi
                break
        if paper_doi and paper_doi in pushed_dois:
            continue

        # Pick the best version:
        # - Prefer the one with the best source priority for URL
        # - Merge metadata (take the most complete fields)
        group.sort(key=lambda p: source_priority.get(p.source, 99))
        best = group[0]

        # Merge: fill in missing fields from other sources
        for other in group[1:]:
            if not best.abstract and other.abstract:
                best.abstract = other.abstract
            if not best.doi and other.doi:
                best.doi = other.doi
            if best.citation_count is None and other.citation_count is not None:
                best.citation_count = other.citation_count
            if not best.venue and other.venue:
                best.venue = other.venue
            if not best.authors and other.authors:
                best.authors = other.authors
            if best.score is None and other.score is not None:
                best.score = other.score

        deduped.append(best)

    return deduped


def update_history(history: dict, papers: list[PaperResult], push_time: str) -> dict:
    """Add pushed papers to history."""
    for paper in papers:
        entry = {
            "title_hash": title_hash(paper.title),
            "title": paper.title[:100],  # truncate for storage
            "doi": paper.doi,
            "pushed_at": push_time,
        }
        history["pushed_papers"].append(entry)

    history["last_push"] = push_time

    # Keep history manageable: only last 500 entries
    if len(history["pushed_papers"]) > 500:
        history["pushed_papers"] = history["pushed_papers"][-500:]

    return history
