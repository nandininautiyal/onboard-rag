"""
run_eval.py

Evaluation harness for the Wayfinder RAG pipeline. Runs every question in
data/qa_testset.json through the full pipeline (hybrid retrieval -> rerank
-> generation) and measures:

1. Retrieval hit rate: for answerable questions, did the correct source
   document appear anywhere in the top-k reranked chunks?
2. Answer-attempt rate: for answerable questions, did the system actually
   attempt an answer (grounded == True) rather than incorrectly refusing?
3. Correct refusal rate: for unanswerable questions, did the system
   correctly decline to answer (grounded == False)? This is the
   hallucination-resistance metric.

Results are saved per-question to eval/results/eval_results.json (for
manual inspection / spot-checking answer quality) and a summary is
printed to the console.

Run from the project root as: python -m eval.run_eval
"""

import json
import os
import time

from src.generation.generator import answer_query
from src.retrieval.hybrid_retriever import hybrid_retrieve, build_bm25_index
from src.retrieval.reranker import rerank

QA_TESTSET_PATH = "data/qa_testset.json"
RESULTS_PATH = "eval/results/eval_results.json"

FINAL_TOP_K = 5
HYBRID_CANDIDATES = 20

REFUSAL_PHRASE = "i don't have information about this in the onboarding docs"


def is_refusal(answer_text: str) -> bool:
    """
    Catches cases where the LLM itself decided to refuse during generation
    (grounded=True was set because retrieval score passed threshold), not
    just cases where the score-based early-exit triggered. Without this,
    a correct LLM-level refusal gets miscounted as an attempted answer.
    """
    return REFUSAL_PHRASE in answer_text.lower()


def load_testset() -> list[dict]:
    with open(QA_TESTSET_PATH, encoding="utf-8") as f:
        return json.load(f)


def get_retrieved_doc_ids(question: str) -> list[str]:
    candidates = hybrid_retrieve(question, top_k=HYBRID_CANDIDATES)
    reranked = rerank(question, candidates, top_k=FINAL_TOP_K)
    return [c["doc_id"] for c in reranked]


def check_retrieval_hit(expected_source: str, retrieved_doc_ids: list[str]) -> bool:
    expected_docs = [d.strip() for d in expected_source.split(",") if d.strip()]
    if not expected_docs:
        return False
    return any(doc in retrieved_doc_ids for doc in expected_docs)


def run_eval():
    build_bm25_index()
    testset = load_testset()

    results = []
    retrieval_hits = 0
    retrieval_total = 0
    correct_refusals = 0
    unanswerable_total = 0
    correct_answers_attempted = 0
    answerable_total = 0

    for i, item in enumerate(testset, 1):
        question = item["question"]
        expected_answer = item["expected_answer"]
        source_doc_id = item.get("source_doc_id", "")
        answerable = item.get("answerable", True)

        print(f"[{i}/{len(testset)}] {question}")

        start = time.time()
        retrieved_doc_ids = get_retrieved_doc_ids(question)
        result = answer_query(question)
        elapsed = time.time() - start

        effectively_answered = result["grounded"] and not is_refusal(result["answer"])

        retrieval_hit = None
        if answerable:
            retrieval_total += 1
            retrieval_hit = check_retrieval_hit(source_doc_id, retrieved_doc_ids)
            if retrieval_hit:
                retrieval_hits += 1

            answerable_total += 1
            if effectively_answered:
                correct_answers_attempted += 1
        else:
            unanswerable_total += 1
            if not effectively_answered:
                correct_refusals += 1

        results.append(
            {
                "question": question,
                "expected_answer": expected_answer,
                "source_doc_id": source_doc_id,
                "answerable": answerable,
                "retrieved_doc_ids": retrieved_doc_ids,
                "retrieval_hit": retrieval_hit,
                "system_answer": result["answer"],
                "grounded": result["grounded"],
                "top_score": result["top_score"],
                "time_seconds": round(elapsed, 2),
            }
        )

    os.makedirs(os.path.dirname(RESULTS_PATH), exist_ok=True)
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("\n" + "=" * 60)
    print("EVAL SUMMARY")
    print("=" * 60)
    if retrieval_total:
        print(
            f"Retrieval hit rate (answerable Qs): {retrieval_hits}/{retrieval_total} "
            f"({100 * retrieval_hits / retrieval_total:.1f}%)"
        )
    if answerable_total:
        print(
            f"Answer-attempt rate (answerable Qs): {correct_answers_attempted}/{answerable_total} "
            f"({100 * correct_answers_attempted / answerable_total:.1f}%)"
        )
    if unanswerable_total:
        print(
            f"Correct refusal rate (unanswerable Qs): {correct_refusals}/{unanswerable_total} "
            f"({100 * correct_refusals / unanswerable_total:.1f}%)"
        )
    print(f"\nFull per-question results saved to {RESULTS_PATH}")


if __name__ == "__main__":
    run_eval()