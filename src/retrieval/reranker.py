"""
reranker.py

Re-scores a set of candidate chunks against the query using a cross-encoder
model (bge-reranker-base), which jointly encodes (query, chunk) pairs rather
than comparing separately-computed embeddings. This is slower than dense/BM25
retrieval but significantly more accurate at judging true relevance, which is
why the standard pattern is: retrieve broadly (top-20 via hybrid search),
then rerank narrowly (top-5) before passing to the LLM.
"""

from sentence_transformers import CrossEncoder

RERANKER_MODEL_NAME = "BAAI/bge-reranker-base"

_reranker = None


def get_reranker() -> CrossEncoder:
    global _reranker
    if _reranker is None:
        _reranker = CrossEncoder(RERANKER_MODEL_NAME)
    return _reranker


def rerank(query: str, candidates: list[dict], top_k: int = 5) -> list[dict]:
    """
    candidates: list of chunk dicts (as returned by hybrid_retrieve), each
    must have a "text" field.
    Returns the top_k candidates re-sorted by cross-encoder relevance score,
    with a "rerank_score" field added to each.
    """
    if not candidates:
        return []

    reranker = get_reranker()

    pairs = [(query, c["text"]) for c in candidates]
    scores = reranker.predict(pairs)

    scored = list(zip(candidates, scores))
    scored.sort(key=lambda x: x[1], reverse=True)

    results = []
    for chunk, score in scored[:top_k]:
        results.append({**chunk, "rerank_score": float(score)})

    return results


if __name__ == "__main__":
    from .hybrid_retriever import hybrid_retrieve, build_bm25_index

    build_bm25_index()

    test_queries = [
        "How many days of paid time off do I get?",
        "1Password setup",
        "GlobalProtect VPN",
    ]

    for q in test_queries:
        candidates = hybrid_retrieve(q, top_k=20)
        reranked = rerank(q, candidates, top_k=3)

        print(f"\nQuery: '{q}'")
        print("-" * 60)
        for i, r in enumerate(reranked, 1):
            print(f"\n[{i}] rerank_score={r['rerank_score']:.4f} | {r['title']} > {r['section_heading']}")
            print(f"    {r['text'][:200]}...")
        print("\n" + "=" * 60)