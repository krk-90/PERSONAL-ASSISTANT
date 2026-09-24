from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langsmith import traceable
import traceback

from app.core.tracing import trace_config
from mcp_server.server.git_server import get_git_tools


async def create_git_agent(llm, repo_path: str):
    tools = await get_git_tools(repo_path)

    print("TOOLS:")
    for t in tools:
        print(t.name)

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                f"""
You are an expert Git assistant.

Repository path:
{repo_path}

Available tools:
- git_status
- git_diff_unstaged
- git_diff_staged
- git_diff
- git_commit
- git_add
- git_reset
- git_log
- git_create_branch
- git_checkout
- git_show
- git_branch

Rules:
- Automatically choose the most appropriate tool.
- Never ask for a tool name.
- Never ask for the repository path.
- Use tools before answering.
- Explain the results clearly.
"""
            ),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}")
        ]
    )

    agent = create_tool_calling_agent(
        llm=llm,
        tools=tools,
        prompt=prompt,
    )

    return AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,
    max_iterations=2,
    handle_parsing_errors=True,
)

@traceable(name="git_agent.response")
async def get_git_agent_response(
    agent: AgentExecutor,
    query: str,
    user_id: str | None = None,
) -> str:
    try:
        response = await agent.ainvoke(
            {"input": query},
            config=trace_config(
                "git_agent.execution",
                user_id=user_id,
                tags=["agent", "git"],
            ),
        )

        return response.get(
            "output",
            "No response generated."
        )


    except Exception as error:
        print("\n" + "=" * 80)
        print("FULL GIT TRACEBACK")
        print("=" * 80)

        traceback.print_exc()

        print("=" * 80 + "\n")

        response = (
            f"Git Agent Error: {type(error).__name__}: {error}"
        )