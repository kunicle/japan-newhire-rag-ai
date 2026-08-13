SUPPORTED_PROVIDER = "openai"
SUPPORTED_MODEL = "text-embedding-3-small"
EXPECTED_DIMENSION = 1536


class EmbeddingService:
    def __init__(self, client):
        self._client = client

    def embed_document(self, provider_name, model_name, text):
        return self._embed(provider_name, model_name, text)

    def embed_query(self, provider_name, model_name, text):
        return self._embed(provider_name, model_name, text)

    def _embed(self, provider_name, model_name, text):
        if provider_name != SUPPORTED_PROVIDER:
            raise ValueError(f"unsupported embedding provider: {provider_name}")

        if model_name != SUPPORTED_MODEL:
            raise ValueError(f"unsupported embedding model: {model_name}")

        if not isinstance(text, str) or not text.strip():
            raise ValueError("embedding text must be a non-blank string")

        response = self._client.embeddings.create(
            model=model_name,
            input=text,
            encoding_format="float",
        )

        data = getattr(response, "data", None)
        if not data:
            raise ValueError("embedding response contains no data")

        vector = getattr(data[0], "embedding", None)
        if not vector:
            raise ValueError("embedding response contains no vector")

        if len(vector) != EXPECTED_DIMENSION:
            raise ValueError(
                f"embedding dimension mismatch: expected {EXPECTED_DIMENSION}, "
                f"got {len(vector)}"
            )

        return vector
