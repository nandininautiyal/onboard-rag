# Wayfinder (onboard-rag)

A Retrieval-Augmented Generation (RAG) system that helps new employees navigate company onboarding documentation through natural-language Q&A, instead of manually skimming dozens of policy and process documents.

## The problem

New hires get a firehose of onboarding material — HR policies, IT setup guides, engineering docs, sales processes — and have to dig through all of it to find answers to specific questions like "how many PTO days do I get" or "how do I request VPN access." Wayfinder lets them just ask, and only surfaces answers grounded in the actual company documents, with citations.

## Architecture

```
Company docs (Markdown, YAML frontmatter: doc_id, department, access_role, ...)
        |
        v
   Ingestion (parse metadata + content)
        |
        v
   Chunking (heading-aware, semantic splitting — not fixed character counts)
        |
        v
   Embedding (sentence-transformers, local)
        |
        v
   Vector store (Qdrant, local)

At query time:
        |
        v
   Role-based access filter (restrict candidate pool by employee role)
        |
        v
   Hybrid retrieval: dense (semantic) search + BM25 (keyword) search
        |    merged via Reciprocal Rank Fusion
        v
   Cross-encoder reranking (bge-reranker-base): top-20 -> top-5
        |
        v
   Confidence check (reranker score threshold)
        |
        v
   Grounded generation (local LLM via Ollama) with source citations
        |
        v
   Answer, or an explicit "I don't have this information" if the
   corpus genuinely doesn't cover the question
```

Every design choice in this pipeline is aimed at two things: **retrieval precision** (finding the right document reliably) and **hallucination resistance** (never presenting an unsupported answer as fact).

## Dataset

Since real company documents aren't available for a portfolio project, the corpus is a synthetic company handbook generated for a fictional company, "Techify" (approximately 600 employees, B2B SaaS). It includes:

- **24 Markdown documents** across HR, IT/Security, Engineering, Sales, Marketing, Finance, General FAQ, and Org Info, each with YAML frontmatter (`doc_id`, `title`, `department`, `doc_type`, `last_updated`, `access_role`)
- **A 38-pair QA test set** (`data/qa_testset.json`) used for evaluation, including single-document questions, multi-document questions, and intentionally unanswerable questions (to test hallucination resistance)
- A few documents are intentionally left slightly outdated or ambiguous, simulating the messiness of real internal documentation (for example, a VPN client mid-rebrand, with old and new tool names both still in circulation)

## Tech stack

| Component | Tool |
|---|---|
| Ingestion | Custom Python parser (`python-frontmatter`) |
| Chunking | Custom heading-aware splitter, with `langchain-text-splitters` used only for overflow splitting of long sections |
| Embeddings | `sentence-transformers` (`BAAI/bge-small-en-v1.5`), local, no API cost |
| Vector store | Qdrant (local, on-disk) |
| Sparse retrieval | `rank-bm25` |
| Retrieval fusion | Reciprocal Rank Fusion (custom implementation) |
| Reranking | Cross-encoder, `BAAI/bge-reranker-base` |
| Access control | Custom role-to-access-tag mapping, enforced at the retrieval layer |
| Generation | Local LLM via Ollama (`llama3.1:8b`), no API cost |
| Evaluation | Custom harness against a hand-curated QA test set |

**Why a local LLM instead of a paid API:** Wayfinder runs entirely on local infrastructure — embeddings, retrieval, reranking, and generation all run on-device, with zero inference cost. The generation call is isolated behind a single function (`call_llm()` in `src/generation/generator.py`), so swapping in a hosted API (Claude, GPT) later is a small, contained change rather than a rewrite.

**Why hybrid retrieval, not just dense search:** pure semantic search can under-match exact terms, product names, or acronyms (for example, "1Password" or "GlobalProtect") that a keyword-based method catches easily. Combining dense and BM25 search via Reciprocal Rank Fusion, then reranking with a cross-encoder, measurably improved both retrieval precision and score separation between genuine and irrelevant matches (see Evaluation below).

**Why role-based access control:** onboarding assistants in a real company would need to respect existing access boundaries — a Sales hire should not be able to retrieve Finance- or Engineering-only documents through the assistant. Access filtering happens at the retrieval layer, before reranking or generation, so restricted content never reaches the LLM at all, not just "isn't mentioned in the answer."

## Project structure

