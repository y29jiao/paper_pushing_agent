"""
Paper Agent — Main orchestration script.

Modes:
  - Full mode (default): parse query with GPT, search, summarize, email + local file
  - Search-only mode (--search-only or no OPENAI_API_KEY): search only, output title + abstract summary to local file
  - Local-only: if no GMAIL credentials, skip email and just save local file

Usage:
  python -m src.main                           # run all active profiles
  python -m src.main --search-only             # skip GPT, output raw results
  python -m src.main --query "some query"      # one-off query
  python -m src.main --query "..." --count 50  # one-off with max count
"""

import os
import sys
import argparse
from datetime import datetime

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils import load_config, load_history, save_history, get_env_or_default, get_mdt_now
from src.search.router import SearchRouter
from src.search.base import PaperResult
from src.dedup import dedup_results, update_history


def save_results_markdown(profile_results: dict[str, list[dict]], output_dir: str = "output"):
    """Save search results to a markdown file for local review."""
    os.makedirs(output_dir, exist_ok=True)
    now = datetime.now()
    filename = f"papers_{now.strftime('%Y%m%d_%H%M%S')}.md"
    filepath = os.path.join(output_dir, filename)

    lines = []
    total = sum(len(papers) for papers in profile_results.values())
    lines.append(f"# Paper Agent Results — {now.strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"Total: {total} papers\n")

    for profile_name, papers in profile_results.items():
        lines.append(f"## {profile_name}")
        lines.append(f"Found {len(papers)} papers\n")

        if not papers:
            lines.append("_No papers found._\n")
            continue

        for i, paper in enumerate(papers, 1):
            title = paper.get("title", "Unknown")
            year = paper.get("year", "N/A")
            venue = paper.get("venue", "N/A")
            url = paper.get("url", "")
            citations = paper.get("citation_count", "N/A")
            source = paper.get("source", "")

            lines.append(f"### {i}. {title}")
            lines.append(f"**Year:** {year} | **Venue:** {venue} | **Citations:** {citations} | **Source:** {source}")
            if url:
                lines.append(f"**URL:** {url}")

            # Authors
            authors = paper.get("authors", [])
            if authors:
                author_str = ", ".join(authors[:5])
                if len(authors) > 5:
                    author_str += " et al."
                lines.append(f"**Authors:** {author_str}")

            # Abstract summary (first 2 sentences or relevance_reason + summary_zh if available)
            if paper.get("summary_zh"):
                lines.append(f"\n> **Summary:** {paper['summary_zh']}")
            if paper.get("relevance_reason"):
                lines.append(f"> **Relevance:** {paper['relevance_reason']}")

            # Short abstract (first ~300 chars)
            abstract = paper.get("abstract", "")
            if abstract:
                short = _truncate_to_sentences(abstract, max_sentences=2)
                lines.append(f"\n> {short}")

            lines.append("")  # blank line between papers

    content = "\n".join(lines)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"[Output] Saved to {filepath}")
    return filepath


def _truncate_to_sentences(text: str, max_sentences: int = 2) -> str:
    """Truncate text to first N sentences."""
    import re
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    result = " ".join(sentences[:max_sentences])
    if len(sentences) > max_sentences:
        result += "..."
    return result


