from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langsmith import traceable

from app.core.tracing import trace_config
from agent.rag.retriever.retrieval import RetrievedChunk


MAX_CONTEXT_CHARS = 6000


ANSWER_PROMPT = ChatPromptTemplate.from_messages(
	[
		(
			"system",
			"""You answer questions using only the supplied context.
If the context does not contain the answer, say you do not know.
Be concise and cite sources using [1], [2], matching the source list.""",
		),
		("human", "Question: {question}\n\nContext:\n{context}"),
	]
)


def format_context(
	results: list[RetrievedChunk], max_chars: int = MAX_CONTEXT_CHARS
) -> str:
	if max_chars <= 0:
		return ""

	formatted: list[str] = []
	remaining = max_chars
	for index, result in enumerate(results, start=1):
		prefix = f"[{index}] Source: {result.chunk.source}\n"
		if remaining <= len(prefix):
			break
		text = result.chunk.text[: remaining - len(prefix)]
		formatted.append(f"{prefix}{text}")
		remaining -= len(formatted[-1]) + 2
		if len(text) < len(result.chunk.text):
			break
	return "\n\n".join(formatted)


@traceable(name="rag.generate_answer")
async def generate_answer(
	llm: BaseChatModel,
	question: str,
	results: list[RetrievedChunk],
	user_id: str | None = None,
) -> str:
	if not results:
		return "I could not find relevant information in the indexed documents."
	response = await (ANSWER_PROMPT | llm).ainvoke(
		{"question": question, "context": format_context(results)},
		config=trace_config(
			"rag.answer_model",
			user_id=user_id,
			tags=["rag", "generation"],
		),
	)
	return str(response.content)


__all__ = ["format_context", "generate_answer"]
