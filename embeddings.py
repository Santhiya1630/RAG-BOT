import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()


class GeminiEmbeddings:
    """Lightweight cloud-based embedding wrapper using Gemini API.

    Zero local PyTorch/CUDA dependencies, minimal RAM usage (< 30 MB),
    and fast inference fitting easily into Render's 512 MB free tier.
    """

    def __init__(self, api_key: str = None, model_name: str = "gemini-embedding-001", dimension: int = 384):
        # Gracefully handle model_name passed as first positional arg for backwards compatibility
        if api_key and (api_key.startswith("gemini-") or api_key.startswith("models/") or "minilm" in api_key.lower()):
            model_name = "gemini-embedding-001" if "minilm" in api_key.lower() else api_key
            api_key = os.getenv("GEMINI_API_KEY")
        elif not api_key:
            api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError("GEMINI_API_KEY is required for GeminiEmbeddings.")

        if "minilm" in str(model_name).lower():
            model_name = "gemini-embedding-001"

        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name or "gemini-embedding-001"
        self._dimension = dimension

    def encode(self, texts):
        if isinstance(texts, str):
            texts = [texts]

        if not texts:
            return []

        vectors = []
        batch_size = 50
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            response = self.client.models.embed_content(
                model=self.model_name,
                contents=batch,
                config=types.EmbedContentConfig(output_dimensionality=self._dimension),
            )
            for emb in response.embeddings:
                vectors.append(emb.values)

        return vectors

    def dimension(self):
        return self._dimension


# Backward compatibility alias
BGEEmbeddings = GeminiEmbeddings