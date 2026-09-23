from pathlib import Path

from fastapi.testclient import TestClient

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
