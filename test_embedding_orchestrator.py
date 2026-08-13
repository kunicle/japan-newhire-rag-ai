from unittest.mock import Mock

import pytest
from qdrant_client import models

from embedding_orchestrator import EmbeddingOrchestrator


def test_process_embeds_ensures_upserts_and_returns_result():
    embedding_service = Mock()
    vector = [0.1, 0.2, 0.3]
    embedding_service.embed_document.return_value = vector
    qdrant_store = Mock()
    orchestrator = EmbeddingOrchestrator(
        embedding_service,
        qdrant_store,
        models.Distance.COSINE,
    )

    result = orchestrator.process(
        document_chunk_id=101,
        document_version_id=10,
        chunk_content="청크 본문",
        provider_name="openai",
        model_name="text-embedding-3-small",
    )

    collection_name = "rag_chunks_openai_text_embedding_3_small"
    embedding_service.embed_document.assert_called_once_with(
        "openai",
        "text-embedding-3-small",
        "청크 본문",
    )
    qdrant_store.ensure_collection.assert_called_once_with(
        collection_name,
        vector_size=3,
        distance=models.Distance.COSINE,
    )
    qdrant_store.upsert_chunk_embedding.assert_called_once_with(
        collection_name,
        101,
        10,
        "청크 본문",
        vector,
    )
    assert result.vector_reference == f"{collection_name}:101"
    assert result.embedding_dimension == 3


def test_process_stops_when_embedding_fails():
    embedding_service = Mock()
    embedding_service.embed_document.side_effect = RuntimeError("openai failed")
    qdrant_store = Mock()
    orchestrator = EmbeddingOrchestrator(
        embedding_service,
        qdrant_store,
        models.Distance.COSINE,
    )

    with pytest.raises(RuntimeError, match="openai failed"):
        orchestrator.process(101, 10, "청크 본문", "openai", "text-embedding-3-small")

    qdrant_store.ensure_collection.assert_not_called()
    qdrant_store.upsert_chunk_embedding.assert_not_called()


def test_process_stops_when_collection_ensure_fails():
    embedding_service = Mock()
    embedding_service.embed_document.return_value = [0.1, 0.2, 0.3]
    qdrant_store = Mock()
    qdrant_store.ensure_collection.side_effect = RuntimeError("qdrant ensure failed")
    orchestrator = EmbeddingOrchestrator(
        embedding_service,
        qdrant_store,
        models.Distance.COSINE,
    )

    with pytest.raises(RuntimeError, match="qdrant ensure failed"):
        orchestrator.process(101, 10, "청크 본문", "openai", "text-embedding-3-small")

    qdrant_store.upsert_chunk_embedding.assert_not_called()


def test_process_propagates_upsert_failure():
    embedding_service = Mock()
    embedding_service.embed_document.return_value = [0.1, 0.2, 0.3]
    qdrant_store = Mock()
    qdrant_store.upsert_chunk_embedding.side_effect = RuntimeError(
        "qdrant upsert failed"
    )
    orchestrator = EmbeddingOrchestrator(
        embedding_service,
        qdrant_store,
        models.Distance.COSINE,
    )

    with pytest.raises(RuntimeError, match="qdrant upsert failed"):
        orchestrator.process(101, 10, "청크 본문", "openai", "text-embedding-3-small")
