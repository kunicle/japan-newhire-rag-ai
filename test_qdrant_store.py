from unittest.mock import Mock, patch

import pytest
from qdrant_client import models

from qdrant_store import (
    QdrantStore,
    build_collection_name,
    build_vector_reference,
    create_qdrant_client,
    normalize_collection_component,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("OpenAI", "openai"),
        ("text-embedding-3-small", "text_embedding_3_small"),
        ("BAAI/bge-m3", "baai_bge_m3"),
        ("provider...model", "provider_model"),
        ("///OpenAI...", "openai"),
    ],
)
def test_normalize_collection_component(value, expected):
    assert normalize_collection_component(value) == expected


@pytest.mark.parametrize("value", [None, 123, "", "   ", "///", "..."])
def test_normalize_collection_component_rejects_invalid_value(value):
    with pytest.raises(ValueError):
        normalize_collection_component(value)


def test_build_collection_name_is_deterministic_and_preserves_component_order():
    expected = "rag_chunks_openai_text_embedding_3_small"

    assert build_collection_name("OpenAI", "text-embedding-3-small") == expected
    assert build_collection_name("OpenAI", "text-embedding-3-small") == expected


def test_build_vector_reference():
    assert (
        build_vector_reference("rag_chunks_openai_text_embedding_3_small", 101)
        == "rag_chunks_openai_text_embedding_3_small:101"
    )


@patch("qdrant_store.QdrantClient")
def test_create_qdrant_client_passes_url_and_api_key(qdrant_client_class):
    client = create_qdrant_client(
        url="https://example.qdrant.io",
        api_key="secret",
    )

    qdrant_client_class.assert_called_once_with(
        url="https://example.qdrant.io",
        api_key="secret",
    )
    assert client is qdrant_client_class.return_value


def test_ensure_collection_does_not_create_existing_collection():
    client = Mock()
    client.collection_exists.return_value = True
    store = QdrantStore(client)

    store.ensure_collection(
        "rag_chunks_openai_text_embedding_3_small",
        vector_size=1024,
        distance=models.Distance.COSINE,
    )

    client.collection_exists.assert_called_once_with(
        "rag_chunks_openai_text_embedding_3_small"
    )
    client.create_collection.assert_not_called()


def test_ensure_collection_creates_missing_collection():
    client = Mock()
    client.collection_exists.return_value = False
    store = QdrantStore(client)

    store.ensure_collection(
        "rag_chunks_openai_text_embedding_3_small",
        vector_size=1024,
        distance=models.Distance.COSINE,
    )

    client.collection_exists.assert_called_once_with(
        "rag_chunks_openai_text_embedding_3_small"
    )
    client.create_collection.assert_called_once()
    call = client.create_collection.call_args
    assert call.kwargs["collection_name"] == (
        "rag_chunks_openai_text_embedding_3_small"
    )
    assert call.kwargs["vectors_config"].size == 1024
    assert call.kwargs["vectors_config"].distance == models.Distance.COSINE


def test_upsert_chunk_embedding_writes_exact_point_and_waits():
    client = Mock()
    store = QdrantStore(client)

    store.upsert_chunk_embedding(
        collection_name="rag_chunks_provider_a_model_a",
        document_chunk_id=101,
        document_version_id=10,
        chunk_content="actual chunk content",
        vector=[0.1, 0.2, 0.3],
    )

    client.upsert.assert_called_once()
    call = client.upsert.call_args
    assert call.kwargs["collection_name"] == "rag_chunks_provider_a_model_a"
    assert call.kwargs["wait"] is True
    assert len(call.kwargs["points"]) == 1

    point = call.kwargs["points"][0]
    assert point.id == 101
    assert point.vector == [0.1, 0.2, 0.3]
    assert point.payload == {
        "document_chunk_id": 101,
        "document_version_id": 10,
        "chunk_content": "actual chunk content",
    }
    client.collection_exists.assert_not_called()
    client.create_collection.assert_not_called()


def test_upsert_chunk_embedding_propagates_client_exception():
    client = Mock()
    client.upsert.side_effect = RuntimeError("qdrant unavailable")
    store = QdrantStore(client)

    with pytest.raises(RuntimeError, match="qdrant unavailable"):
        store.upsert_chunk_embedding(
            collection_name="rag_chunks_provider_a_model_a",
            document_chunk_id=101,
            document_version_id=10,
            chunk_content="actual chunk content",
            vector=[0.1, 0.2, 0.3],
        )
