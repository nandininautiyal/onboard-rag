# onboard-rag

A Retrieval-Augmented Generation (RAG) system that lets new employees ask natural-language questions across company onboarding documentation, instead of manually reading through dozens of policy and process documents.

The system retrieves relevant document sections using hybrid (semantic + keyword) search, reranks them for precision, and generates grounded, cited answers — enforcing role-based access to documents and explicitly declining to answer questions the corpus doesn't cover.

## Architecture

```
                              ┌────────────────────────┐
                              │     Document Corpus     │
                              │  (Markdown + frontmatter)│
                              └────────────┬────────────┘
                                           │
                                           ▼
                              ┌────────────────────────┐
                              │        Ingestion         │
                              │  parse metadata + text   │
                              └────────────┬────────────┘
                                           │
                                           ▼
                              ┌────────────────────────┐
                              │        Chunking          │
                              │  heading-aware, semantic │
                              └────────────┬────────────┘
                                           │
                                           ▼
                              ┌────────────────────────┐
                              │       Embedding           │
                              │  sentence-transformers    │
                              └────────────┬────────────┘
                                           │
                                           ▼
                              ┌────────────────────────┐
                              │     Vector Store (Qdrant) │
                              └────────────┬────────────┘
                                           │
                        ══════════════ query time ══════════════
                                           │
                                           ▼
                              ┌────────────────────────┐
                              │  Role-Based Access Filter │
                              │  (restrict by employee    │
                              │   role before retrieval)  │
                              └────────────┬────────────┘
                                           │
                                           ▼
                     ┌─────────────────────┴─────────────────────┐
                     ▼                                           ▼
          ┌────────────────────┐                     ┌────────────────────┐
          │   Dense Retrieval    │                     │   Sparse Retrieval  │
          │  (semantic search)   │                     │   (BM25 keyword)    │
          └──────────┬──────────┘                     └──────────┬──────────┘
                     └─────────────────┬─────────────────────────┘
                                       ▼
                          ┌────────────────────────┐
                          │  Reciprocal Rank Fusion  │
                          └────────────┬────────────┘
                                       ▼
                          ┌────────────────────────┐
                          │   Cross-Encoder Reranking │
                          │   (top-20 → top-5)         │
                          └────────────┬────────────┘
                                       ▼
                          ┌────────────────────────┐
                          │     Confidence Check       │
                          └────────────┬────────────┘
                                       ▼
                          ┌────────────────────────┐
                          │  Grounded Generation (LLM) │
                          │   with source citations    │
                          └────────────┬────────────┘
                                       ▼
                          ┌────────────────────────┐
                          │   Answer, or explicit      │
                          │   "not covered" response   │
                          └────────────────────────┘
```

**Key design principles:**
- **Hybrid retrieval** — combines semantic (dense) and keyword (BM25) search via Reciprocal Rank Fusion, so exact terms and product names are matched as reliably as conceptual queries.
- **Reranking** — a cross-encoder re-scores the top candidates against the query directly, producing far more accurate relevance ordering than retrieval alone.
- **Access control at the retrieval layer** — documents are filtered by the requesting employee's role before reranking or generation, so restricted content never reaches the language model.
- **Grounded generation** — the model is instructed to answer only from retrieved context and to explicitly decline when the corpus doesn't contain the answer, rather than guessing.

## Project structure

```
onboard-rag/
├── data/
│   ├── raw/               # source documents (.md, YAML frontmatter)
│   ├── processed/
│   ├── chunks/
│   └── qa_testset.json    # evaluation question-answer pairs
├── src/
│   ├── ingestion/          # document loading and parsing
│   ├── embeddings/         # embedding generation and vector indexing
│   ├── retrieval/          # dense, hybrid, and reranking logic
│   ├── generation/         # grounded answer generation
│   └── access_control/     # role-based retrieval filtering
├── eval/
│   ├── run_eval.py         # evaluation harness
│   └── results/            # evaluation outputs
├── frontend/                # (planned) chat interface
├── scripts/                  # utility scripts
├── vectorstore/               # local vector store data (gitignored)
└── requirements.txt
```

## Setup and usage

```bash
# clone the repository
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

Run the pipeline:

```bash
# build the vector index from the document corpus
python -m src.embeddings.embed

# test retrieval directly
python -m src.retrieval.retriever
python -m src.retrieval.hybrid_retriever
python -m src.retrieval.reranker

# ask questions end-to-end (retrieval, reranking, and grounded generation)
python -m src.generation.generator

# run the evaluation suite
python -m eval.run_eval
```

`answer_query()` in `src/generation/generator.py` accepts an optional `user_role` argument (for example, `"engineering"`, `"sales"`, `"finance"`, `"manager"`) to demonstrate role-based access filtering; omitting it retrieves across the full corpus.