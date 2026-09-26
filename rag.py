import json
import os
import uuid
from pathlib import Path

from google import genai
from google.genai import types
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams, Filter, FieldCondition, MatchValue

from document_processor import process_document
from embeddings import GeminiEmbeddings


class RAGEngine:
    def __init__(self, config):
        self.config = config

        # Connect directly to Qdrant Cloud
        self.qdrant = QdrantClient(
            url=config["qdrant_url"],
            port=config.get("qdrant_port"),
            api_key=config["qdrant_api_key"],
            timeout=config.get("qdrant_timeout", 60),
        )

        self.embeddings = GeminiEmbeddings(
            api_key=config["gemini_api_key"],
            model_name=config.get("embedding_model", "gemini-embedding-001"),
            dimension=384,
        )
        self.gemini = genai.Client(api_key=config["gemini_api_key"])
        self.collection = config["qdrant_collection"]

        self._ensure_collection()

    def _ensure_collection(self):
        existing = {c.name for c in self.qdrant.get_collections().collections}
        if self.collection not in existing:
            self.qdrant.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(
                    size=self.embeddings.dimension(),
                    distance=Distance.COSINE,
                ),
            )

        # Create keyword index for document_id
        try:
            self.qdrant.create_payload_index(
                collection_name=self.collection,
                field_name="document_id",
                field_schema="keyword",
            )
        except Exception as e:
            print("document_id index check:", e)

    def index_uploaded_file(self, file, filename):
        data = file.read()
        if not data:
            raise ValueError("The uploaded document is empty.")

        document_id = __import__("hashlib").sha256(data).hexdigest()

        # Stable hash prevents the same file from being indexed repeatedly.
        existing = self.qdrant.scroll(
            collection_name=self.collection,
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=document_id),
                    )
                ]
            ),
            limit=1,
            with_payload=False,
            with_vectors=False,
        )
        if existing[0]:
            return {
                "message": "This document is already indexed.",
                "document_id": document_id,
                "filename": filename,
                "duplicate": True,
            }

        processed = process_document(
            data,
            filename,
            self.config["chunk_size"],
            self.config["chunk_overlap"],
        )
        vectors = self.embeddings.encode([c["text"] for c in processed["chunks"]])

        points = []
        for chunk, vector in zip(processed["chunks"], vectors):
            points.append(
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vector,
                    payload=chunk,
                )
            )

        self.qdrant.upsert(
            collection_name=self.collection,
            points=points,
        )

        Path("documents").mkdir(exist_ok=True)
        with open(Path("documents") / f"{document_id}.json", "w", encoding="utf-8") as f:
            json.dump(
                {
                    "document_id": document_id,
                    "filename": filename,
                    "file_type": processed["file_type"],
                    "chunk_count": len(points),
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

        return {
            "message": f"{filename} indexed successfully.",
            "document_id": document_id,
            "filename": filename,
            "chunks": len(points),
            "duplicate": False,
        }

    def list_documents(self):
        result = []
        documents_dir = Path("documents")
        documents_dir.mkdir(exist_ok=True)

        for path in documents_dir.glob("*.json"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    result.append(json.load(f))
            except (OSError, json.JSONDecodeError):
                continue

        return sorted(result, key=lambda x: x.get("filename", "").lower())

    def delete_document(self, document_id):
        deleted = self.qdrant.delete(
            collection_name=self.collection,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=document_id),
                    )
                ]
            ),
        )

        metadata_file = Path("documents") / f"{document_id}.json"
        if metadata_file.exists():
            metadata_file.unlink()

        return {"message": "Document deleted.", "document_id": document_id}

    def answer(self, question):
        if not self.list_documents():
            raise ValueError("Please upload a document before asking questions.")

        query_vector = self.embeddings.encode(question)[0]

        hits = self.qdrant.query_points(
            collection_name=self.collection,
            query=query_vector,
            limit=self.config["top_k"],
            with_payload=True,
        ).points

        if not hits:
            return {
                "answer": "I couldn't find this information in the uploaded documents.",
                "sources": [],
            }

        context_parts = []
        sources = []
        for i, hit in enumerate(hits, start=1):
            payload = hit.payload or {}
            page = payload.get("page")
            source = payload.get("source", "Unknown")
            page_text = f" — Page {page}" if page else ""
            context_parts.append(
                f"[Context {i}] Source: {source}{page_text}\n{payload.get('text', '')}"
            )
            sources.append({
                "source": source,
                "page": page,
                "score": round(float(hit.score), 4),
            })

        context = "\n\n".join(context_parts)

        system_instruction = """You are a document-grounded AI assistant.
Answer the user's question using the provided retrieved document context.

Rules:
1. Use the retrieved context as the primary and required source.
2. Do not invent facts that are not supported by the context.
3. If the answer cannot be found in the retrieved context, say exactly:
"I couldn't find this information in the uploaded documents."
4. Do not pretend that information exists in the documents when it does not.
5. Give concise, useful answers.
6. When appropriate, mention the source document and page number.
"""

        prompt = f"""Retrieved document context:
{context}

User question:
{question}
"""

        models_to_try = [
            self.config.get("gemini_model", "gemini-3.5-flash-lite"),
            "gemini-3.5-flash-lite",
            "gemma-4-26b-a4b-it",
            "gemma-4-31b-it",
            "gemini-3.5-flash",
            "gemini-flash-latest",
        ]
        # Deduplicate while preserving order
        models_to_try = list(dict.fromkeys(models_to_try))

        response = None
        last_error = None
        for model_name in models_to_try:
            try:
                response = self.gemini.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.2,
                    ),
                )
                if response and response.text:
                    break
            except Exception as e:
                last_error = e
                __import__("time").sleep(1)
                continue

        if response is None or not (response.text or "").strip():
            if last_error:
                raise RuntimeError(f"Gemini API error across attempted models: {last_error}")
            answer = "I couldn't find this information in the uploaded documents."
        else:
            answer = response.text.strip()

        return {"answer": answer, "sources": sources}
