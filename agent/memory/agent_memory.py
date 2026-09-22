import asyncio
import os
from typing import Any

from mem0 import Memory


class LongTermMemory:
	def __init__(self, user_id: str = "default-user"):
		self.user_id = user_id
		self._memory: Memory | None = None

	def _get_memory(self) -> Memory:
		if self._memory is None:
			connection_string = os.getenv("SUPABASE_DB_URL")
			if not connection_string:
				raise RuntimeError("SUPABASE_DB_URL is required for long-term memory")

			config = {
				"vector_store": {
					"provider": "supabase",
					"config": {
						"connection_string": connection_string,
						"collection_name": "assistant_memory",
						"embedding_model_dims": 384,
					},
				},
				"llm": {
					"provider": "groq",
					"config": {
						"model": os.getenv(
							"MEM0_LLM_MODEL", "llama-3.3-70b-versatile"
						),
					},
				},
				"embedder": {
					"provider": "fastembed",
					"config": {
						"model": os.getenv(
							"MEM0_EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5"
						),
						"embedding_dims": 384,
					},
				},
				"history_db_path": os.getenv(
					"MEM0_HISTORY_DB_PATH", "data/mem0-history.db"
				),
			}
			self._memory = Memory.from_config(config)

		return self._memory

	async def search(self, query: str, limit: int = 5) -> list[str]:
		try:
			result = await asyncio.to_thread(
				self._get_memory().search,
				query,
				user_id=self.user_id,
				top_k=limit,
			)
			return [item["memory"] for item in result.get("results", [])]
		except Exception:
			return []

	async def add(self, user_message: str, assistant_message: str) -> bool:
		try:
			messages = [
				{"role": "user", "content": user_message},
				{"role": "assistant", "content": assistant_message},
			]
			await asyncio.to_thread(
				self._get_memory().add,
				messages,
				user_id=self.user_id,
			)
			return True
		except Exception:
			return False

	async def clear(self) -> bool:
		try:
			await asyncio.to_thread(
				self._get_memory().delete_all,
				user_id=self.user_id,
			)
			return True
		except Exception:
			return False

	@staticmethod
	def format_context(memories: list[str]) -> str:
		if not memories:
			return ""
		items = "\n".join(f"- {memory}" for memory in memories)
		return f"Relevant long-term memory:\n{items}\n\n"


__all__ = ["LongTermMemory"]
