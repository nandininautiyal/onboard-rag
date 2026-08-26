"""
embed.py

Embeds all chunks produced by the ingestion pipeline using a local
sentence-transformers model, and pushes them into a Qdrant collection
along with their metadata (doc_id, department, access_role, section
heading, etc.) so later retrieval can filter on these fields.

Requires a running Qdrant instance. Easiest local option is Docker:

    docker run -p 6333:6333 -v ${PWD}/vectorstore:/qdrant/storage qdrant/qdrant

If you don't have Docker set up yet, this script also supports an
in-memory / on-disk local mode via QdrantClient(path=...), which needs
no Docker at all — see USE_LOCAL_FILE_MODE below.
"""

from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import uuid

from ..ingestion.loaders import load_documents
from ..ingestion.chunker import chunk_all_documents

# ---- Config ----
EMBEDDING_MODEL_NAME = "BAAI/bge-small-en-v1.5"
COLLECTION_NAME = "techify_onboarding_docs"

# If True, uses a local on-disk Qdrant (no Docker/server needed).
# If False, connects to a Qdrant server running at localhost:6333.
USE_LOCAL_FILE_MODE = True
LOCAL_QDRANT_PATH = "vectorstore/qdrant_local"


def get_qdrant_client() -> QdrantClient:
    if USE_LOCAL_FILE_MODE:
        return QdrantClient(path=LOCAL_QDRANT_PATH)
    else:
        return QdrantClient(host="localhost", port=6333)


def build_index():
    print(f"Loading embedding model: {EMBEDDING_MODEL_NAME} ...")
    model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    vector_size = model.get_sentence_embedding_dimension()

    print("Loading and chunking documents ...")
    documents = load_documents()
    chunks = chunk_all_documents(documents)

    print(f"Embedding {len(chunks)} chunks ...")
    texts = [chunk.text for chunk in chunks]
    embeddings = model.encode(texts, show_progress_bar=True, normalize_embeddings=True)

    client = get_qdrant_client()

    # Recreate collection fresh each time we reindex
    if client.collection_exists(COLLECTION_NAME):
        client.delete_collection(COLLECTION_NAME)

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
    )

    points = []
    for chunk, vector in zip(chunks, embeddings):
        points.append(
            PointStruct(
                id=str(uuid.uuid4()),
                vector=vector.tolist(),
                payload={
                    "chunk_id": chunk.chunk_id,
                    "doc_id": chunk.doc_id,
                    "title": chunk.title,
                    "department": chunk.department,
                    "doc_type": chunk.doc_type,
                    "last_updated": chunk.last_updated,
                    "access_role": chunk.access_role,
                    "section_heading": chunk.section_heading,
                    "text": chunk.text,
                },
            )
        )

    client.upsert(collection_name=COLLECTION_NAME, points=points)
    print(f"Indexed {len(points)} chunks into Qdrant collection '{COLLECTION_NAME}'")

    return client, model


if __name__ == "__main__":
    build_index()
    print("\nDone. Run a test query with src/retrieval/retriever.py next.")