"""
generator.py

Takes a user query, retrieves relevant chunks (via src.retrieval.retriever),
and generates a grounded natural-language answer using a local LLM served
by Ollama (free, runs on-device — no API costs).

Key design choices:
- The system prompt forces the model to answer ONLY from provided context.
- If the top retrieval score is below CONFIDENCE_THRESHOLD, we skip
  generation entirely and return a canned "not found" response — this is
  our first line of defense against hallucination on out-of-corpus
  questions (like "What is Techify's stock price?").
- Every answer includes citations back to the source doc_id/title so the
  user can verify or read further.
- Generation backend is intentionally isolated in call_llm() so this can
  later be swapped to a paid API (Claude/GPT) via a config flag without
  touching any other part of the pipeline.
"""

import requests

from ..retrieval.retriever import retrieve

OLLAMA_URL = "http://localhost:11434/api/generate"
GENERATION_MODEL = "llama3.1:8b"
TOP_K = 5
CONFIDENCE_THRESHOLD = 0.55  # below this top score, we assume no real match exists

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


def format_context(chunks: list[dict]) -> str:
    blocks = []
    for i, chunk in enumerate(chunks, 1):
        blocks.append(
            f"[Chunk {i}] Source: {chunk['title']} > {chunk['section_heading']}\n{chunk['text']}"
        )
    return "\n\n".join(blocks)


def call_llm(prompt: str) -> str:
    """
    Calls the local Ollama server to generate a response.
    Isolated here so the generation backend can be swapped later
    (e.g. to Claude/GPT API) without changing answer_query().
    """
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
    Full RAG pipeline: retrieve -> confidence check -> generate.
    Returns a dict with the answer, whether it was grounded, and sources used.
    """
    chunks = retrieve(query, top_k=TOP_K, access_role=access_role)

    if not chunks or chunks[0]["score"] < CONFIDENCE_THRESHOLD:
        return {
            "answer": "I don't have information about this in the onboarding docs — please check with the relevant team.",
            "grounded": False,
            "sources": [],
            "top_score": chunks[0]["score"] if chunks else None,
        }

    context = format_context(chunks)
    prompt = f"Context:\n\n{context}\n\nQuestion: {query}"

    answer_text = call_llm(prompt)

    sources = list({f"{c['title']}" for c in chunks})

    return {
        "answer": answer_text,
        "grounded": True,
        "sources": sources,
        "top_score": chunks[0]["score"],
    }


if __name__ == "__main__":
    test_queries = [
        "How many days of paid time off do I get?",
        "How do I set up VPN access?",
        "What's the process for expense reimbursement?",
        "What is Techify's stock price?",
    ]

    for q in test_queries:
        result = answer_query(q)
        print(f"\nQ: {q}")
        print(f"Top score: {result['top_score']}")
        print(f"Answer: {result['answer']}")
        if result["sources"]:
            print(f"Sources: {', '.join(result['sources'])}")
        print("=" * 60)