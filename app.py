import os

from flask import Flask, jsonify, request
from openai import OpenAI
from qdrant_client import models

from embedding_orchestrator import EmbeddingOrchestrator
from embedding_service import EmbeddingService
from qdrant_store import QdrantStore, create_qdrant_client

app = Flask(__name__)


def _get_embedding_orchestrator():
    orchestrator = app.extensions.get("embedding_orchestrator")
    if orchestrator is not None:
        return orchestrator

    vector_db_url = os.getenv("VECTOR_DB_URL")
    if not vector_db_url or not vector_db_url.strip():
        raise RuntimeError("VECTOR_DB_URL is required")

    embedding_service = EmbeddingService(OpenAI())
    qdrant_client = create_qdrant_client(
        url=vector_db_url,
        api_key=os.getenv("QDRANT_API_KEY"),
    )
    orchestrator = EmbeddingOrchestrator(
        embedding_service,
        QdrantStore(qdrant_client),
        models.Distance.COSINE,
    )
    app.extensions["embedding_orchestrator"] = orchestrator
    return orchestrator


@app.get("/health")
def health():
    return jsonify(
        service="japan-newhire-rag-ai",
        status="ok",
    )


@app.post("/rag/search")
def rag_search():
    body = request.get_json(silent=True)

    if not isinstance(body, dict):
        return jsonify(error="malformed request"), 400

    question = body.get("question")
    allowed_document_version_ids = body.get("allowed_document_version_ids")
    provider_name = body.get("provider_name")
    model_name = body.get("model_name")

    if not isinstance(question, str) or not question.strip():
        return jsonify(error="malformed request"), 400

    if (
        not isinstance(allowed_document_version_ids, list)
        or not allowed_document_version_ids
        or any(
            not isinstance(document_version_id, int)
            or isinstance(document_version_id, bool)
            for document_version_id in allowed_document_version_ids
        )
    ):
        return jsonify(error="malformed request"), 400

    if not isinstance(provider_name, str) or not provider_name.strip():
        return jsonify(error="malformed request"), 400

    if not isinstance(model_name, str) or not model_name.strip():
        return jsonify(error="malformed request"), 400

    return jsonify(
        search_results=[
            {
                "document_version_id": allowed_document_version_ids[0],
                "chunk_id": 5001,
                "content": "예시 규정 텍스트",
                "similarity_score": 0.87,
            }
        ]
    )


@app.post("/rag/generate")
def rag_generate():
    body = request.get_json(silent=True)

    if not isinstance(body, dict):
        return jsonify(error="malformed request"), 400

    question = body.get("question")
    evidence = body.get("evidence")

    if not isinstance(question, str) or not question.strip():
        return jsonify(error="malformed request"), 400

    if (
        not isinstance(evidence, list)
        or not evidence
        or not isinstance(evidence[0], dict)
        or "chunk_id" not in evidence[0]
    ):
        return jsonify(error="malformed request"), 400

    return jsonify(
        answer="예시 답변 텍스트",
        cited_chunk_ids=[evidence[0]["chunk_id"]],
    )


@app.post("/embed")
def embed():
    body = request.get_json(silent=True)

    if not isinstance(body, dict):
        return jsonify(error="malformed request"), 400

    document_chunk_id = body.get("document_chunk_id")
    document_version_id = body.get("document_version_id")
    chunk_content = body.get("chunk_content")
    provider_name = body.get("provider_name")
    model_name = body.get("model_name")

    if not isinstance(document_chunk_id, int) or isinstance(document_chunk_id, bool):
        return jsonify(error="malformed request"), 400

    if not isinstance(document_version_id, int) or isinstance(document_version_id, bool):
        return jsonify(error="malformed request"), 400

    if not isinstance(chunk_content, str) or not chunk_content.strip():
        return jsonify(error="malformed request"), 400

    if not isinstance(provider_name, str) or not provider_name.strip():
        return jsonify(error="malformed request"), 400

    if not isinstance(model_name, str) or not model_name.strip():
        return jsonify(error="malformed request"), 400

    result = _get_embedding_orchestrator().process(
        document_chunk_id,
        document_version_id,
        chunk_content,
        provider_name,
        model_name,
    )

    return jsonify(
        vector_reference=result.vector_reference,
        embedding_dimension=result.embedding_dimension,
    )


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5001,
        debug=True,
    )
