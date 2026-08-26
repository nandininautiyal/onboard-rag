import re
import os

RAW_TXT_PATH = "data/raw/techify_onboarding_corpus.txt"
OUTPUT_DOC_DIR = "data/raw"
QA_OUTPUT_PATH = "data/qa_testset.json"

def split_docs(raw_text):
    doc_blocks = re.findall(r"===DOC_START===(.*?)===DOC_END===", raw_text, re.DOTALL)
    return doc_blocks

def parse_doc(block):
    block = block.strip()
    # Split metadata header from body using the "---" line
    parts = block.split("---", 1)
    if len(parts) != 2:
        raise ValueError("Doc block missing '---' separator between metadata and content")

    meta_lines = parts[0].strip().splitlines()
    content = parts[1].strip()

    meta = {}
    for line in meta_lines:
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip().upper()] = value.strip()

    return meta, content

def write_doc_file(meta, content):
    doc_id = meta.get("DOC_ID", "unknown_doc")
    filepath = os.path.join(OUTPUT_DOC_DIR, f"{doc_id}.md")

    frontmatter = (
        "---\n"
        f"doc_id: {meta.get('DOC_ID', '')}\n"
        f"title: {meta.get('TITLE', '')}\n"
        f"department: {meta.get('DEPARTMENT', '')}\n"
        f"doc_type: {meta.get('DOC_TYPE', '')}\n"
        f"last_updated: {meta.get('LAST_UPDATED', '')}\n"
        f"access_role: {meta.get('ACCESS_ROLE', '')}\n"
        "---\n\n"
    )

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(frontmatter + content + "\n")

    print(f"Wrote {filepath}")

def extract_qa_section(raw_text):
    match = re.search(r"===QA_TESTSET_START===(.*?)===QA_TESTSET_END===", raw_text, re.DOTALL)
    if not match:
        print("WARNING: QA testset section not found.")
        return None
    return match.group(1).strip()

def main():
    with open(RAW_TXT_PATH, "r", encoding="utf-8") as f:
        raw_text = f.read()

    doc_blocks = split_docs(raw_text)
    print(f"Found {len(doc_blocks)} documents.")

    for block in doc_blocks:
        meta, content = parse_doc(block)
        write_doc_file(meta, content)

    qa_json_text = extract_qa_section(raw_text)
    if qa_json_text:
        os.makedirs(os.path.dirname(QA_OUTPUT_PATH), exist_ok=True)
        with open(QA_OUTPUT_PATH, "w", encoding="utf-8") as f:
            f.write(qa_json_text)
        print(f"Wrote {QA_OUTPUT_PATH}")

if __name__ == "__main__":
    main()