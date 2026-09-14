from qdrant_store import build_collection_name


class RagSearchOrchestrator:
    def __init__(self, embedding_service, qdrant_store, limit):
        self._embedding_service = embedding_service
        self._qdrant_store = qdrant_store
        self._limit = limit

    def process(
        self,
        question,
        allowed_document_version_ids,
        provider_name,
        model_name,
    ):
        query_vector = self._embedding_service.embed_query(
            provider_name,
            model_name,
            question,
        )
        collection_name = build_collection_name(provider_name, model_name)
        return self._qdrant_store.search_chunks(
            collection_name,
            query_vector,
            allowed_document_version_ids,
            limit=self._limit,
        )
