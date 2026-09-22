import asyncio
import sys
from pathlib import Path

if __package__ in {None, ""}:
	sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from agent.graph.orchestrator.orchestrator import (
	create_orchestrator,
	get_orchestrator_response,
)
from llm_gateway.provider.groq_llm import get_model


async def main():
	llm = get_model("openai/gpt-oss-20b")

	while True:
		repo_path = input("Repository path (or exit): ").strip()

		if repo_path.lower() in {"exit", "quit"}:
			break

		orchestrator = await create_orchestrator(llm, repo_path)

		while True:
			query = input("\nAssistant (or exit to switch repository): ").strip()

			if query.lower() in {"exit", "quit"}:
				break

			response = await get_orchestrator_response(orchestrator, query)
			print("\n", response)


if __name__ == "__main__":
	asyncio.run(main())
