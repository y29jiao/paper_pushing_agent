"""
Paper Agent — Main orchestration script.

This script:
1. Reads config and determines which profiles to run
2. For each active profile, parses the query, searches, deduplicates, and summarizes
3. Builds an HTML email with all results
4. Sends via Gmail SMTP
5. Updates history.json
"""

import os
import sys
from datetime import datetime

from openai import OpenAI

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils import load_config, load_history, save_history, get_env_or_default, get_mdt_now
from src.query_parser import parse_query
from src.search.router import SearchRouter
from src.search.base import PaperResult
from src.dedup import dedup_results, update_history
from src.summarizer import filter_and_summarize
from src.email_sender import build_email_html, send_email


def run(config_path="config.json", history_path="history.json"):
    """Main execution flow."""
    # ── Load configuration ──
    config = load_config(config_path)
    history = load_history(history_path)

    # ── Environment variables ──
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    gmail_address = os.environ.get("GMAIL_ADDRESS")
    gmail_app_password = os.environ.get("GMAIL_APP_PASSWORD")
    gpt_model = os.environ.get("GPT_MODEL", "gpt-5.2")

    if not openai_api_key:
        print("[Error] OPENAI_API_KEY not set")
        sys.exit(1)
    if not gmail_address or not gmail_app_password:
        print("[Error] GMAIL_ADDRESS or GMAIL_APP_PASSWORD not set")
        sys.exit(1)

    # ── Workflow dispatch overrides ──
    trigger_query = get_env_or_default("TRIGGER_QUERY")
    trigger_count = get_env_or_default("TRIGGER_COUNT")
    trigger_profile = get_env_or_default("TRIGGER_PROFILE")

    target_count = int(trigger_count) if trigger_count else None

    # ── Initialize clients ──
    client = OpenAI(api_key=openai_api_key)
    router = SearchRouter()

    # ── Determine which profiles to run ──
    profiles = config.get("profiles", [])
    venue_groups = config.get("venue_groups", {})

    if trigger_query:
        # One-off query: create a temporary profile
        profiles_to_run = [{
            "id": "_oneoff",
            "name": f"临时查询: {trigger_query[:40]}",
            "query": trigger_query,
            "sources": ["semantic_scholar", "openreview", "openalex"],
            "venue_filter": "any",
            "count": target_count,
            "active": True,
        }]
    elif trigger_profile:
        # Run specific profile
        profiles_to_run = [p for p in profiles if p["id"] == trigger_profile and p.get("active", True)]
        if not profiles_to_run:
            print(f"[Error] Profile '{trigger_profile}' not found or not active")
            sys.exit(1)
    else:
        # Run all active profiles (scheduled push)
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
        count = target_count or profile.get("count") or None

        print(f"\n{'='*60}")
        print(f"[Profile] {profile_name}")
        print(f"[Query] {query}")
        print(f"[Sources] {sources}")
        print(f"[Venues] {venue_filter_name} -> {venue_list}")
        print(f"[Count] {count or 'auto'}")

        # Step 1: Parse query with GPT
        print("[Step 1] Parsing query...")
        try:
            parsed = parse_query(query, client, model=gpt_model)
            print(f"  Keywords: {parsed['keywords_en']}")
            print(f"  Alt keywords: {parsed['keywords_alt']}")
            print(f"  Focus: {parsed['focus']}")
            print(f"  Year from: {parsed.get('year_from')}")
        except Exception as e:
            print(f"  [Error] Query parsing failed: {e}")
            profile_results[profile_name] = []
            continue

        # Step 2: Search with primary keywords
        print("[Step 2] Searching papers...")
        search_max = (count or 5) * 4  # fetch extra for filtering
        papers = router.search(
            keywords=parsed["keywords_en"],
            sources=sources,
            venue_filter_name=venue_filter_name,
            venue_list=venue_list,
            max_results=search_max,
            year_from=parsed.get("year_from"),
        )
        print(f"  Found {len(papers)} papers with primary keywords")

        # If not enough results, try alternative keywords
        if len(papers) < (count or 5):
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

        # Step 4: Filter and summarize with GPT
        print("[Step 4] Filtering and summarizing...")
        try:
            enriched = filter_and_summarize(
                papers=papers,
                user_query=query,
                client=client,
                model=gpt_model,
                target_count=count,
            )
            print(f"  Selected {len(enriched)} papers")
        except Exception as e:
            print(f"  [Error] Summarization failed: {e}")
            # Fallback: use raw results without summaries
            enriched = [p.to_dict() for p in papers[:count or 5]]
            for p in enriched:
                p["relevance_reason"] = "自动检索结果（摘要生成失败）"
                p["summary_zh"] = "摘要生成失败，请直接查看Abstract。"

        profile_results[profile_name] = enriched

        # Track papers for history update
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

    # ── Build and send email ──
    now = get_mdt_now()
    push_time = now.strftime("%Y年%m月%d日 %A %H:%M (MDT)")

    total_papers = sum(len(papers) for papers in profile_results.values())
    if total_papers == 0:
        print("\n[Info] No papers to push. Skipping email.")
        return

    print(f"\n[Step 5] Building email ({total_papers} papers total)...")
    html = build_email_html(profile_results, push_time)

    subject = f"📚 Paper Agent — {now.strftime('%m/%d')} | {total_papers} 篇论文推送"

    print("[Step 6] Sending email...")
    try:
        send_email(
            to_email=config["global"]["email"],
            subject=subject,
            html_content=html,
            gmail_address=gmail_address,
            gmail_app_password=gmail_app_password,
        )
        print("[Done] Email sent successfully!")
    except Exception as e:
        print(f"[Error] Email send failed: {e}")
        sys.exit(1)

    # ── Update history ──
    print("[Step 7] Updating history...")
    history = update_history(history, all_pushed_papers, now.isoformat())
    save_history(history, history_path)
    print(f"[Done] History updated. Total tracked: {len(history['pushed_papers'])}")


if __name__ == "__main__":
    run()
