from __future__ import annotations

import logging
import os
from pathlib import Path

from langchain_core.language_models.chat_models import BaseChatModel
from langsmith import traceable

from app.core.tracing import trace_config
from agent.rag.generator.generation import generate_answer
from agent.rag.loading import DocumentChunk, chunk_documents, load_documents
from agent.rag.retriever.retrieval import (
    LocalRetriever,
    RetrievedChunk,
    SupabaseRetriever,
)


logger = logging.getLogger(__name__)


class RAGPipeline:
    def __init__(
        self,
        llm: BaseChatModel,
        chunks: list[DocumentChunk],
        use_supabase: bool = True,
        user_id: str | None = None,
    ):
        self.llm = llm
        self.user_id = user_id
        self.retriever = self._create_retriever(chunks, use_supabase, user_id)

    @staticmethod
    def _create_retriever(
        chunks: list[DocumentChunk],
        use_supabase: bool,
        user_id: str | None = None,
    ):
        resolved_user_id = user_id or os.getenv("TASK_USER_ID")
        configured = all(
            os.getenv(name)
            for name in ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY")
        ) and bool(resolved_user_id)
        if use_supabase and configured:
            try:
                return SupabaseRetriever(chunks, user_id=resolved_user_id)
            except Exception:
                logger.exception("SupabaseRetriever failed; falling back to in-memory LocalRetriever")
        elif use_supabase:
            logger.warning("Supabase RAG not configured (SUPABASE_URL/SERVICE_ROLE_KEY/user_id); using LocalRetriever")
        return LocalRetriever(chunks)

    @classmethod
    def from_path(
        cls,
        llm: BaseChatModel,
        path: str | Path | list[str | Path],
        chunk_size: int = 800,
        overlap: int = 120,
        user_id: str | None = None,
    ) -> "RAGPipeline":
        documents = load_documents(path)
        chunks = chunk_documents(documents, chunk_size=chunk_size, overlap=overlap)
        return cls(llm, chunks, user_id=user_id)

    def retrieve(self, question: str, limit: int = 4) -> list[RetrievedChunk]:
        return self.retriever.search(question, limit=limit)

    @traceable(name="rag.pipeline.ask")
    async def ask(self, question: str, limit: int = 4) -> str:
        results = self.retrieve(question, limit=limit)
        return await generate_answer(
            self.llm,
            question,
            results,
            user_id=self.user_id,
        )


__all__ = ["RAGPipeline"]