def run(config_path="config.json", history_path="history.json", search_only=False,
        cli_query=None, cli_count=None):
    """Main execution flow."""
    # ── Load configuration ──
    config = load_config(config_path)
    history = load_history(history_path)

    # ── Environment variables ──
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    gmail_address = os.environ.get("GMAIL_ADDRESS")
    gmail_app_password = os.environ.get("GMAIL_APP_PASSWORD")
    gpt_model = os.environ.get("GPT_MODEL", "gpt-5.2")

    # Auto-detect search-only mode if no OpenAI key
    if not openai_api_key:
        if not search_only:
            print("[Info] No OPENAI_API_KEY — running in search-only mode")
        search_only = True

    has_email = bool(gmail_address and gmail_app_password)

    # ── Workflow dispatch overrides (GitHub Actions compat) ──
    trigger_query = cli_query or get_env_or_default("TRIGGER_QUERY")
    trigger_count = cli_count or get_env_or_default("TRIGGER_COUNT")
    trigger_profile = get_env_or_default("TRIGGER_PROFILE")

    target_count = int(trigger_count) if trigger_count else None

    # ── Initialize search router ──
    router = SearchRouter()

    # ── Determine which profiles to run ──
    profiles = config.get("profiles", [])
    venue_groups = config.get("venue_groups", {})

    if trigger_query:
        profiles_to_run = [{
            "id": "_oneoff",
            "name": f"Query: {trigger_query[:60]}",
            "query": trigger_query,
            "sources": ["semantic_scholar", "openalex"],
            "venue_filter": "any",
            "count": target_count,
            "active": True,
        }]
    elif trigger_profile:
        profiles_to_run = [p for p in profiles if p["id"] == trigger_profile and p.get("active", True)]
        if not profiles_to_run:
            print(f"[Error] Profile '{trigger_profile}' not found or not active")
            sys.exit(1)
    else:
        profiles_to_run = [p for p in profiles if p.get("active", True)]

    if not profiles_to_run:
        print("[Info] No active profiles to run")
        return

    # ── Process each profile ──
    profile_results: dict[str, list[dict]] = {}
    all_pushed_papers: list[PaperResult] = []

    for profile in profiles_to_run:
        profile_name = profile["name"]
        query = profile["query"]
        sources = profile.get("sources", ["semantic_scholar", "openalex"])
        venue_filter_name = profile.get("venue_filter", "any")
        venue_list = venue_groups.get(venue_filter_name, [])
        count = target_count or profile.get("count") or 50  # default to 50 if not specified

        print(f"\n{'='*60}")
        print(f"[Profile] {profile_name}")
        print(f"[Query] {query}")
        print(f"[Sources] {sources}")
        print(f"[Venues] {venue_filter_name} -> {venue_list}")
        print(f"[Count] {count}")

        # Step 1: Parse query
        if search_only:
            # In search-only mode, generate keywords directly from the query
            parsed = _simple_parse_query(query)
        else:
            from src.query_parser import parse_query
            from openai import OpenAI
            client = OpenAI(api_key=openai_api_key)
            print("[Step 1] Parsing query with GPT...")
            try:
                parsed = parse_query(query, client, model=gpt_model)
            except Exception as e:
                print(f"  [Error] Query parsing failed: {e}, falling back to simple parse")
                parsed = _simple_parse_query(query)

        print(f"  Keywords: {parsed['keywords_en']}")
        print(f"  Alt keywords: {parsed['keywords_alt']}")

        # Step 2: Search
        print("[Step 2] Searching papers...")
        search_max = count * 3  # fetch extra for filtering

        # Check if profile has explicit keyword groups
        keyword_groups = profile.get("search_keyword_groups")
        if keyword_groups:
            print(f"  Using {len(keyword_groups)} keyword groups from profile config")
            papers = []
            for i, kw_group in enumerate(keyword_groups):
                print(f"  [Group {i+1}/{len(keyword_groups)}] Keywords: {kw_group}")
                group_papers = router.search(
                    keywords=kw_group,
                    sources=sources,
                    venue_filter_name=venue_filter_name,
                    venue_list=venue_list,
                    max_results=search_max // len(keyword_groups) + 10,
                    year_from=parsed.get("year_from"),
                )
                papers.extend(group_papers)
                print(f"    Found {len(group_papers)} papers (total so far: {len(papers)})")
        else:
            papers = router.search(
                keywords=parsed["keywords_en"],
                sources=sources,
                venue_filter_name=venue_filter_name,
                venue_list=venue_list,
                max_results=search_max,
                year_from=parsed.get("year_from"),
            )
            print(f"  Found {len(papers)} papers with primary keywords")

            # Try alternative keywords if not enough
            if len(papers) < count:
                print("  Trying alternative keywords...")
                alt_papers = router.search(
                    keywords=parsed["keywords_alt"],
                    sources=sources,
                    venue_filter_name=venue_filter_name,
                    venue_list=venue_list,
                    max_results=search_max,
                    year_from=parsed.get("year_from"),
                )
                papers.extend(alt_papers)
                print(f"  Total after alt search: {len(papers)}")

        # Step 3: Deduplicate
        print("[Step 3] Deduplicating...")
        papers = dedup_results(papers, history)
        print(f"  After dedup: {len(papers)}")

        if not papers:
            print("  No new papers found for this profile")
            profile_results[profile_name] = []
            continue

        # Step 4: Filter/summarize
        if search_only:
            # Apply lightweight relevance filtering based on query keywords
            enriched = _relevance_filter(papers, query)
            print(f"  [Search-only] {len(enriched)} papers after relevance filtering")
        else:
            from src.summarizer import filter_and_summarize
            from openai import OpenAI
            client = OpenAI(api_key=openai_api_key)
            print("[Step 4] Filtering and summarizing with GPT...")
            try:
                enriched = filter_and_summarize(
                    papers=papers, user_query=query, client=client,
                    model=gpt_model, target_count=count,
                )
                print(f"  Selected {len(enriched)} papers")
            except Exception as e:
                print(f"  [Error] Summarization failed: {e}")
                enriched = [p.to_dict() for p in papers[:count]]

        profile_results[profile_name] = enriched

        for ep in enriched:
            all_pushed_papers.append(PaperResult(
                title=ep["title"],
                abstract=ep.get("abstract", ""),
                doi=ep.get("doi"),
                url=ep.get("url", ""),
                source=ep.get("source", ""),
                venue=ep.get("venue", ""),
                year=ep.get("year"),
            ))

    # ── Save to local file (always) ──
    total_papers = sum(len(papers) for papers in profile_results.values())
    if total_papers == 0:
        print("\n[Info] No papers found.")
        return

    print(f"\n[Step 5] Saving results locally ({total_papers} papers total)...")
    output_path = save_results_markdown(profile_results)

    # ── Send email (optional) ──
    if has_email and not search_only:
        from src.email_sender import build_email_html, send_email
        now = get_mdt_now()
        push_time = now.strftime("%Y年%m月%d日 %A %H:%M (MDT)")
        html = build_email_html(profile_results, push_time)
        subject = f"Paper Agent — {now.strftime('%m/%d')} | {total_papers} papers"

        print("[Step 6] Sending email...")
        try:
            send_email(
                to_email=config["global"]["email"],
                subject=subject,
                html_content=html,
                gmail_address=gmail_address,
                gmail_app_password=gmail_app_password,
            )
            print("[Done] Email sent!")
        except Exception as e:
            print(f"[Warning] Email send failed: {e} (results saved locally)")
    else:
        if not has_email:
            print("[Info] No GMAIL credentials — skipping email (results saved locally)")

    # ── Update history ──
    print("[Step 7] Updating history...")
    now = get_mdt_now()
    history = update_history(history, all_pushed_papers, now.isoformat())
    save_history(history, history_path)
    print(f"[Done] History updated. Total tracked: {len(history['pushed_papers'])}")


