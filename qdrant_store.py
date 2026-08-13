import re

from qdrant_client import QdrantClient, models


def normalize_collection_component(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("collection component must be a non-blank string")

    normalized = re.sub(r"[^a-z0-9_]+", "_", value.lower())
    normalized = re.sub(r"_+", "_", normalized).strip("_")

    if not normalized:
        raise ValueError("collection component must contain letters or numbers")

    return normalized


def build_collection_name(provider_name, model_name):
    normalized_provider = normalize_collection_component(provider_name)
    normalized_model = normalize_collection_component(model_name)
    return f"rag_chunks_{normalized_provider}_{normalized_model}"


def build_vector_reference(collection_name, point_id):
    return f"{collection_name}:{point_id}"


def create_qdrant_client(url, api_key=None):
    return QdrantClient(url=url, api_key=api_key)


class QdrantStore:
    def __init__(self, client):
        self._client = client

    def ensure_collection(self, collection_name, vector_size, distance):
        if self._client.collection_exists(collection_name):
            return

        self._client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=vector_size,
                distance=distance,
            ),
        )

    def upsert_chunk_embedding(
        self,
        collection_name,
        document_chunk_id,
        document_version_id,
        chunk_content,
        vector,
    ):
        point = models.PointStruct(
            id=document_chunk_id,
            vector=vector,
            payload={
                "document_chunk_id": document_chunk_id,
                "document_version_id": document_version_id,
                "chunk_content": chunk_content,
            },
        )

        self._client.upsert(
            collection_name=collection_name,
            points=[point],
            wait=True,
        )
