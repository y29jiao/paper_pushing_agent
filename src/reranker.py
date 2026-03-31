"""Embedding-based semantic reranking for papers."""

import math
from src.search.base import PaperResult


def rerank_papers(
    papers: list[PaperResult],
    query: str,
    client,
    top_k: int,
    model: str = "text-embedding-3-small",
    keyword_weight: float = 0.3,
    embedding_weight: float = 0.7,
) -> list[PaperResult]:
    """
    Rerank papers by combining keyword search rank with embedding cosine similarity.

    Args:
        papers: Papers from keyword search (already deduped), order = keyword relevance.
        query: Original user query.
        client: OpenAI client instance.
        top_k: Number of papers to return.
        model: Embedding model name.
        keyword_weight: Weight for keyword rank score (0-1).
        embedding_weight: Weight for embedding similarity (0-1).

    Returns:
        Top-k papers sorted by combined score.
    """
    if not papers:
        return papers

    # Build text for each paper
    paper_texts = []
    for p in papers:
        abstract_snippet = (p.abstract or "")[:500]
        paper_texts.append(f"{p.title}. {abstract_snippet}" if abstract_snippet else p.title)

    # Get embeddings
    try:
        query_emb = _get_embeddings([query], client, model)[0]
        paper_embs = _get_embeddings(paper_texts, client, model)
    except Exception as e:
        print(f"  [Reranker] Embedding API failed: {e}, skipping rerank")
        return papers[:top_k]

    # Score each paper
    total = len(papers)
    scored = []
    for i, paper in enumerate(papers):
        cos_sim = _cosine_similarity(query_emb, paper_embs[i])
        keyword_rank_score = 1.0 - (i / total)
        combined = keyword_weight * keyword_rank_score + embedding_weight * cos_sim
        scored.append((combined, cos_sim, paper))

    # Sort by combined score descending
    scored.sort(key=lambda x: x[0], reverse=True)

    # Log top boosts (papers that moved up significantly thanks to embedding)
    for rank, (combined, cos_sim, paper) in enumerate(scored[:top_k]):
        orig_rank = papers.index(paper)
        if orig_rank - rank >= 5:
            print(f"  [Reranker] Boosted: \"{paper.title[:60]}...\" "
                  f"rank {orig_rank+1} -> {rank+1} (sim={cos_sim:.3f})")

    return [paper for _, _, paper in scored[:top_k]]


def _get_embeddings(texts: list[str], client, model: str) -> list[list[float]]:
    """Get embeddings for a list of texts, handling batching."""
    all_embeddings = []
    batch_size = 2048
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        resp = client.embeddings.create(input=batch, model=model)
        all_embeddings.extend([d.embedding for d in resp.data])
    return all_embeddings


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
