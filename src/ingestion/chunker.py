"""
chunker.py

Splits each Document's content into semantic chunks based on markdown
headings (## sections), rather than fixed-size character splitting.
Each chunk retains the parent document's metadata plus the section
heading it came from, so later stages can cite "Carryover section of
the Leave Policy" rather than just a raw doc_id.

If a single section is very long, it gets further split using
RecursiveCharacterTextSplitter with overlap, so no chunk is too large
for the embedding model's context window.
"""

import re
import uuid
from dataclasses import dataclass, field

from langchain_text_splitters import RecursiveCharacterTextSplitter

from .loaders import Document, load_documents

# Max characters per chunk before we further split within a section.
MAX_CHUNK_CHARS = 1000
CHUNK_OVERLAP = 150


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    title: str
    department: str
    doc_type: str
    last_updated: str
    access_role: str
    section_heading: str
    text: str


def split_by_headings(content: str) -> list[tuple[str, str]]:
    """
    Split markdown content into (heading, section_text) pairs based on
    '## ' headings. Content before the first heading (if any) is kept
    under an "Overview" pseudo-heading.
    """
    # Split on lines starting with "## " (level-2 headings), keeping the heading text
    pattern = re.compile(r"^##\s+(.*)$", re.MULTILINE)

    matches = list(pattern.finditer(content))

    if not matches:
        # No headings at all — treat the whole doc as one section
        return [("General", content.strip())]

    sections = []

    # Anything before the first heading
    if matches[0].start() > 0:
        preamble = content[: matches[0].start()].strip()
        if preamble:
            sections.append(("Overview", preamble))

    for i, match in enumerate(matches):
        heading = match.group(1).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        section_text = content[start:end].strip()
        if section_text:
            sections.append((heading, section_text))

    return sections


def chunk_document(doc: Document) -> list[Chunk]:
    """
    Convert a single Document into a list of Chunks, one per section
    (further split if a section is too long).
    """
    chunks = []
    sections = split_by_headings(doc.content)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=MAX_CHUNK_CHARS,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    for heading, section_text in sections:
        if len(section_text) <= MAX_CHUNK_CHARS:
            sub_texts = [section_text]
        else:
            sub_texts = splitter.split_text(section_text)

        for sub_text in sub_texts:
            chunk = Chunk(
                chunk_id=str(uuid.uuid4()),
                doc_id=doc.doc_id,
                title=doc.title,
                department=doc.department,
                doc_type=doc.doc_type,
                last_updated=doc.last_updated,
                access_role=doc.access_role,
                section_heading=heading,
                text=sub_text.strip(),
            )
            chunks.append(chunk)

    return chunks


def chunk_all_documents(documents: list[Document]) -> list[Chunk]:
    all_chunks = []
    for doc in documents:
        doc_chunks = chunk_document(doc)
        all_chunks.extend(doc_chunks)
    print(f"Created {len(all_chunks)} chunks from {len(documents)} documents")
    return all_chunks


if __name__ == "__main__":
    docs = load_documents()
    chunks = chunk_all_documents(docs)

    # Preview a few chunks
    for chunk in chunks[:5]:
        print(f"\n--- {chunk.doc_id} | {chunk.section_heading} ---")
        print(f"Chars: {len(chunk.text)}")
        print(f"Text preview: {chunk.text[:150]}...")

    # Quick sanity stats
    avg_len = sum(len(c.text) for c in chunks) / len(chunks)
    print(f"\nTotal chunks: {len(chunks)}")
    print(f"Average chunk length: {avg_len:.0f} characters")