```
onboard-rag/
├── data/
│   ├── raw/               # 24 synthetic Techify onboarding docs (.md, frontmatter)
│   ├── processed/
│   ├── chunks/
│   └── qa_testset.json    # evaluation question-answer pairs
├── src/
│   ├── ingestion/          # loaders.py, chunker.py
│   ├── embeddings/         # embed.py
│   ├── retrieval/          # retriever.py, hybrid_retriever.py, reranker.py
│   ├── generation/         # generator.py
│   ├── access_control/     # role_filter.py
│   └── api/                 # (planned)
├── eval/
│   ├── run_eval.py
│   └── results/             # eval_results.json (per-question outputs)
├── frontend/                 # (planned — Streamlit chat UI)
├── scripts/                  # one-off utility scripts (corpus splitting, debugging)
├── vectorstore/               # local Qdrant data (gitignored)
└── requirements.txt
```

## Setup

```bash
# clone and enter the repo
git clone https://github.com/nandininautiyal/onboard-rag.git
cd onboard-rag

# create and activate a virtual environment (Python 3.10 recommended)
python -m venv venv
.\venv\Scripts\Activate.ps1      # Windows PowerShell
# source venv/bin/activate       # macOS/Linux

# install dependencies
pip install -r requirements.txt

# install Ollama and pull the generation model
# see https://ollama.com/download
ollama pull llama3.1:8b
```

## Running the pipeline

```bash
# 1. Build the vector index from the document corpus
python -m src.embeddings.embed

# 2. Test retrieval directly (dense-only, hybrid, or reranked)
python -m src.retrieval.retriever
python -m src.retrieval.hybrid_retriever
python -m src.retrieval.reranker

# 3. Ask questions end-to-end (retrieval + rerank + grounded generation)
python -m src.generation.generator

# 4. Run the full evaluation suite against the QA test set
python -m eval.run_eval
```

`answer_query()` in `src/generation/generator.py` accepts an optional `user_role` argument (for example, `"engineering"`, `"sales"`, `"finance"`, `"manager"`) to demonstrate role-based access filtering; omitting it retrieves across the full corpus.

## Evaluation results

The pipeline was evaluated against all 38 questions in `data/qa_testset.json` (34 answerable, 4 deliberately unanswerable):

| Metric | Result |
|---|---|
| Retrieval hit rate (correct source document found, answerable questions) | 34/34 (100%) |
| Answer-attempt rate (system attempted an answer when it should have) | 32/34 (94.1%) |
| Correct refusal rate (system correctly declined on unanswerable questions) | 4/4 (100%) |

**Known limitation:** the two answerable questions the system incorrectly declined to answer ("What is the default laptop issued to new Techify hires?" and "What is Techify's daily meal per diem for domestic business travel?") both scored well below the confidence threshold at retrieval time. In both cases, the query phrasing diverged significantly from how the source document phrased the same information, and neither dense nor keyword search scored the correct chunk highly enough to clear the confidence threshold before generation. This is a genuine, instructive limitation of phrase-based retrieval rather than a pipeline bug, and a natural next step for improvement (see below).

**On hallucination resistance:** during evaluation, one case surfaced where the system correctly refused to answer, but a classification bug in the evaluation harness itself (not the RAG pipeline) initially miscounted a valid LLM-generated refusal as an "attempted answer." This was identified and fixed by having the harness check the actual answer text for refusal language, not only the retrieval-score-based early exit. The corrected run confirmed 100% correct refusal behavior.

## Known limitations and future work

- **Query-phrasing sensitivity**: as shown by the two retrieval misses above, questions phrased very differently from the source document's own language can still fall below the confidence threshold. Possible improvements: query rewriting/expansion before retrieval, or a lower threshold paired with stronger prompt-level grounding.
- **Confidence threshold tuning**: the current reranker-score threshold (0.4) was set from manual observation of score distributions rather than a formal sweep. A proper threshold sweep against the QA test set would likely improve the answer-attempt rate without harming refusal accuracy.
- **No frontend yet**: the project is currently script-driven. A lightweight Streamlit chat interface is planned to make the assistant demoable rather than requiring the command line.
- **Local model generation quirks**: the local model (`llama3.1:8b`) occasionally drops a space between words during generation (for example, rendering "your first day" as "yourfirst day"). This is a known small-model artifact, not a retrieval or grounding issue, and would likely not occur with a larger or hosted model.
- **RAGAS-style faithfulness scoring**: the current evaluation harness measures retrieval accuracy and refusal correctness directly; a deeper automated faithfulness/relevancy score (for example, via RAGAS) was intentionally deferred, since standard RAGAS tooling assumes an LLM-as-judge that is easiest to wire up against a paid API rather than a local model.

## Why this project

Built as a portfolio piece to demonstrate RAG engineering beyond a basic tutorial: heading-aware chunking, hybrid retrieval with reranking, metadata-based access control enforced at the retrieval layer, and a real evaluation methodology with honestly reported failure cases — plus a deliberate focus on hallucination resistance and cost-conscious local infrastructure, both relevant to an interest in AI security and applied ML engineering.