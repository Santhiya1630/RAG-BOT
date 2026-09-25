from pathlib import Path
import hashlib
import io

import pymupdf as fitz
from docx import Document
from llama_index.core.node_parser import SentenceSplitter


ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}


def document_id_from_bytes(data):
    return hashlib.sha256(data).hexdigest()


def _clean(text):
    lines = [line.strip() for line in text.replace("\x00", "").splitlines()]
    return "\n".join(line for line in lines if line).strip()


def _pdf_pages(data):
    pages = []
    with fitz.open(stream=data, filetype="pdf") as pdf:
        for page_number, page in enumerate(pdf, start=1):
            text = _clean(page.get_text("text"))
            if text:
                pages.append({"text": text, "page": page_number})
    return pages


def _docx_text(data):
    doc = Document(io.BytesIO(data))
    paragraphs = [_clean(p.text) for p in doc.paragraphs if _clean(p.text)]
    text = "\n".join(paragraphs)

    # Tables are also useful document content.
    for table in doc.tables:
        rows = []
        for row in table.rows:
            rows.append(" | ".join(_clean(cell.text) for cell in row.cells))
        table_text = "\n".join(r for r in rows if r.strip())
        if table_text:
            text += ("\n" if text else "") + table_text

    return [{"text": _clean(text), "page": None}] if text.strip() else []


def _txt_text(data):
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = data.decode("utf-8", errors="replace")
    text = _clean(text)
    return [{"text": text, "page": None}] if text else []


def process_document(data, filename, chunk_size=800, chunk_overlap=100):
    ext = Path(filename).suffix.lower().lstrip(".")
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError("Only PDF, DOCX, and TXT files are allowed.")

    document_id = document_id_from_bytes(data)

    if ext == "pdf":
        page_parts = _pdf_pages(data)
    elif ext == "docx":
        page_parts = _docx_text(data)
    else:
        page_parts = _txt_text(data)

    if not page_parts:
        raise ValueError("The uploaded document does not contain readable text.")

    splitter = SentenceSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    chunks = []
    chunk_index = 0

    for part in page_parts:
        nodes = splitter.split_text(part["text"])
        for node_text in nodes:
            cleaned = _clean(node_text)
            if not cleaned:
                continue
            chunks.append({
                "text": cleaned,
                "source": filename,
                "file_type": ext,
                "page": part["page"],
                "chunk_index": chunk_index,
                "document_id": document_id,
            })
            chunk_index += 1

    if not chunks:
        raise ValueError("The uploaded document does not contain readable text.")

    return {
        "document_id": document_id,
        "filename": filename,
        "file_type": ext,
        "chunks": chunks,
    }
