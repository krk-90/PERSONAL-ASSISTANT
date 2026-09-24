from pathlib import Path

from fastapi.testclient import TestClient

from agent.rag.generator.generation import format_context
from agent.rag.loading import DocumentChunk
from agent.rag.retriever.retrieval import LocalRetriever, RetrievedChunk
from app.main import fastapi_app
from app.routes.RAG import save_uploaded_documents


def test_rag_upload_route_requires_auth():
    client = TestClient(fastapi_app)

    response = client.post(
        "/rag/upload",
        files=[("files", ("notes.txt", b"hello from rag", "text/plain"))],
    )

    assert response.status_code == 401


def test_save_uploaded_documents_stores_files(tmp_path):
    saved = save_uploaded_documents(
        [
            {
                "filename": "notes.txt",
                "content": b"hello from rag",
            }
        ],
        user_id="user-123",
        base_dir=tmp_path,
    )

    assert len(saved) == 1
    saved_path = Path(saved[0])
    assert saved_path.name == "notes.txt"
    assert saved_path.exists()


def test_list_and_delete_uploaded_documents(tmp_path):
    file_paths = save_uploaded_documents(
        [{"filename": "alpha.txt", "content": b"alpha"}],
        user_id="user-456",
        base_dir=tmp_path,
    )

    assert len(file_paths) == 1
    file_path = Path(file_paths[0])
    assert file_path.exists()

    file_path.unlink()
    assert not file_path.exists()


def test_local_retriever_matches_uploaded_filename():
    retriever = LocalRetriever(
        [DocumentChunk("Artificial intelligence projects", "resume.pdf", 0)]
    )

    results = retriever.search("check resume")

    assert len(results) == 1


def test_format_context_caps_long_retrieved_content():
    results = [
        RetrievedChunk(DocumentChunk("x" * 1000, "notes.txt", 0), 1.0),
        RetrievedChunk(DocumentChunk("y" * 1000, "more.txt", 1), 0.9),
    ]

    context = format_context(results, max_chars=100)

    assert len(context) <= 100
    assert context.startswith("[1] Source: notes.txt\n")
