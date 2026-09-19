from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate

from mcp_server.server.git_server import get_git_tools


async def create_git_agent(llm, repo_path: str):
    tools = await get_git_tools()

    print("\n[Git Agent] Loaded tools:")
    for tool in tools:
        print(f" - {tool.name}")

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                f"""
You are an Expert Git Assistant.

Repository Path:
{repo_path}

Rules:
- Always use this repository path when calling Git tools.
- Never ask for the repository path.
- Use Git tools whenever repository information is required.
- Never invent Git output.
- Summarize results clearly.
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
        verbose=False,
        max_iterations=5,
        handle_parsing_errors=True,
    )


async def get_git_agent_response(
    agent: AgentExecutor,
    query: str
) -> str:
    try:
        response = await agent.ainvoke(
            {
                "input": query
            }
        )

        return response.get(
            "output",
            "No response generated."
        )

    except Exception as e:
        return f"Git Agent Error: {e}"