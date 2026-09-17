"""
generator.py

Full RAG pipeline: hybrid retrieval (dense + BM25, role-filtered) ->
cross-encoder reranking -> confidence check -> grounded generation.

Generation backend is controlled by the GENERATION_BACKEND environment
variable:
    - "ollama" (default): free, local inference via Ollama. Used for
      local development — no API costs, no internet dependency.
    - "groq": free-tier hosted inference via Groq's API. Used for the
      publicly deployed version (e.g. on Hugging Face Spaces), since
      a deployed environment can't run a local Ollama server.

This isolation means switching environments is a one-line .env change,
not a code change — call_llm() is the only place backend-specific logic
lives; everything else in the pipeline is backend-agnostic.
"""

import os

import requests
from dotenv import load_dotenv

from ..retrieval.hybrid_retriever import hybrid_retrieve, build_bm25_index
from ..retrieval.reranker import rerank

load_dotenv()

GENERATION_BACKEND = os.getenv("GENERATION_BACKEND", "ollama").lower()

# --- Ollama (local) config ---
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.1:8b"

# --- Groq (hosted) config ---
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

HYBRID_CANDIDATES = 20
FINAL_TOP_K = 5
CONFIDENCE_THRESHOLD = 0.4
# See earlier calibration notes: genuine matches scored 0.86-0.98,
# tangential/irrelevant ones 0.01-0.25 in manual testing. To be tuned
# properly once the eval harness runs against qa_testset.json.

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


def _call_ollama(prompt: str) -> str:
    full_prompt = f"{SYSTEM_PROMPT}\n\n{prompt}"
    response = requests.post(
        OLLAMA_URL,
        json={"model": OLLAMA_MODEL, "prompt": full_prompt, "stream": False},
        timeout=120,
    )
    response.raise_for_status()
    return response.json()["response"].strip()


def _call_groq(prompt: str) -> str:
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not set in .env, but GENERATION_BACKEND=groq")

    response = requests.post(
        GROQ_URL,
        headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
        json={
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 500,
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip()


def call_llm(prompt: str) -> str:
    if GENERATION_BACKEND == "groq":
        return _call_groq(prompt)
    return _call_ollama(prompt)


def answer_query(query: str, user_role: str | None = None) -> dict:
    """
    Full RAG pipeline: hybrid retrieve (role-filtered) -> rerank ->
    confidence check -> generate.
    """
    _ensure_bm25_ready()

    candidates = hybrid_retrieve(query, top_k=HYBRID_CANDIDATES, user_role=user_role)
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
    print(f"Using generation backend: {GENERATION_BACKEND}")

    test_queries = [
        "How many days of paid time off do I get?",
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