from sentence_transformers import SentenceTransformer


class BGEEmbeddings:
    """Lightweight embedding wrapper for all-MiniLM-L6-v2."""

    def __init__(self, model_name):
        self.model = SentenceTransformer(
            model_name,
            device="cpu"
        )

    def encode(self, texts):
        if isinstance(texts, str):
            texts = [texts]

        vectors = self.model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
            batch_size=1
        )

        return vectors.tolist()

    def dimension(self):
        if hasattr(self.model, "get_embedding_dimension"):
            return self.model.get_embedding_dimension()

        return self.model.get_sentence_embedding_dimension()