def _relevance_filter(papers: list, query: str) -> list[dict]:
    """
    Lightweight relevance scoring without GPT.
    Scores each paper based on how many query-relevant terms appear in title + abstract.
    Filters out papers with very low relevance.
    """
    import re
    query_lower = query.lower()

    # Extract meaningful terms from query
    STOPWORDS = {
        "a", "an", "the", "of", "in", "on", "at", "to", "for", "and", "or",
        "is", "are", "was", "were", "be", "with", "by", "from", "as", "that",
        "this", "not", "but", "can", "has", "have", "how", "what", "which",
    }

    # Weighted terms: (term, weight) — compound/specific terms score higher
    weighted_terms = []

    # High-weight terms: domain-specific compound phrases
    high_weight = []
    if any(t in query_lower for t in ["building code", "regulation", "compliance", "法规"]):
        high_weight.extend(["building code", "code checking", "rule checking",
                          "compliance checking", "code compliance",
                          "automated compliance", "regulatory compliance",
                          "building regulation"])
    if any(t in query_lower for t in ["chatbot", "agent", "对话"]):
        high_weight.extend(["chatbot", "question answering", "conversational ai",
                          "large language model", "natural language processing"])
    if any(t in query_lower for t in ["comparison", "对比"]):
        high_weight.extend(["comparison", "comparing"])

    for term in high_weight:
        weighted_terms.append((term, 3))

    # Medium-weight: moderately specific single terms
    medium_weight = ["compliance", "regulation", "nlp", "llm", "bim",
                     "automated", "rule", "checking"]
    for term in medium_weight:
        weighted_terms.append((term, 2))

    # Low-weight: generic terms (match broadly, less signal)
    low_weight = ["construction", "building", "civil", "agent", "engineering",
                  "architecture", "aec"]
    for term in low_weight:
        weighted_terms.append((term, 1))

    scored_papers = []
    for paper in papers:
        title_lower = paper.title.lower()
        text = (title_lower + " " + paper.abstract.lower())
        score = 0
        for term, weight in weighted_terms:
            if term in text:
                score += weight
                # Bonus for terms in title
                if term in title_lower:
                    score += weight

        scored_papers.append((score, paper))

    # Sort by score descending
    scored_papers.sort(key=lambda x: x[0], reverse=True)

    # Filter: keep papers with score >= threshold
    min_score = 10
    filtered = [p.to_dict() for score, p in scored_papers if score >= min_score]

    if len(filtered) < 10:
        # If filtering is too strict, return top papers by score
        filtered = [p.to_dict() for _, p in scored_papers[:max(20, len(filtered))]]

    return filtered


