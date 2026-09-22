import asyncio

from agent.graph.git_agent import (
    create_git_agent,
    get_git_agent_response
)
from agent.graph.task_agent import (
    create_task_agent,
    get_task_agent_response,
)

from llm_gateway.provider.groq_llm import get_model


async def main():
    llm = get_model("openai/gpt-oss-20b")

    while True:
        agent_type = input("Choose agent (git/task, or exit): ").strip().lower()

        if agent_type in {"exit", "quit"}:
            break

        if agent_type not in {"git", "task"}:
            print("Please choose either 'git' or 'task'.")
            continue

        if agent_type == "git":
            repo_path = input("Enter repo path: ").strip()
            agent = await create_git_agent(llm, repo_path)
            get_response = get_git_agent_response
            prompt_name = "Git"
        else:
            agent = await create_task_agent(llm)
            get_response = get_task_agent_response
            prompt_name = "Task"

        while True:
            query = input(f"\n{prompt_name}> ").strip()

            if query.lower() in ["exit", "quit"]:
                break

            response = await get_response(agent, query)

            print("\n", response)


if __name__ == "__main__":
    asyncio.run(main())