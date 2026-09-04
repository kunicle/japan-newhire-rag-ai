import os

from flask import Flask, jsonify, request
from openai import OpenAI
from qdrant_client import models

from embedding_orchestrator import EmbeddingOrchestrator
from embedding_service import EmbeddingService
from generation_service import GenerationService
from qdrant_store import QdrantStore, create_qdrant_client
from rag_search_orchestrator import RagSearchOrchestrator

app = Flask(__name__)
RAG_SEARCH_LIMIT = 5


def get_flask_runtime_config():
    flask_env = os.getenv("FLASK_ENV", "development").strip().lower()
    flask_host = os.getenv("FLASK_HOST", "127.0.0.1")
    flask_port_value = os.getenv("FLASK_PORT", "5001")

    try:
        flask_port = int(flask_port_value)
    except ValueError as error:
        raise ValueError("FLASK_PORT must be an integer") from error

    if not 1 <= flask_port <= 65535:
        raise ValueError("FLASK_PORT must be between 1 and 65535")

    return {
        "host": flask_host,
        "port": flask_port,
        "debug": flask_env == "development",
    }


def _get_embedding_service():
    service = app.extensions.get("embedding_service")
    if service is None:
        service = EmbeddingService(OpenAI())
        app.extensions["embedding_service"] = service
    return service


def _get_generation_service():
    service = app.extensions.get("generation_service")
    if service is None:
        service = GenerationService(OpenAI())
        app.extensions["generation_service"] = service
    return service


def _get_qdrant_store():
    store = app.extensions.get("qdrant_store")
    if store is not None:
        return store

    vector_db_url = os.getenv("VECTOR_DB_URL")
    if not vector_db_url or not vector_db_url.strip():
        raise RuntimeError("VECTOR_DB_URL is required")

    client = create_qdrant_client(
        url=vector_db_url,
        api_key=os.getenv("QDRANT_API_KEY"),
    )
    store = QdrantStore(client)
    app.extensions["qdrant_store"] = store
    return store


def _get_embedding_orchestrator():
    orchestrator = app.extensions.get("embedding_orchestrator")
    if orchestrator is not None:
        return orchestrator

    orchestrator = EmbeddingOrchestrator(
        _get_embedding_service(),
        _get_qdrant_store(),
        models.Distance.COSINE,
    )
    app.extensions["embedding_orchestrator"] = orchestrator
    return orchestrator


def _get_rag_search_orchestrator():
    orchestrator = app.extensions.get("rag_search_orchestrator")
    if orchestrator is None:
        orchestrator = RagSearchOrchestrator(
            _get_embedding_service(),
            _get_qdrant_store(),
            RAG_SEARCH_LIMIT,
        )
        app.extensions["rag_search_orchestrator"] = orchestrator
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

    results = _get_rag_search_orchestrator().process(
        question,
        allowed_document_version_ids,
        provider_name,
        model_name,
    )

    return jsonify(
        search_results=[
            {
                "document_version_id": result.document_version_id,
                "chunk_id": result.document_chunk_id,
                "content": result.chunk_content,
                "similarity_score": result.score,
            }
            for result in results
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

    answer, citations = _get_generation_service().generate(question, evidence)
    return jsonify(answer=answer, cited_chunk_ids=citations)


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
    app.run(**get_flask_runtime_config())
