"""
retriever.py

Takes a natural-language query, embeds it using the same model used for
indexing, and searches the Qdrant collection for the top-k most similar
chunks. Supports optional metadata filtering (e.g. by access_role or
department) for later role-based access control.

This is intentionally the "naive RAG" retrieval step — pure dense
(semantic) search, no BM25/hybrid, no reranking yet. Those get added
in later iterations once this baseline is confirmed working.
"""

from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

EMBEDDING_MODEL_NAME = "BAAI/bge-small-en-v1.5"
COLLECTION_NAME = "techify_onboarding_docs"
LOCAL_QDRANT_PATH = "vectorstore/qdrant_local"

_model = None
_client = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _model


def get_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(path=LOCAL_QDRANT_PATH)
    return _client


def retrieve(query: str, top_k: int = 5, access_role: str | None = None) -> list[dict]:
    """
    Retrieve the top_k most relevant chunks for a query.

    If access_role is provided (e.g. "engineering", "finance"), results
    are filtered to only chunks tagged "all" or matching that role —
    this is the hook for role-based access control, wired in properly
    once src/access_control is built.
    """
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
        limit=top_k,
        query_filter=query_filter,
        with_payload=True,
    ).points

    formatted = []
    for point in results:
        formatted.append(
            {
                "score": point.score,
                "doc_id": point.payload["doc_id"],
                "title": point.payload["title"],
                "section_heading": point.payload["section_heading"],
                "department": point.payload["department"],
                "access_role": point.payload["access_role"],
                "text": point.payload["text"],
            }
        )

    return formatted


def print_results(query: str, results: list[dict]):
    print(f"\nQuery: '{query}'")
    print("-" * 60)
    for i, r in enumerate(results, 1):
        print(f"\n[{i}] score={r['score']:.3f} | {r['title']} > {r['section_heading']}")
        print(f"    (doc_id: {r['doc_id']}, department: {r['department']}, access_role: {r['access_role']})")
        print(f"    {r['text'][:200]}...")


if __name__ == "__main__":
    test_queries = [
        "How many days of paid time off do I get?",
        "How do I set up VPN access?",
        "What's the process for expense reimbursement?",
        "What is Techify's stock price?",  # should retrieve poorly / low scores — not in corpus
    ]

    for q in test_queries:
        results = retrieve(q, top_k=3)
        print_results(q, results)
        print("\n" + "=" * 60)