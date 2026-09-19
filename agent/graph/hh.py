import asyncio

from agent.graph.git_agent import (
    create_git_agent,
    get_git_agent_response
)

from llm_gateway.provider.groq_llm import get_model


async def main():
    repo_path = input("Enter repo path: ").strip()

    llm = get_model("openai/gpt-oss-20b")

    git_agent = await create_git_agent(
        llm,
        repo_path
    )

    response = await get_git_agent_response(
        git_agent,
        "Show me the current git status"
    )

    print(response)


if __name__ == "__main__":
    asyncio.run(main())