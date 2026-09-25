from sentence_transformers import SentenceTransformer


class BGEEmbeddings:
    """Embedding wrapper using Sentence Transformers."""

    def __init__(self, model_name):
        self.model = SentenceTransformer(model_name)

    def encode(self, texts):
        if isinstance(texts, str):
            texts = [texts]

        vectors = self.model.encode(
            texts,
            normalize_embeddings=True
        )

        return vectors.tolist()

    def dimension(self):
        return 384
