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
