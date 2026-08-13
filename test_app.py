from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from app import app
from qdrant_store import QdrantChunkSearchResult


@pytest.fixture
def client():
    app.config.update(TESTING=True)
    return app.test_client()


@patch("app._get_rag_search_orchestrator")
def test_rag_search_calls_orchestrator_and_maps_results(get_orchestrator, client):
    orchestrator = Mock()
    orchestrator.process.return_value = [
        QdrantChunkSearchResult(
            document_chunk_id=5001,
            document_version_id=10,
            chunk_content="예시 규정 텍스트",
            score=0.87,
        )
    ]
    get_orchestrator.return_value = orchestrator

    response = client.post(
        "/rag/search",
        json=valid_rag_search_body(),
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "search_results": [
            {
                "document_version_id": 10,
                "chunk_id": 5001,
                "content": "예시 규정 텍스트",
                "similarity_score": 0.87,
            }
        ]
    }
    orchestrator.process.assert_called_once_with(
        "육아휴직 규정을 알려주세요",
        [101, 102, 205],
        "openai",
        "text-embedding-3-small",
    )


def test_rag_search_rejects_missing_question(client):
    body = valid_rag_search_body()
    body.pop("question")

    response = client.post("/rag/search", json=body)

    assert_malformed_request(response)


@pytest.mark.parametrize(
    "allowed_document_version_ids",
    [
        None,
        [],
    ],
)
def test_rag_search_rejects_missing_or_empty_allowed_ids(
    client, allowed_document_version_ids
):
    body = valid_rag_search_body()
    if allowed_document_version_ids is None:
        body.pop("allowed_document_version_ids")
    else:
        body["allowed_document_version_ids"] = allowed_document_version_ids

    response = client.post("/rag/search", json=body)

    assert_malformed_request(response)


@pytest.mark.parametrize("field_name", ["provider_name", "model_name"])
@pytest.mark.parametrize("invalid_value", [None, "", "   ", 123])
def test_rag_search_rejects_invalid_model_fields(client, field_name, invalid_value):
    body = valid_rag_search_body()
    body[field_name] = invalid_value

    response = client.post("/rag/search", json=body)

    assert_malformed_request(response)


@pytest.mark.parametrize("field_name", ["provider_name", "model_name"])
def test_rag_search_rejects_missing_model_fields(client, field_name):
    body = valid_rag_search_body()
    body.pop(field_name)

    response = client.post("/rag/search", json=body)

    assert_malformed_request(response)


def test_rag_generate_returns_answer_with_citation_from_evidence(client):
    evidence = [
        {
            "document_version_id": 101,
            "chunk_id": 5001,
            "content": "육아휴직은 관련 규정에 따라 신청할 수 있습니다.",
            "similarity_score": 0.87,
        },
        {
            "document_version_id": 102,
            "chunk_id": 5002,
            "content": "두 번째 예시 규정 텍스트",
            "similarity_score": 0.82,
        },
    ]

    response = client.post(
        "/rag/generate",
        json={
            "question": "육아휴직 규정을 알려주세요",
            "evidence": evidence,
        },
    )

    assert response.status_code == 200
    response_body = response.get_json()
    assert "answer" in response_body
    assert isinstance(response_body["cited_chunk_ids"], list)
    assert set(response_body["cited_chunk_ids"]).issubset(
        {item["chunk_id"] for item in evidence}
    )


@pytest.mark.parametrize(
    "body",
    [
        {"evidence": [{"chunk_id": 5001}]},
        {"question": None, "evidence": [{"chunk_id": 5001}]},
        {"question": "", "evidence": [{"chunk_id": 5001}]},
        {"question": "   ", "evidence": [{"chunk_id": 5001}]},
    ],
)
def test_rag_generate_rejects_missing_null_or_blank_question(client, body):
    response = client.post("/rag/generate", json=body)

    assert response.status_code == 400


@pytest.mark.parametrize(
    "body",
    [
        {"question": "육아휴직 규정을 알려주세요"},
        {"question": "육아휴직 규정을 알려주세요", "evidence": None},
        {"question": "육아휴직 규정을 알려주세요", "evidence": []},
    ],
)
def test_rag_generate_rejects_missing_null_or_empty_evidence(client, body):
    response = client.post("/rag/generate", json=body)

    assert response.status_code == 400


@patch("app._get_embedding_orchestrator")
def test_embed_calls_orchestrator_and_returns_result(get_orchestrator, client):
    orchestrator = Mock()
    orchestrator.process.return_value = SimpleNamespace(
        vector_reference="rag_chunks_openai_text_embedding_3_small:101",
        embedding_dimension=1536,
    )
    get_orchestrator.return_value = orchestrator

    response = client.post("/embed", json=valid_embed_body())

    assert response.status_code == 200
    assert response.get_json() == {
        "vector_reference": "rag_chunks_openai_text_embedding_3_small:101",
        "embedding_dimension": 1536,
    }
    orchestrator.process.assert_called_once_with(
        101,
        10,
        "청크 본문",
        "openai",
        "text-embedding-3-small",
    )


@pytest.mark.parametrize(
    "document_chunk_id",
    [None, "101", True],
)
def test_embed_rejects_invalid_document_chunk_id(client, document_chunk_id):
    body = valid_embed_body()
    body["document_chunk_id"] = document_chunk_id

    response = client.post("/embed", json=body)

    assert_malformed_request(response)


def test_embed_rejects_missing_document_chunk_id(client):
    body = valid_embed_body()
    body.pop("document_chunk_id")

    response = client.post("/embed", json=body)

    assert_malformed_request(response)


@pytest.mark.parametrize(
    "document_version_id",
    [None, "10", True],
)
def test_embed_rejects_invalid_document_version_id(client, document_version_id):
    body = valid_embed_body()
    body["document_version_id"] = document_version_id

    response = client.post("/embed", json=body)

    assert_malformed_request(response)


def test_embed_rejects_missing_document_version_id(client):
    body = valid_embed_body()
    body.pop("document_version_id")

    response = client.post("/embed", json=body)

    assert_malformed_request(response)


@pytest.mark.parametrize("field_name", ["chunk_content", "provider_name", "model_name"])
@pytest.mark.parametrize(
    "invalid_value",
    [None, "", "   ", 123],
)
def test_embed_rejects_invalid_string_fields(client, field_name, invalid_value):
    body = valid_embed_body()
    body[field_name] = invalid_value

    response = client.post("/embed", json=body)

    assert_malformed_request(response)


@pytest.mark.parametrize("field_name", ["chunk_content", "provider_name", "model_name"])
def test_embed_rejects_missing_string_fields(client, field_name):
    body = valid_embed_body()
    body.pop(field_name)

    response = client.post("/embed", json=body)

    assert_malformed_request(response)


@pytest.mark.parametrize("body", [None, [], "invalid"])
def test_embed_rejects_missing_or_non_object_body(client, body):
    if body is None:
        response = client.post("/embed")
    else:
        response = client.post("/embed", json=body)

    assert_malformed_request(response)


def valid_embed_body():
    return {
        "document_chunk_id": 101,
        "document_version_id": 10,
        "chunk_content": "청크 본문",
        "provider_name": "openai",
        "model_name": "text-embedding-3-small",
    }


def valid_rag_search_body():
    return {
        "question": "육아휴직 규정을 알려주세요",
        "allowed_document_version_ids": [101, 102, 205],
        "provider_name": "openai",
        "model_name": "text-embedding-3-small",
    }


def assert_malformed_request(response):
    assert response.status_code == 400
    assert response.get_json() == {"error": "malformed request"}
