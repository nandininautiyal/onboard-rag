"""
hybrid_retriever.py

Combines dense (semantic) retrieval from Qdrant with sparse (keyword)
retrieval via BM25, merging results using Reciprocal Rank Fusion (RRF).

Why this matters: pure dense/semantic search can miss exact-term queries
(tool names, acronyms, specific phrases like "1Password" or "GlobalProtect")
that BM25 keyword matching catches easily. Combining both gives more robust
retrieval than either alone.

RRF is used to merge the two ranked lists because it doesn't require the
two methods' raw scores to be on the same scale (cosine similarity vs.
BM25 scores are not directly comparable) — it only uses each result's
*rank position* in its own list.
"""

import hashlib

from rank_bm25 import BM25Okapi
from qdrant_client.models import Filter, FieldCondition, MatchValue

from ..ingestion.loaders import load_documents
from ..ingestion.chunker import chunk_all_documents
from .retriever import get_model, get_client, COLLECTION_NAME

RRF_K = 60  # standard smoothing constant for Reciprocal Rank Fusion
DENSE_CANDIDATES = 20
BM25_CANDIDATES = 20

_bm25_index = None
_bm25_chunks = None  # list of chunk dicts, aligned with the BM25 corpus order


def _chunk_key(text: str) -> str:
    """Stable identifier for a chunk based on its text content, used to
    match the same chunk across dense and BM25 result sets (their
    randomly-generated chunk_ids differ across separate chunking runs,
    but the underlying text is identical since chunking is deterministic)."""
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def _tokenize(text: str) -> list[str]:
    return text.lower().split()


def build_bm25_index():
    """Builds the in-memory BM25 index over all chunks. Cached at module
    level so it's only built once per process."""
    global _bm25_index, _bm25_chunks

    documents = load_documents()
    chunks = chunk_all_documents(documents)

    _bm25_chunks = []
    tokenized_corpus = []

    for chunk in chunks:
        chunk_dict = {
            "key": _chunk_key(chunk.text),
            "doc_id": chunk.doc_id,
            "title": chunk.title,
            "department": chunk.department,
            "doc_type": chunk.doc_type,
            "access_role": chunk.access_role,
            "section_heading": chunk.section_heading,
            "text": chunk.text,
        }
        _bm25_chunks.append(chunk_dict)
        tokenized_corpus.append(_tokenize(chunk.text))

    _bm25_index = BM25Okapi(tokenized_corpus)
    print(f"Built BM25 index over {len(_bm25_chunks)} chunks")


def bm25_search(query: str, top_n: int = BM25_CANDIDATES) -> list[dict]:
    if _bm25_index is None:
        build_bm25_index()

    tokenized_query = _tokenize(query)
    scores = _bm25_index.get_scores(tokenized_query)

    ranked = sorted(zip(_bm25_chunks, scores), key=lambda x: x[1], reverse=True)[:top_n]
    return [{**chunk, "bm25_score": float(score)} for chunk, score in ranked]


def dense_search(query: str, top_n: int = DENSE_CANDIDATES, access_role: str | None = None) -> list[dict]:
    model = get_model()
    client = get_client()

    query_vector = model.encode(query, normalize_embeddings=True).tolist()

    query_filter = None
    if access_role:
        query_filter = Filter(
            should=[
                FieldCondition(key="access_role", match=MatchValue(value="all")),
                FieldCondition(key="access_role", match=MatchValue(value=access_role)),
            ]
        )

    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=top_n,
        query_filter=query_filter,
        with_payload=True,
    ).points

    formatted = []
    for point in results:
        payload = point.payload
        formatted.append(
            {
                "key": _chunk_key(payload["text"]),
                "doc_id": payload["doc_id"],
                "title": payload["title"],
                "department": payload["department"],
                "doc_type": payload.get("doc_type"),
                "access_role": payload["access_role"],
                "section_heading": payload["section_heading"],
                "text": payload["text"],
                "dense_score": point.score,
            }
        )
    return formatted


def reciprocal_rank_fusion(dense_results: list[dict], bm25_results: list[dict], k: int = RRF_K) -> list[dict]:
    """
    score(chunk) = sum over each list it appears in of 1 / (k + rank)
    Chunks appearing near the top of either (or both) lists score highest.
    """
    scores = {}
    chunk_lookup = {}

    for rank, chunk in enumerate(dense_results):
        key = chunk["key"]
        scores[key] = scores.get(key, 0) + 1 / (k + rank + 1)
        chunk_lookup[key] = chunk

    for rank, chunk in enumerate(bm25_results):
        key = chunk["key"]
        scores[key] = scores.get(key, 0) + 1 / (k + rank + 1)
        chunk_lookup.setdefault(key, chunk)

    merged = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    return [{**chunk_lookup[key], "rrf_score": score} for key, score in merged]


def hybrid_retrieve(query: str, top_k: int = 5, access_role: str | None = None) -> list[dict]:
    dense_results = dense_search(query, top_n=DENSE_CANDIDATES, access_role=access_role)
    bm25_results = bm25_search(query, top_n=BM25_CANDIDATES)

    if access_role:
        bm25_results = [c for c in bm25_results if c["access_role"] in ("all", access_role)]

    merged = reciprocal_rank_fusion(dense_results, bm25_results)
    return merged[:top_k]


def print_results(query: str, results: list[dict]):
    print(f"\nQuery: '{query}'")
    print("-" * 60)
    for i, r in enumerate(results, 1):
        print(f"\n[{i}] rrf_score={r['rrf_score']:.4f} | {r['title']} > {r['section_heading']}")
        print(f"    (doc_id: {r['doc_id']}, department: {r['department']})")
        print(f"    {r['text'][:200]}...")


if __name__ == "__main__":
    build_bm25_index()

    test_queries = [
        "How many days of paid time off do I get?",
        "1Password setup",
        "GlobalProtect VPN",
        "What is Techify's stock price?",
    ]

    for q in test_queries:
        results = hybrid_retrieve(q, top_k=3)
        print_results(q, results)
        print("\n" + "=" * 60)