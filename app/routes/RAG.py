from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.core.security import bearer_scheme, get_authenticated_user_id
from app.services.chat_services import invalidate_orchestrator_cache

router = APIRouter(prefix="/rag", tags=["rag"])


def get_user_upload_dir(user_id: str, base_dir: str | Path | None = None) -> Path:
    root = Path(base_dir) if base_dir is not None else Path(__file__).resolve().parents[2] / "data" / "uploads"
    upload_dir = root / user_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def save_uploaded_documents(files, user_id: str, base_dir: str | Path | None = None):
    storage_root = get_user_upload_dir(user_id, base_dir)
    saved_paths = []
    for file in files:
        filename = Path(file["filename"]).name
        if not filename:
            continue
        destination = storage_root / filename
        destination.write_bytes(file["content"])
        saved_paths.append(str(destination))

    return saved_paths


@router.post("/upload")
async def upload_documents(
    files: list[UploadFile] = File(
        ..., description="Files to upload for RAG indexing"
    ),
    credentials=Depends(bearer_scheme),
):
    user_id = get_authenticated_user_id(credentials)

    if not files:
        raise HTTPException(
            status_code=400,
            detail="No files uploaded",
        )

    upload_dir = get_user_upload_dir(user_id)

    saved = []

    for file in files:
        if not file.filename:
            continue

        file_path = upload_dir / Path(file.filename).name

        content = await file.read()

        if not content:
            continue

        file_path.write_bytes(content)

        saved.append({
            "filename": file.filename,
            "content_type": file.content_type,
            "size": len(content),
            "path": str(file_path),
        })

    if not saved:
        raise HTTPException(
            status_code=400,
            detail="No valid files uploaded",
        )

    invalidate_orchestrator_cache(user_id)

    return {
        "message": "Files uploaded successfully",
        "files": saved,
    }


@router.get("/files")
async def list_uploaded_documents(credentials=Depends(bearer_scheme)):
    user_id = get_authenticated_user_id(credentials)
    upload_dir = get_user_upload_dir(user_id)

    files = [
        {"filename": path.name, "path": str(path)}
        for path in sorted(upload_dir.iterdir())
        if path.is_file()
    ]

    return {"files": files}


@router.delete("/files/{filename}")
async def delete_uploaded_document(filename: str, credentials=Depends(bearer_scheme)):
    user_id = get_authenticated_user_id(credentials)
    upload_dir = get_user_upload_dir(user_id)
    destination = upload_dir / filename

    if not destination.exists() or not destination.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    destination.unlink()
    return {"message": "File deleted successfully", "filename": filename}
