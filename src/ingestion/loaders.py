"""
loaders.py

Reads all markdown documents from data/raw/, parses their YAML frontmatter
(doc_id, title, department, doc_type, last_updated, access_role) and body
content, and returns a list of structured Document objects for downstream
chunking.
"""

import glob
import os
from dataclasses import dataclass, field

import frontmatter


@dataclass
class Document:
    doc_id: str
    title: str
    department: str
    doc_type: str
    last_updated: str
    access_role: str
    content: str
    filepath: str


def load_documents(raw_dir: str = "data/raw") -> list[Document]:
    """
    Load and parse every .md file in raw_dir into a Document object.
    Skips files that fail to parse, printing a warning instead of crashing
    the whole pipeline (useful since this corpus was LLM-generated and may
    have occasional formatting quirks).
    """
    documents = []
    md_paths = sorted(glob.glob(os.path.join(raw_dir, "*.md")))

    if not md_paths:
        print(f"WARNING: No .md files found in {raw_dir}")
        return documents

    for path in md_paths:
        try:
            post = frontmatter.load(path)
            metadata = post.metadata
            content = post.content.strip()

            doc = Document(
                doc_id=metadata.get("doc_id", os.path.splitext(os.path.basename(path))[0]),
                title=metadata.get("title", "Untitled"),
                department=metadata.get("department", "Unknown"),
                doc_type=metadata.get("doc_type", "Unknown"),
                last_updated=str(metadata.get("last_updated", "")),
                access_role=metadata.get("access_role", "all"),
                content=content,
                filepath=path,
            )
            documents.append(doc)

        except Exception as e:
            print(f"WARNING: Failed to parse {path}: {e}")
            continue

    print(f"Loaded {len(documents)} documents from {raw_dir}")
    return documents


if __name__ == "__main__":
    docs = load_documents()
    for doc in docs[:3]:
        print(f"\n--- {doc.doc_id} ---")
        print(f"Title: {doc.title}")
        print(f"Department: {doc.department} | Type: {doc.doc_type} | Access: {doc.access_role}")
        print(f"Content preview: {doc.content[:150]}...")