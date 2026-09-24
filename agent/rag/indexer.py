from __future__ import annotations

from pathlib import Path

from agent.rag.loading import chunk_documents, load_documents
from agent.rag.retriever.retrieval import SupabaseRetriever


def index_user_files(user_id: str, paths: list[str | Path]) -> int:
    """Chunk, embed and upsert files. Raises on failure (caller reports it)."""
    chunks = chunk_documents(load_documents(paths))
    if not chunks:
        return 0
    SupabaseRetriever(chunks, user_id=user_id)  
    return len(chunks)


def delete_user_source(user_id: str, source: str) -> None:
    SupabaseRetriever([], user_id=user_id).delete_source(source)