def _simple_parse_query(query: str) -> dict:
    """
    Simple keyword extraction without GPT.
    Builds effective academic search queries from natural language input.
    """
    import re
    query_lower = query.lower()

    STOPWORDS = {
        "a", "an", "the", "of", "in", "on", "at", "to", "for", "and", "or",
        "is", "are", "was", "were", "be", "been", "with", "by", "from", "as",
        "that", "this", "it", "its", "not", "but", "can", "has", "have", "had",
        "do", "does", "did", "will", "would", "could", "should", "may", "might",
        "about", "into", "than", "then", "also", "very", "just", "how", "what",
        "which", "who", "whom", "where", "when", "why", "some", "any", "all",
        "我", "的", "了", "在", "是", "有", "和", "与", "或者", "帮我", "找",
        "好的", "论文", "相关", "方面",
    }

    keywords = []
    alt_keywords = []

    # Extract meaningful English words (skip stopwords)
    english_words = re.findall(r'[a-zA-Z][a-zA-Z\-]{2,}', query)
    for w in english_words:
        if w.lower() not in STOPWORDS and w.lower() not in [k.lower() for k in keywords]:
            keywords.append(w)

    # Domain-specific keyword expansion
    domain_maps = {
        "civil": ["civil engineering", "construction"],
        "建筑": ["civil engineering", "construction", "building"],
        "法规": ["building code", "regulation", "compliance checking"],
        "对比": ["comparison", "compliance checking", "automated checking"],
        "chatbot": ["chatbot", "conversational AI", "question answering"],
        "agent": ["AI agent", "LLM agent", "intelligent agent"],
        "graphrag": ["GraphRAG", "graph retrieval augmented generation"],
        "rag": ["retrieval augmented generation", "RAG"],
        "nlp": ["natural language processing", "NLP"],
        "llm": ["large language model", "LLM"],
        "regulation": ["building code", "regulatory compliance", "code compliance"],
        "building code": ["building regulation", "construction standard", "code checking"],
        "compliance": ["automated compliance checking", "rule checking"],
    }

    for trigger, expansions in domain_maps.items():
        if trigger in query_lower:
            for kw in expansions:
                if kw.lower() not in [k.lower() for k in keywords]:
                    keywords.append(kw)

    # Build alt keywords as broader variants
    alt_keywords = [
        kw for kw in keywords[len(keywords)//2:]
    ]
    # Add broader terms
    broad_terms = ["NLP", "artificial intelligence", "deep learning", "automation"]
    for t in broad_terms:
        if t.lower() not in [k.lower() for k in alt_keywords]:
            alt_keywords.append(t)

    return {
        "keywords_en": keywords[:12],
        "keywords_alt": alt_keywords[:10],
        "focus": "any",
        "time_range": "any",
        "year_from": None,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Paper Agent — Academic paper search")
    parser.add_argument("--search-only", action="store_true",
                        help="Skip GPT parsing/summarization, output raw search results")
    parser.add_argument("--query", type=str, default=None,
                        help="One-off search query (overrides config profiles)")
    parser.add_argument("--count", type=str, default=None,
                        help="Max number of papers to find")
    parser.add_argument("--config", type=str, default="config.json",
                        help="Path to config file")

    args = parser.parse_args()
    run(
        config_path=args.config,
        search_only=args.search_only,
        cli_query=args.query,
        cli_count=args.count,
    )
