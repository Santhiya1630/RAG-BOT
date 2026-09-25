from fastembed import TextEmbedding


class BGEEmbeddings:
    """Lightweight embedding wrapper using FastEmbed."""

    def __init__(self, model_name):
        self.model = TextEmbedding(
            model_name=model_name
        )

    def encode(self, texts):
        if isinstance(texts, str):
            texts = [texts]

        vectors = list(self.model.embed(texts))
        return [vector.tolist() for vector in vectors]

    def dimension(self):
        return 384
