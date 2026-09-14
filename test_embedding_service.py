from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from embedding_service import EmbeddingService


def embedding_response(vector=None):
    if vector is None:
        vector = [0.1] * 1536
    return SimpleNamespace(data=[SimpleNamespace(embedding=vector)])


def test_embed_document_calls_openai_and_returns_vector():
    client = Mock()
    vector = [0.1] * 1536
    client.embeddings.create.return_value = embedding_response(vector)
    service = EmbeddingService(client)

    result = service.embed_document(
        "openai",
        "text-embedding-3-small",
        "사내 규정 텍스트",
    )

    client.embeddings.create.assert_called_once_with(
        model="text-embedding-3-small",
        input="사내 규정 텍스트",
        encoding_format="float",
    )
    assert result is vector


def test_embed_query_calls_openai_and_returns_vector():
    client = Mock()
    vector = [0.2] * 1536
    client.embeddings.create.return_value = embedding_response(vector)
    service = EmbeddingService(client)

    result = service.embed_query(
        "openai",
        "text-embedding-3-small",
        "휴가 규정은 어떻게 되나요?",
    )

    client.embeddings.create.assert_called_once_with(
        model="text-embedding-3-small",
        input="휴가 규정은 어떻게 되나요?",
        encoding_format="float",
    )
    assert result is vector


def test_embed_preserves_original_text():
    client = Mock()
    client.embeddings.create.return_value = embedding_response()
    service = EmbeddingService(client)

    service.embed_document(
        "openai",
        "text-embedding-3-small",
        "  규정 텍스트  ",
    )

    assert client.embeddings.create.call_args.kwargs["input"] == "  규정 텍스트  "


def test_embed_rejects_unsupported_provider_without_calling_client():
    client = Mock()
    service = EmbeddingService(client)

    with pytest.raises(ValueError, match="unsupported embedding provider"):
        service.embed_document(
            "cohere",
            "text-embedding-3-small",
            "규정 텍스트",
        )

    client.embeddings.create.assert_not_called()


def test_embed_rejects_unsupported_model_without_calling_client():
    client = Mock()
    service = EmbeddingService(client)

    with pytest.raises(ValueError, match="unsupported embedding model"):
        service.embed_document(
            "openai",
            "text-embedding-3-large",
            "규정 텍스트",
        )

    client.embeddings.create.assert_not_called()


@pytest.mark.parametrize("text", [None, 123, "", "   "])
def test_embed_rejects_invalid_text_without_calling_client(text):
    client = Mock()
    service = EmbeddingService(client)

    with pytest.raises(ValueError, match="embedding text"):
        service.embed_document("openai", "text-embedding-3-small", text)

    client.embeddings.create.assert_not_called()


def test_embed_rejects_response_without_data():
    client = Mock()
    client.embeddings.create.return_value = SimpleNamespace(data=[])
    service = EmbeddingService(client)

    with pytest.raises(ValueError, match="contains no data"):
        service.embed_document(
            "openai",
            "text-embedding-3-small",
            "규정 텍스트",
        )


def test_embed_rejects_empty_embedding():
    client = Mock()
    client.embeddings.create.return_value = embedding_response([])
    service = EmbeddingService(client)

    with pytest.raises(ValueError, match="contains no vector"):
        service.embed_document(
            "openai",
            "text-embedding-3-small",
            "규정 텍스트",
        )


def test_embed_rejects_wrong_dimension():
    client = Mock()
    client.embeddings.create.return_value = embedding_response([0.1] * 1535)
    service = EmbeddingService(client)

    with pytest.raises(ValueError, match="expected 1536, got 1535"):
        service.embed_document(
            "openai",
            "text-embedding-3-small",
            "규정 텍스트",
        )


def test_embed_propagates_client_exception():
    client = Mock()
    client.embeddings.create.side_effect = RuntimeError("openai unavailable")
    service = EmbeddingService(client)

    with pytest.raises(RuntimeError, match="openai unavailable"):
        service.embed_query(
            "openai",
            "text-embedding-3-small",
            "휴가 규정은 어떻게 되나요?",
        )
