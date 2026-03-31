"""GPT-based paper filtering and summarization."""

import json
from openai import OpenAI
from src.search.base import PaperResult


SUMMARIZE_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "paper_summaries",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "selected_papers": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "index": {
                                "type": "integer",
                                "description": "0-based index of the paper in the candidate list"
                            },
                            "relevance_reason": {
                                "type": "string",
                                "description": "1-2 sentences explaining why this paper matches the user's need"
                            },
                            "summary_text": {
                                "type": "string",
                                "description": "Summary (3-5 sentences) highlighting key contributions, methods, and results"
                            },
                            "relevance_score": {
                                "type": "number",
                                "description": "Relevance score from 0 to 1"
                            }
                        },
                        "required": ["index", "relevance_reason", "summary_text", "relevance_score"],
                        "additionalProperties": False
                    }
                }
            },
            "required": ["selected_papers"],
            "additionalProperties": False
        }
    }
}

SYSTEM_PROMPT_TEMPLATE = """You are an expert research paper reviewer. Your job is to:

1. Filter candidate papers based on the user's original request - only keep papers that are genuinely relevant.
2. For each selected paper, explain WHY it's relevant (1-2 sentences, in {language_name}).
3. Write a {language_name} summary (3-5 sentences) that highlights:
   - The core contribution/novelty
   - The method/approach used
   - Key results or findings
   - Engineering/practical significance (if the user cares about implementation)
4. Assign a relevance score (0-1) to help with ranking.

Be strict in filtering. If a paper's abstract doesn't clearly match the user's need, don't include it.
If the user wants implementation/engineering papers, prioritize those with concrete systems, frameworks, or experiments.
If the user wants theoretical papers, prioritize those with novel models or algorithms.

Always write summaries in {language_instruction}. The relevance_reason should also be in {language_instruction}.
"""


def filter_and_summarize(
    papers: list[PaperResult],
    user_query: str,
    client: OpenAI,
    model: str = "gpt-5.4-mini",
    target_count: int | None = None,
    output_language: str = "zh",
) -> list[dict]:
    """
    Use GPT to filter and summarize candidate papers.

    Args:
        papers: Candidate papers from search
        user_query: Original user query for context
        client: OpenAI client
        model: Model to use
        target_count: Desired number of papers (None = model decides)

    Returns:
        List of dicts with paper info + summary
    """
    if not papers:
        return []

    # Build candidate list for GPT
    candidates = []
    for i, paper in enumerate(papers):
        entry = f"[{i}] Title: {paper.title}\n"
        entry += f"    Venue: {paper.venue or 'N/A'} | Year: {paper.year or 'N/A'}"
        if paper.citation_count is not None:
            entry += f" | Citations: {paper.citation_count}"
        if paper.score is not None:
            entry += f" | Review Score: {paper.score}"
        entry += f"\n    Abstract: {paper.abstract[:800]}"
        candidates.append(entry)

    candidates_text = "\n\n".join(candidates)

    count_instruction = ""
    if target_count:
        count_instruction = f"\nSelect approximately {target_count} most relevant papers."
    else:
        count_instruction = "\nSelect the most relevant papers. Use your judgment on how many to include (typically 3-8)."

    user_message = f"""User's search request: {user_query}
{count_instruction}

Candidate papers:
{candidates_text}"""

    language_name = "Simplified Chinese" if output_language == "zh" else "English"
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        language_name=language_name,
        language_instruction=language_name,
    )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        response_format=SUMMARIZE_SCHEMA,
        temperature=0.4,
    )

    result = json.loads(response.choices[0].message.content)

    # Merge GPT output with original paper data
    enriched = []
    for selection in result.get("selected_papers", []):
        idx = selection["index"]
        if 0 <= idx < len(papers):
            paper = papers[idx]
            summary_text = selection["summary_text"]
            enriched.append({
                **paper.to_dict(),
                "relevance_reason": selection["relevance_reason"],
                "summary_text": summary_text,
                "summary_zh": summary_text if output_language == "zh" else paper.to_dict().get("summary_zh"),
                "relevance_score": selection["relevance_score"],
            })

    # Sort by relevance score descending
    enriched.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)

    return enriched
