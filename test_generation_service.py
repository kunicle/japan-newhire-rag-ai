import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from generation_service import GenerationService


@pytest.fixture(autouse=True)
def generation_model(monkeypatch):
    monkeypatch.setenv("OPENAI_GENERATION_MODEL", "gpt-4.1-mini")


def generation_response(answer="근거 기반 답변", citations=None, refusal=None):
    if citations is None:
        citations = [5001]
    message = SimpleNamespace(
        content=json.dumps({"answer": answer, "citations": citations}, ensure_ascii=False),
        refusal=refusal,
    )
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def evidence():
    return [
        {
            "document_version_id": 101,
            "chunk_id": 5001,
            "content": "육아휴직은 관련 규정에 따라 신청할 수 있습니다.",
            "similarity_score": 0.87,
        },
        {
            "document_version_id": 102,
            "chunk_id": 5002,
            "content": "신청 절차는 인사 부서에 문의합니다.",
            "similarity_score": 0.82,
        },
    ]


@pytest.mark.parametrize("citations", [[5001], [5001, 5002]])
def test_generate_parses_structured_response(citations):
    client = Mock()
    client.chat.completions.create.return_value = generation_response(citations=citations)

    answer, actual_citations = GenerationService(client).generate("질문", evidence())

    assert answer == "근거 기반 답변"
    assert actual_citations == citations


@pytest.mark.parametrize(
    ("question", "answer"),
    [
        ("육아휴직 규정을 알려주세요", "육아휴직을 신청할 수 있습니다."),
        ("育児休業の規定を教えてください", "育児休業を申請できます。"),
    ],
)
def test_generate_preserves_question_language(question, answer):
    client = Mock()
    client.chat.completions.create.return_value = generation_response(answer=answer)

    actual_answer, _ = GenerationService(client).generate(question, evidence())

    assert actual_answer == answer


@pytest.mark.parametrize("question", [None, "", "   "])
def test_generate_rejects_invalid_question_without_calling_client(question):
    client = Mock()

    with pytest.raises(ValueError, match="generation question"):
        GenerationService(client).generate(question, evidence())

    client.chat.completions.create.assert_not_called()


@pytest.mark.parametrize("evidence_items", [None, []])
def test_generate_rejects_invalid_evidence_without_calling_client(evidence_items):
    client = Mock()

    with pytest.raises(ValueError, match="generation evidence"):
        GenerationService(client).generate("질문", evidence_items)

    client.chat.completions.create.assert_not_called()


def test_generate_requires_model_without_calling_client(monkeypatch):
    monkeypatch.delenv("OPENAI_GENERATION_MODEL")
    client = Mock()

    with pytest.raises(RuntimeError, match="OPENAI_GENERATION_MODEL is required"):
        GenerationService(client).generate("질문", evidence())

    client.chat.completions.create.assert_not_called()


def test_generate_rejects_refusal():
    client = Mock()
    client.chat.completions.create.return_value = generation_response(refusal="cannot answer")

    with pytest.raises(ValueError, match="refused"):
        GenerationService(client).generate("질문", evidence())


def test_generate_rejects_malformed_json():
    client = Mock()
    message = SimpleNamespace(content="not-json", refusal=None)
    client.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=message)]
    )

    with pytest.raises(ValueError, match="malformed JSON"):
        GenerationService(client).generate("질문", evidence())


@pytest.mark.parametrize("answer", [None, "", "   "])
def test_generate_rejects_blank_answer(answer):
    client = Mock()
    client.chat.completions.create.return_value = generation_response(answer=answer)

    with pytest.raises(ValueError, match="answer must be a non-blank string"):
        GenerationService(client).generate("질문", evidence())


@pytest.mark.parametrize("citations", [5001, "5001", {"chunk_id": 5001}])
def test_generate_rejects_non_list_citations(citations):
    client = Mock()
    client.chat.completions.create.return_value = generation_response(citations=citations)

    with pytest.raises(ValueError, match="citations must be a list"):
        GenerationService(client).generate("질문", evidence())


@pytest.mark.parametrize("citations", [["5001"], [5001, 1.5], [True]])
def test_generate_rejects_non_integer_citation_items(citations):
    client = Mock()
    client.chat.completions.create.return_value = generation_response(citations=citations)

    with pytest.raises(ValueError, match="only integers"):
        GenerationService(client).generate("질문", evidence())


def test_generate_propagates_openai_exception():
    client = Mock()
    client.chat.completions.create.side_effect = RuntimeError("openai unavailable")

    with pytest.raises(RuntimeError, match="openai unavailable"):
        GenerationService(client).generate("질문", evidence())


def test_generate_prompt_contains_question_and_all_evidence():
    client = Mock()
    client.chat.completions.create.return_value = generation_response()

    GenerationService(client).generate("육아휴직 질문", evidence())

    messages = client.chat.completions.create.call_args.kwargs["messages"]
    user_message = messages[1]["content"]
    assert "육아휴직 질문" in user_message
    for item in evidence():
        assert f"[chunk_id={item['chunk_id']}]" in user_message
        assert item["content"] in user_message


def test_generate_passes_selected_model_and_generation_parameters():
    client = Mock()
    client.chat.completions.create.return_value = generation_response()

    GenerationService(client).generate("질문", evidence())

    kwargs = client.chat.completions.create.call_args.kwargs
    assert kwargs["model"] == "gpt-4.1-mini"
    assert kwargs["temperature"] == 0
    assert kwargs["max_completion_tokens"] == 800
    assert kwargs["response_format"]["type"] == "json_schema"
