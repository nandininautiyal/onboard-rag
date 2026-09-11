"""
hybrid_retriever.py

Combines dense (semantic) retrieval from Qdrant with sparse (keyword)
retrieval via BM25, merging results using Reciprocal Rank Fusion (RRF).

Also applies role-based access filtering: given a user_role (e.g.
"sales", "engineering"), only chunks tagged "all" or matching that
role's allowed access tags (see src/access_control/role_filter.py)
are retrieved at all — restricted content never even reaches the
candidate pool, let alone the LLM.
"""

import hashlib

from rank_bm25 import BM25Okapi
from qdrant_client.models import Filter, FieldCondition, MatchValue

from ..ingestion.loaders import load_documents
from ..ingestion.chunker import chunk_all_documents
from ..access_control.role_filter import get_allowed_access_roles
from .retriever import get_model, get_client, COLLECTION_NAME

RRF_K = 60
DENSE_CANDIDATES = 20
BM25_CANDIDATES = 20

_bm25_index = None
_bm25_chunks = None


def _chunk_key(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def _tokenize(text: str) -> list[str]:
    return text.lower().split()


def build_bm25_index():
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


def bm25_search(query: str, top_n: int = BM25_CANDIDATES, allowed_roles: set[str] | None = None) -> list[dict]:
    if _bm25_index is None:
        build_bm25_index()

    tokenized_query = _tokenize(query)
    scores = _bm25_index.get_scores(tokenized_query)

    scored_chunks = list(zip(_bm25_chunks, scores))

    if allowed_roles is not None:
        scored_chunks = [(c, s) for c, s in scored_chunks if c["access_role"] in allowed_roles]

    ranked = sorted(scored_chunks, key=lambda x: x[1], reverse=True)[:top_n]
    return [{**chunk, "bm25_score": float(score)} for chunk, score in ranked]


def dense_search(query: str, top_n: int = DENSE_CANDIDATES, allowed_roles: set[str] | None = None) -> list[dict]:
    model = get_model()
    client = get_client()

    query_vector = model.encode(query, normalize_embeddings=True).tolist()

    query_filter = None
    if allowed_roles is not None:
        query_filter = Filter(
            should=[
                FieldCondition(key="access_role", match=MatchValue(value=role))
                for role in allowed_roles
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


def hybrid_retrieve(query: str, top_k: int = 5, user_role: str | None = None) -> list[dict]:
    """
    user_role: an employee role (e.g. "engineering", "sales", "manager").
    If provided, retrieval is restricted to chunks tagged "all" or
    matching that role's allowed access tags. If None, no restriction
    is applied (full-corpus access — used for eval/testing).
    """
    allowed_roles = get_allowed_access_roles(user_role)

    dense_results = dense_search(query, top_n=DENSE_CANDIDATES, allowed_roles=allowed_roles)
    bm25_results = bm25_search(query, top_n=BM25_CANDIDATES, allowed_roles=allowed_roles)

    merged = reciprocal_rank_fusion(dense_results, bm25_results)
    return merged[:top_k]


def print_results(query: str, results: list[dict]):
    print(f"\nQuery: '{query}'")
    print("-" * 60)
    if not results:
        print("  (no results — likely filtered out by access role)")
        return
    for i, r in enumerate(results, 1):
        print(f"\n[{i}] rrf_score={r['rrf_score']:.4f} | {r['title']} > {r['section_heading']}")
        print(f"    (doc_id: {r['doc_id']}, access_role: {r['access_role']})")
        print(f"    {r['text'][:200]}...")


if __name__ == "__main__":
    build_bm25_index()

    # Demonstrate access control: an engineering-specific query, asked
    # as different roles, should return different (or no) results.
    query = "What's the on-call rotation policy?"

    for role in [None, "engineering", "sales"]:
        print(f"\n{'='*60}\nAsking as role: {role}\n{'='*60}")
        results = hybrid_retrieve(query, top_k=3, user_role=role)
        print_results(query, results)