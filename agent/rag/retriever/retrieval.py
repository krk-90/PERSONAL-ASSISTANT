from __future__ import annotations

import logging
import math
import os
import re
from collections import Counter
from dataclasses import dataclass
from hashlib import sha256

from agent.rag.loading import DocumentChunk


logger = logging.getLogger(__name__)

TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9_]{2,}")
STOP_WORDS = {"the", "and", "for", "with", "that", "this", "from", "are", "was"}


def _tokens(text: str) -> list[str]:
	return [token for token in TOKEN_PATTERN.findall(text.lower()) if token not in STOP_WORDS]


@dataclass(frozen=True)
class RetrievedChunk:
	chunk: DocumentChunk
	score: float


class LocalRetriever:
	def __init__(self, chunks: list[DocumentChunk]):
		self.chunks = chunks
		self._term_counts = [
			Counter(_tokens(f"{chunk.source} {chunk.text}"))
			for chunk in chunks
		]
		document_frequency = Counter(
			token for counts in self._term_counts for token in counts
		)
		self._idf = {
			token: math.log((1 + len(chunks)) / (1 + frequency)) + 1
			for token, frequency in document_frequency.items()
		}

	def search(self, query: str, limit: int = 4) -> list[RetrievedChunk]:
		if limit <= 0:
			return []
		query_terms = Counter(_tokens(query))
		scored = []
		for chunk, term_counts in zip(self.chunks, self._term_counts):
			score = sum(
				query_frequency
				* (1 + math.log(term_counts[token]))
				* self._idf.get(token, 0.0)
				for token, query_frequency in query_terms.items()
				if token in term_counts
			)
			if score:
				scored.append(RetrievedChunk(chunk, score))
		return sorted(scored, key=lambda item: item.score, reverse=True)[:limit]


class SupabaseRetriever:
	def __init__(
		self,
		chunks: list[DocumentChunk],
		user_id: str | None = None,
		index_chunks: bool = True,
	):
		from fastembed import TextEmbedding
		from supabase import Client, create_client

		url = os.getenv("SUPABASE_URL")
		key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
		user_id = user_id or os.getenv("TASK_USER_ID")
		if not url or not key or not user_id:
			raise RuntimeError(
				"SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, and an authenticated user are required."
			)

		self.client: Client = create_client(url, key)
		self.user_id = user_id
		self.embedder = TextEmbedding(
			model_name=os.getenv("RAG_EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
		)
		if index_chunks:
			self.index(chunks)

	def _embedding(self, text: str) -> list[float]:
		return [float(x) for x in next(iter(self.embedder.embed([text])))]

	def _chunk_embedding(self, chunk: DocumentChunk) -> list[float]:
		return self._embedding(f"{chunk.source}\n{chunk.text}")

	def _row_id(self, chunk: DocumentChunk) -> str:
		value = f"{self.user_id}:{chunk.source}:{chunk.chunk_id}"
		return sha256(value.encode("utf-8")).hexdigest()

	def index(self, chunks: list[DocumentChunk]) -> None:
		if not chunks:
			return
		rows = [
			{
				"id": self._row_id(chunk),
				"user_id": self.user_id,
				"source": chunk.source,
				"content": chunk.text,
				"chunk_id": chunk.chunk_id,
				"embedding": self._chunk_embedding(chunk),
			}
			for chunk in chunks
		]
		for start in range(0, len(rows), 50):
			self.client.table("rag_documents").upsert(rows[start : start + 50]).execute()
		logger.info("Indexed %d chunks into rag_documents for user %s", len(rows), self.user_id)

	def delete_source(self, source: str) -> None:
		self.client.table("rag_documents").delete().eq("user_id", self.user_id).eq("source", source).execute()

	def search(self, query: str, limit: int = 4) -> list[RetrievedChunk]:
		if limit <= 0:
			return []
		response = self.client.rpc(
			"match_rag_documents",
			{
				"query_embedding": self._embedding(query),
				"match_user_id": self.user_id,
				"match_count": limit,
			},
		).execute()
		return [
			RetrievedChunk(
				DocumentChunk(row["content"], row["source"], row["chunk_id"]),
				float(row.get("similarity", 0.0)),
			)
			for row in response.data or []
		]


__all__ = ["LocalRetriever", "RetrievedChunk", "SupabaseRetriever"]
