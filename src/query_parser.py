"""Parse user's natural language query into structured search parameters using GPT."""

import json
from openai import OpenAI
from datetime import datetime


PARSE_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "search_params",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "keywords_en": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "English search keywords for academic APIs (3-8 keywords)"
                },
                "keywords_alt": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Alternative/broader English keywords for fallback search"
                },
                "focus": {
                    "type": "string",
                    "enum": ["theory", "implementation", "survey", "application", "any"],
                    "description": "The focus of papers the user wants"
                },
                "time_range": {
                    "type": "string",
                    "enum": ["recent_1_year", "recent_2_years", "recent_5_years", "any"],
                    "description": "How recent the papers should be"
                },
                "venue_preference": {
                    "type": "string",
                    "enum": ["top_venues", "specific_venues", "any"],
                    "description": "Whether user wants top-tier venues or any"
                }
            },
            "required": ["keywords_en", "keywords_alt", "focus", "time_range", "venue_preference"],
            "additionalProperties": False
        }
    }
}

SYSTEM_PROMPT = """You are a research assistant that converts natural language paper search requests into structured search parameters.

Your job:
1. Extract the core research topic and convert to effective English search keywords for academic search engines (Semantic Scholar, OpenAlex).
2. Generate alternative/broader keywords as fallback.
3. Determine the focus (theory, implementation, survey, application, or any).
4. Determine how recent the papers should be.
5. Determine venue preference.

Guidelines:
- Keywords should be in English regardless of the input language.
- Include both specific terms and broader synonyms.
- For implementation-focused queries, include terms like "system", "framework", "pipeline", "architecture".
- For theory-focused queries, include terms like "model", "method", "algorithm", "approach".
- Be generous with keywords - more is better for recall.

Examples:
Input: "帮我找好的journal或者conference的应用GraphRAG成功完成工程实现的论文"
Output keywords_en: ["GraphRAG", "graph retrieval augmented generation", "knowledge graph RAG", "implementation", "system"]
Output keywords_alt: ["retrieval augmented generation", "knowledge graph", "question answering"]
Output focus: "implementation"
Output time_range: "recent_2_years"
Output venue_preference: "top_venues"
"""


def parse_query(query: str, client: OpenAI, model: str = "gpt-5.2") -> dict:
    """
    Parse a natural language query into structured search parameters.

    Returns dict with keys: keywords_en, keywords_alt, focus, time_range, venue_preference
    """
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ],
        response_format=PARSE_SCHEMA,
        temperature=0.3,
    )

    result = json.loads(response.choices[0].message.content)

    # Convert time_range to year_from
    current_year = datetime.now().year
    time_map = {
        "recent_1_year": current_year - 1,
        "recent_2_years": current_year - 2,
        "recent_5_years": current_year - 5,
        "any": None,
    }
    result["year_from"] = time_map.get(result["time_range"])

    return result
