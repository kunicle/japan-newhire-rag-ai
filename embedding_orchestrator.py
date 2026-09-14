from dataclasses import dataclass

from qdrant_store import build_collection_name, build_vector_reference


@dataclass(frozen=True)
class EmbeddingOrchestrationResult:
    vector_reference: str
    embedding_dimension: int


class EmbeddingOrchestrator:
    def __init__(self, embedding_service, qdrant_store, distance):
        self._embedding_service = embedding_service
        self._qdrant_store = qdrant_store
        self._distance = distance

    def process(
        self,
        document_chunk_id,
        document_version_id,
        chunk_content,
        provider_name,
        model_name,
    ):
        vector = self._embedding_service.embed_document(
            provider_name,
            model_name,
            chunk_content,
        )
        embedding_dimension = len(vector)
        collection_name = build_collection_name(provider_name, model_name)

        self._qdrant_store.ensure_collection(
            collection_name,
            vector_size=embedding_dimension,
            distance=self._distance,
        )
        self._qdrant_store.upsert_chunk_embedding(
            collection_name,
            document_chunk_id,
            document_version_id,
            chunk_content,
            vector,
        )

        return EmbeddingOrchestrationResult(
            vector_reference=build_vector_reference(
                collection_name,
                document_chunk_id,
            ),
            embedding_dimension=embedding_dimension,
        )
