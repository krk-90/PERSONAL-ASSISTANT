from __future__ import annotations

import os
from pathlib import Path

from langchain_core.language_models.chat_models import BaseChatModel

from agent.rag.generator.generation import generate_answer
from agent.rag.loading import DocumentChunk, chunk_documents, load_documents
from agent.rag.retriever.retrieval import (
    LocalRetriever,
    RetrievedChunk,
    SupabaseRetriever,
)


class RAGPipeline:
    def __init__(
        self,
        llm: BaseChatModel,
        chunks: list[DocumentChunk],
        use_supabase: bool = True,
    ):
        self.llm = llm
        self.retriever = self._create_retriever(chunks, use_supabase)

    @staticmethod
    def _create_retriever(chunks: list[DocumentChunk], use_supabase: bool):
        configured = all(
            os.getenv(name)
            for name in ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "TASK_USER_ID")
        )
        if use_supabase and configured:
            try:
                return SupabaseRetriever(chunks)
            except Exception:
                pass
        return LocalRetriever(chunks)

    @classmethod
    def from_path(
        cls,
        llm: BaseChatModel,
        path: str | Path | list[str | Path],
        chunk_size: int = 800,
        overlap: int = 120,
    ) -> "RAGPipeline":
        documents = load_documents(path)
        chunks = chunk_documents(documents, chunk_size=chunk_size, overlap=overlap)
        return cls(llm, chunks)

    def retrieve(self, question: str, limit: int = 4) -> list[RetrievedChunk]:
        return self.retriever.search(question, limit=limit)

    async def ask(self, question: str, limit: int = 4) -> str:
        results = self.retrieve(question, limit=limit)
        return await generate_answer(self.llm, question, results)


__all__ = ["RAGPipeline"]