import re
from dataclasses import dataclass

from qdrant_client import QdrantClient, models


@dataclass(frozen=True)
class QdrantChunkSearchResult:
    document_chunk_id: int
    document_version_id: int
    chunk_content: str
    score: float


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

    def search_chunks(
        self,
        collection_name,
        query_vector,
        allowed_document_version_ids,
        limit,
    ):
        if not self._client.collection_exists(collection_name):
            return []

        response = self._client.query_points(
            collection_name=collection_name,
            query=query_vector,
            query_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="document_version_id",
                        match=models.MatchAny(any=allowed_document_version_ids),
                    )
                ]
            ),
            limit=limit,
            with_payload=True,
            with_vectors=False,
            score_threshold=0.0,
        )

        return [self._map_search_result(point) for point in response.points]

    @staticmethod
    def _map_search_result(point):
        payload = point.payload
        if not isinstance(payload, dict):
            raise ValueError("Qdrant search result payload is malformed")

        document_chunk_id = payload.get("document_chunk_id")
        document_version_id = payload.get("document_version_id")
        chunk_content = payload.get("chunk_content")
        score = point.score

        if not isinstance(document_chunk_id, int) or isinstance(
            document_chunk_id, bool
        ):
            raise ValueError("Qdrant search result payload is malformed")
        if not isinstance(document_version_id, int) or isinstance(
            document_version_id, bool
        ):
            raise ValueError("Qdrant search result payload is malformed")
        if not isinstance(chunk_content, str):
            raise ValueError("Qdrant search result payload is malformed")
        if not isinstance(score, (int, float)) or isinstance(score, bool):
            raise ValueError("Qdrant search result score is malformed")

        return QdrantChunkSearchResult(
            document_chunk_id=document_chunk_id,
            document_version_id=document_version_id,
            chunk_content=chunk_content,
            score=score,
        )
