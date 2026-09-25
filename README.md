# RAG Chatbot

A real document-grounded RAG chatbot built with Flask, BGE-M3, Qdrant, LlamaIndex chunking, and the current `google-genai` SDK.

## Architecture

PDF / DOCX / TXT
→ Parser
→ LlamaIndex SentenceSplitter
→ BGE-M3 embeddings
→ Qdrant
→ similarity retrieval
→ Gemini
→ grounded answer + sources
→ browser UI

## Important

This project uses **LlamaIndex only for chunking** through `SentenceSplitter`.

**LangChain is not used.**

## Project structure

```text
RAG-CHATBOT/
├── app.py
├── rag.py
├── document_processor.py
├── embeddings.py
├── config.py
├── templates/
│   └── index.html
├── static/
│   ├── style.css
│   └── script.js
├── documents/
├── qdrant_storage/
├── .env
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## Requirements

- Python 3.10+ recommended
- Gemini API key
- Internet connection for Gemini and the first BGE-M3 model download
- Qdrant can run locally using the included persistent `qdrant_storage/` directory, so Qdrant Cloud is optional.

## Setup

### 1. Create a virtual environment

Windows:

```text
python -m venv .venv
.venv\Scripts\activate
```

### 2. Install packages

```text
pip install -r requirements.txt
```

### 3. Create `.env`

Copy `.env.example` to `.env` and fill in:

```env
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-3.1-flash-lite

QDRANT_URL=
QDRANT_API_KEY=
QDRANT_COLLECTION=rag_documents

EMBEDDING_MODEL=BAAI/bge-m3

CHUNK_SIZE=800
CHUNK_OVERLAP=100
TOP_K=5

FLASK_SECRET_KEY=some_random_secret
```

Never put the Gemini key in JavaScript or commit `.env`.

## Qdrant local mode

The default configuration uses local persistent Qdrant:

```env
QDRANT_URL=
QDRANT_API_KEY=
```

Vectors are stored in:

```text
qdrant_storage/
```

For Qdrant Cloud, set:

```env
QDRANT_URL=https://your-cluster-url
QDRANT_API_KEY=your_qdrant_key
```

## Run locally

```text
python app.py
```

Open:

```text
http://127.0.0.1:5000
```

## Use the chatbot

1. Upload a PDF, DOCX, or TXT file.
2. Wait for the indexing message.
3. Ask a question that is answered by the document.
4. Check the source and page shown below the answer.
5. Ask an unrelated question. The assistant should say that the information was not found in the uploaded documents.

## Delete a document

Click the `✕` button next to a document. This removes its vectors from Qdrant and removes its local metadata file.

## New Chat

The `New Chat` button clears only the browser chat interface. It does not delete indexed documents or vectors.

## Gunicorn deployment

Linux/server example:

```text
gunicorn --bind 0.0.0.0:8000 app:app
```

Set the required `.env` variables in the deployment environment.

## Troubleshooting

### Gemini configuration is missing

Check that `GEMINI_API_KEY` exists in `.env`.

### Vector database connection failed

For local mode, make sure the application can write to `qdrant_storage/`.

For Cloud mode, check `QDRANT_URL` and `QDRANT_API_KEY`.

### Document has no readable text

The file may be image-only/scanned or otherwise contain no extractable text. This implementation does not perform OCR.

### First run is slow

BGE-M3 is a real embedding model and may need to download model files the first time. It is then loaded once and reused by the application.

### Gemini cannot answer

Make sure the question is related to the uploaded document and that the document was indexed successfully.

## Security

- Secrets are loaded from `.env`.
- `.env` is ignored by Git.
- Uploads are limited to PDF/DOCX/TXT.
- Filenames are sanitized.
- API credentials never go to the browser.
- Backend errors are returned without Python tracebacks.
