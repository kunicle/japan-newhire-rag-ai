import pytest

from app import app


@pytest.fixture
def client():
    app.config.update(TESTING=True)
    return app.test_client()


def test_rag_search_returns_stub_result(client):
    response = client.post(
        "/rag/search",
        json={
            "question": "육아휴직 규정을 알려주세요",
            "allowed_document_version_ids": [101, 102, 205],
        },
    )

    assert response.status_code == 200
    search_results = response.get_json()["search_results"]
    assert isinstance(search_results, list)
    assert len(search_results) == 1
    assert set(search_results[0]) == {
        "document_version_id",
        "chunk_id",
        "content",
        "similarity_score",
    }


def test_rag_search_rejects_missing_question(client):
    response = client.post(
        "/rag/search",
        json={"allowed_document_version_ids": [101]},
    )

    assert response.status_code == 400


@pytest.mark.parametrize(
    "body",
    [
        {"question": "육아휴직 규정을 알려주세요"},
        {
            "question": "육아휴직 규정을 알려주세요",
            "allowed_document_version_ids": [],
        },
    ],
)
def test_rag_search_rejects_missing_or_empty_allowed_ids(client, body):
    response = client.post("/rag/search", json=body)

    assert response.status_code == 400


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


def test_embed_returns_deterministic_stub_result(client):
    response = client.post(
        "/embed",
        json={
            "document_chunk_id": 101,
            "chunk_content": "example",
            "provider_name": "provider-a",
            "model_name": "model-a",
        },
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "vector_reference": "chunk-101-vector",
        "embedding_dimension": 3,
    }


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
        "chunk_content": "example",
        "provider_name": "provider-a",
        "model_name": "model-a",
    }


def assert_malformed_request(response):
    assert response.status_code == 400
    assert response.get_json() == {"error": "malformed request"}
