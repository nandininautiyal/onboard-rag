# Wayfinder (onboard-rag)

A Retrieval-Augmented Generation (RAG) system that helps new employees navigate company onboarding documentation through natural-language Q&A — instead of manually skimming dozens of policy and process docs.

> **Status: Work in progress.** Core naive RAG pipeline is functional end-to-end. Hybrid retrieval, reranking, access control, and evaluation are in progress — see [Roadmap](#roadmap).

## The problem

New hires get a firehose of onboarding material — HR policies, IT setup guides, engineering docs, sales processes — and have to dig through all of it to find answers to specific questions like "how many PTO days do I get" or "how do I request VPN access." Wayfinder lets them just ask.

## How it works

```
Company docs (Markdown, YAML frontmatter)
        ↓
   Ingestion (parse metadata + content)
        ↓
   Chunking (heading-aware, semantic — not fixed-size)
        ↓
   Embedding (sentence-transformers, local)
        ↓
   Vector store (Qdrant)
        ↓
[User query] → Dense retrieval → LLM generation (grounded, cited) → Answer
```

The system only answers from retrieved context, cites its sources, and is designed to say "I don't know" rather than hallucinate when a question falls outside the document corpus.

## Dataset

Since real company documents aren't available for a portfolio project, the corpus is a **synthetic company handbook** generated for a fictional company, "Techify" (~600 employees, B2B SaaS). It includes:

- **24 Markdown documents** across HR, IT/Security, Engineering, Sales, Marketing, Finance, General FAQ, and Org Info — each with YAML frontmatter (`doc_id`, `title`, `department`, `doc_type`, `last_updated`, `access_role`)
- **A 38-pair QA test set** (`data/qa_testset.json`) for evaluation, including single-document questions, multi-document questions, and intentionally unanswerable questions (to test hallucination resistance)
- A few documents are intentionally left slightly outdated or ambiguous, simulating the messiness of real internal documentation

## Tech stack

| Component | Tool |
|---|---|
| Ingestion | Custom Python parser (`python-frontmatter`) |
| Chunking | Custom heading-aware splitter + `langchain-text-splitters` for overflow |
| Embeddings | `sentence-transformers` (`BAAI/bge-small-en-v1.5`), local, free |
| Vector store | Qdrant (local, on-disk) |
| Retrieval | Dense (semantic) search, with `access_role` metadata filtering hook |
| Generation | Local LLM via [Ollama](https://ollama.com) (`llama3.1:8b`) — no API costs |
| Planned | BM25 hybrid search, cross-encoder reranking, RAGAS evaluation, Streamlit UI |

**Why a local LLM instead of a paid API:** Wayfinder is built to run entirely on local infrastructure — embeddings and generation both run on-device via `sentence-transformers` and Ollama, with zero inference cost. The generation call is isolated behind a single function (`call_llm()` in `src/generation/generator.py`), so swapping in a hosted API (Claude, GPT) later is a small, contained change rather than a rewrite — useful if quality/cost tradeoffs favor a hosted model down the line.

## Project structure

```
onboard-rag/
├── data/
│   ├── raw/              # 24 synthetic Techify onboarding docs (.md, frontmatter)
│   ├── processed/
│   ├── chunks/
│   └── qa_testset.json   # evaluation question-answer pairs
├── src/
│   ├── ingestion/         # loaders.py, chunker.py
│   ├── embeddings/        # embed.py
│   ├── retrieval/         # retriever.py
│   ├── generation/        # generator.py
│   ├── access_control/    # (planned)
│   └── api/                # (planned)
├── eval/                   # (planned) RAGAS harness + results
├── frontend/               # (planned) Streamlit chat UI
├── scripts/                # one-off utility scripts (corpus splitting, etc.)
├── vectorstore/            # local Qdrant data (gitignored)
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

# 2. Test retrieval directly
python -m src.retrieval.retriever

# 3. Ask questions end-to-end (retrieval + grounded generation)
python -m src.generation.generator
```

## Current capabilities

- ✅ Parses and chunks a real (synthetic) document corpus by semantic section, not arbitrary character counts
- ✅ Local, cost-free embedding and generation pipeline
- ✅ Dense semantic retrieval with strong precision on in-corpus questions
- ✅ Confidence-based fallback + prompt-level grounding to resist hallucination on out-of-corpus questions
- ✅ Source citations on every generated answer

## Roadmap

- [ ] **Hybrid retrieval** — combine dense (semantic) search with BM25 (keyword) search, since new hires often search exact terms ("VPN setup") that pure semantic search can miss
- [ ] **Reranking** — add a cross-encoder (`bge-reranker-base`) to rerank top-20 candidates into a more precise top-5
- [ ] **Role-based access control** — filter retrieval by department/role so, e.g., a Sales hire can't retrieve Finance-only documents (metadata hook already in place in `retriever.py`)
- [ ] **Evaluation harness** — run the full `qa_testset.json` through the pipeline and measure retrieval precision/recall and answer faithfulness using RAGAS, with before/after comparisons across each improvement above
- [ ] **Frontend** — lightweight Streamlit chat interface
- [ ] Architecture diagram and full eval results in this README

## Why this project

Built as a portfolio piece to demonstrate RAG engineering beyond a basic tutorial: heading-aware chunking, hybrid retrieval + reranking, metadata-based access control, and a real evaluation methodology — plus a deliberate focus on hallucination resistance and cost-conscious local infrastructure, both relevant to my interest in AI security and applied ML engineering.