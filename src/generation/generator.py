"""
generator.py

Full RAG pipeline: hybrid retrieval (dense + BM25) -> cross-encoder
reranking -> confidence check -> grounded generation via local Ollama.

Pipeline stages:
1. hybrid_retrieve() pulls a broad candidate set (top-20) combining
   semantic and keyword search.
2. rerank() re-scores those candidates with a cross-encoder for much
   more accurate relevance judgments, narrowing to the final top-k.
3. If the top reranked score is below CONFIDENCE_THRESHOLD, we skip
   generation and return a canned "not found" response. Rerank scores
   are far better separated than raw dense/RRF scores (~0.85-0.98 for
   genuine matches vs. near-zero for irrelevant ones), so this check
   is now meaningfully more reliable than the old dense-score threshold.
4. The LLM is still explicitly instructed to say "I don't know" if the
   provided context doesn't answer the question, as a second layer of
   defense beyond the score-based check.
"""

import requests

from ..retrieval.hybrid_retriever import hybrid_retrieve, build_bm25_index
from ..retrieval.reranker import rerank

OLLAMA_URL = "http://localhost:11434/api/generate"
GENERATION_MODEL = "llama3.1:8b"

HYBRID_CANDIDATES = 20   # broad candidate pool from hybrid retrieval
FINAL_TOP_K = 5          # final chunk count after reranking
CONFIDENCE_THRESHOLD = 0.4  # rerank_score below this = treat as "no real match"
# NOTE: this threshold is a reasonable starting point based on manual testing
# (genuine matches scored 0.86-0.98, tangential ones 0.01-0.25). It should be
# tuned properly once the eval harness runs against qa_testset.json's
# unanswerable questions.

SYSTEM_PROMPT = """You are Wayfinder, an onboarding assistant for Techify employees.

Answer the user's question using ONLY the provided context chunks below.
Do not use any outside knowledge about companies, HR policy, or anything else.

Rules:
- If the context fully answers the question, answer clearly and concisely.
- If the context only partially answers it, say what you know and note what's missing.
- If the context does not contain the answer at all, say exactly:
  "I don't have information about this in the onboarding docs — please check with the relevant team."
- Always cite which document(s) your answer comes from, using the format [Source: <title>].
- Do not make up policy details, numbers, or process steps that aren't explicitly in the context.
"""

_bm25_ready = False


def _ensure_bm25_ready():
    global _bm25_ready
    if not _bm25_ready:
        build_bm25_index()
        _bm25_ready = True


def format_context(chunks: list[dict]) -> str:
    blocks = []
    for i, chunk in enumerate(chunks, 1):
        blocks.append(
            f"[Chunk {i}] Source: {chunk['title']} > {chunk['section_heading']}\n{chunk['text']}"
        )
    return "\n\n".join(blocks)


def call_llm(prompt: str) -> str:
    full_prompt = f"{SYSTEM_PROMPT}\n\n{prompt}"

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": GENERATION_MODEL,
            "prompt": full_prompt,
            "stream": False,
        },
        timeout=120,
    )
    response.raise_for_status()
    return response.json()["response"].strip()


def answer_query(query: str, access_role: str | None = None) -> dict:
    """
    Full RAG pipeline: hybrid retrieve -> rerank -> confidence check -> generate.
    Returns a dict with the answer, whether it was grounded, sources, and the
    top rerank score (useful for debugging/eval).
    """
    _ensure_bm25_ready()

    candidates = hybrid_retrieve(query, top_k=HYBRID_CANDIDATES, access_role=access_role)
    reranked_chunks = rerank(query, candidates, top_k=FINAL_TOP_K)

    if not reranked_chunks or reranked_chunks[0]["rerank_score"] < CONFIDENCE_THRESHOLD:
        return {
            "answer": "I don't have information about this in the onboarding docs — please check with the relevant team.",
            "grounded": False,
            "sources": [],
            "top_score": reranked_chunks[0]["rerank_score"] if reranked_chunks else None,
        }

    context = format_context(reranked_chunks)
    prompt = f"Context:\n\n{context}\n\nQuestion: {query}"

    answer_text = call_llm(prompt)

    sources = list({c["title"] for c in reranked_chunks})

    return {
        "answer": answer_text,
        "grounded": True,
        "sources": sources,
        "top_score": reranked_chunks[0]["rerank_score"],
    }


if __name__ == "__main__":
    test_queries = [
        "How many days of paid time off do I get?",
        "1Password setup",
        "GlobalProtect VPN",
        "What's the process for expense reimbursement?",
        "What is Techify's stock price?",
    ]

    for q in test_queries:
        result = answer_query(q)
        print(f"\nQ: {q}")
        print(f"Top rerank score: {result['top_score']}")
        print(f"Answer: {result['answer']}")
        if result["sources"]:
            print(f"Sources: {', '.join(result['sources'])}")
        print("=" * 60)