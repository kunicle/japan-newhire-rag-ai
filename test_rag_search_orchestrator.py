from unittest.mock import Mock

import pytest

from rag_search_orchestrator import RagSearchOrchestrator


def test_process_embeds_query_and_searches_model_collection():
    embedding_service = Mock()
    query_vector = [0.1, 0.2, 0.3]
    embedding_service.embed_query.return_value = query_vector
    qdrant_store = Mock()
    expected_results = [Mock()]
    qdrant_store.search_chunks.return_value = expected_results
    orchestrator = RagSearchOrchestrator(embedding_service, qdrant_store, limit=5)

    results = orchestrator.process(
        "육아휴직 규정을 알려주세요",
        [10, 20],
        "openai",
        "text-embedding-3-small",
    )

    embedding_service.embed_query.assert_called_once_with(
        "openai",
        "text-embedding-3-small",
        "육아휴직 규정을 알려주세요",
    )
    qdrant_store.search_chunks.assert_called_once_with(
        "rag_chunks_openai_text_embedding_3_small",
        query_vector,
        [10, 20],
        limit=5,
    )
    assert results is expected_results


def test_process_stops_when_query_embedding_fails():
    embedding_service = Mock()
    embedding_service.embed_query.side_effect = RuntimeError("openai failed")
    qdrant_store = Mock()
    orchestrator = RagSearchOrchestrator(embedding_service, qdrant_store, limit=5)

    with pytest.raises(RuntimeError, match="openai failed"):
        orchestrator.process(
            "질문",
            [10],
            "openai",
            "text-embedding-3-small",
        )

    qdrant_store.search_chunks.assert_not_called()


def test_process_propagates_search_failure():
    embedding_service = Mock()
    embedding_service.embed_query.return_value = [0.1, 0.2, 0.3]
    qdrant_store = Mock()
    qdrant_store.search_chunks.side_effect = RuntimeError("qdrant failed")
    orchestrator = RagSearchOrchestrator(embedding_service, qdrant_store, limit=5)

    with pytest.raises(RuntimeError, match="qdrant failed"):
        orchestrator.process(
            "질문",
            [10],
            "openai",
            "text-embedding-3-small",
        )
