from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate

from agent.rag.retriever.retrieval import RetrievedChunk


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


def format_context(results: list[RetrievedChunk]) -> str:
	return "\n\n".join(
		f"[{index}] Source: {result.chunk.source}\n{result.chunk.text}"
		for index, result in enumerate(results, start=1)
	)


async def generate_answer(
	llm: BaseChatModel,
	question: str,
	results: list[RetrievedChunk],
) -> str:
	if not results:
		return "I could not find relevant information in the indexed documents."
	response = await (ANSWER_PROMPT | llm).ainvoke(
		{"question": question, "context": format_context(results)}
	)
	return str(response.content)


__all__ = ["format_context", "generate_answer"]
