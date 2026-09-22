from typing import Literal

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

from agent.graph.git_agent import create_git_agent, get_git_agent_response
from agent.graph.task_agent import create_task_agent, get_task_agent_response


class RouteDecision(BaseModel):
    agent: Literal["git", "task"] = Field(
        description="The specialist that should handle the user's request."
    )


class OrchestratorState(TypedDict, total=False):
    query: str
    route: Literal["git", "task"]
    response: str


ROUTER_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
You route requests to one specialist agent.

Choose git for repository operations such as status, diffs, branches, commits,
history, checkout, or inspecting files in a repository.
Choose task for creating, listing, updating, completing, or deleting personal tasks.
Return only the selected specialist.
""",
        ),
        ("human", "{query}"),
    ]
)


async def create_orchestrator(llm: BaseChatModel, repo_path: str):
    """Build and compile the router graph with both specialist agents."""
    task_agent = await create_task_agent(llm)
    router = ROUTER_PROMPT | llm.with_structured_output(RouteDecision)
    git_agent = None

    async def route_request(state: OrchestratorState) -> dict:
        decision = await router.ainvoke({"query": state["query"]})
        return {"route": decision.agent}

    async def run_git_agent(state: OrchestratorState) -> dict:
        nonlocal git_agent
        try:
            if git_agent is None:
                git_agent = await create_git_agent(llm, repo_path)
            response = await get_git_agent_response(git_agent, state["query"])
        except Exception as error:
            response = f"Git Agent Error: {error}"
        return {"response": response}

    async def run_task_agent(state: OrchestratorState) -> dict:
        response = await get_task_agent_response(task_agent, state["query"])
        return {"response": response}

    def select_agent(state: OrchestratorState) -> str:
        return state["route"]

    graph = StateGraph(OrchestratorState)
    graph.add_node("route_request", route_request)
    graph.add_node("git", run_git_agent)
    graph.add_node("task", run_task_agent)
    graph.add_edge(START, "route_request")
    graph.add_conditional_edges(
        "route_request",
        select_agent,
        {"git": "git", "task": "task"},
    )
    graph.add_edge("git", END)
    graph.add_edge("task", END)

    return graph.compile()


async def get_orchestrator_response(orchestrator, query: str) -> str:
    result = await orchestrator.ainvoke({"query": query})
    return result.get("response", "No response generated.")


__all__ = ["create_orchestrator", "get_orchestrator_response"]