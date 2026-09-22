import os
from typing import Literal
import re

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

from agent.graph.git_agent import create_git_agent, get_git_agent_response
from agent.graph.task_agent import create_task_agent, get_task_agent_response
from agent.memory.agent_memory import LongTermMemory
from agent.rag.pipeline import RAGPipeline


class RouteDecision(BaseModel):
    agent: Literal["git", "task", "rag"] = Field(
        description="The specialist that should handle the user's request."
    )
    confidence: float = Field(
        default=0.0,
        description="Confidence score from 0 to 1."
    )


class OrchestratorState(TypedDict, total=False):
    query: str
    route: Literal["git", "task", "rag"]
    response: str
    memory_context: str


ROUTER_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
You route requests to one specialist.

Choose git for:
- commits
- branches
- checkout
- repository history
- git status
- git diff
- code inspection
- repository file analysis

Choose task for:
- task creation
- task lookup
- task updates
- todo management
- reminders
- task completion
- task deletion

Choose rag for:
- questions about repository documentation or source files
- general questions that are not git or task operations
- answers that should be grounded in indexed documents

Return only the selected specialist and confidence.
""",
        ),
        ("human", "{query}"),
    ]
)

TASK_ID_PATTERN = re.compile(r"\b[a-f0-9]{32}\b", re.IGNORECASE)

TASK_KEYWORDS = {
    "task",
    "tasks",
    "todo",
    "pending",
    "complete",
    "completed",
    "finish",
    "done",
    "priority",
    "assignee",
    "due",
    "deadline",
    "reminder",
}

TASK_PHRASES = [
    "add task",
    "create task",
    "new task",
    "show task",
    "list task",
    "list tasks",
    "task details",
    "delete task",
    "update task",
    "mark task",
    "finish task",
]

GIT_KEYWORDS = {
    "git",
    "commit",
    "commits",
    "branch",
    "branches",
    "checkout",
    "merge",
    "rebase",
    "repository",
    "repo",
    "diff",
    "status",
    "stash",
    "tag",
    "pull",
    "push",
    "file history",
    "blame",
}

GIT_PHRASES = [
    "git status",
    "git diff",
    "git log",
    "show commits",
    "checkout branch",
    "create branch",
]


def deterministic_route(query: str) -> str | None:

    q = query.lower().strip()

    if TASK_ID_PATTERN.search(q):
        if any(
            word in q
            for word in [
                "task",
                "done",
                "complete",
                "status",
                "delete",
                "update",
                "what",
            ]
        ):
            return "task"
        
    if any(phrase in q for phrase in TASK_PHRASES):
        return "task"

    task_hits = sum(keyword in q for keyword in TASK_KEYWORDS)

    if task_hits >= 1:
        return "task"

    if any(phrase in q for phrase in GIT_PHRASES):
        return "git"

    git_hits = sum(keyword in q for keyword in GIT_KEYWORDS)

    if git_hits >= 1:
        return "git"

    return None


async def create_orchestrator(
    llm: BaseChatModel,
    repo_path: str,
    user_id: str = "default-user",
    memory: LongTermMemory | None = None,
):
    os.environ["TASK_USER_ID"] = user_id
    task_agent = await create_task_agent(llm)

    router = ROUTER_PROMPT | llm.with_structured_output(RouteDecision)

    git_agent = None
    rag_pipeline = RAGPipeline.from_path(llm, repo_path)
    long_term_memory = memory or LongTermMemory(user_id)

    async def load_memory(state: OrchestratorState) -> dict:
        memories = await long_term_memory.search(state["query"])
        return {
            "memory_context": long_term_memory.format_context(memories)
        }

    async def route_request(state: OrchestratorState) -> dict:
        query = state["query"]

        route = deterministic_route(query)

        if route:
            print(
                f"[ROUTER] deterministic route={route} query='{query}'"
            )
            return {"route": route}

        decision = await router.ainvoke({"query": query})

        print(
            f"[ROUTER] llm route={decision.agent} "
            f"confidence={decision.confidence:.2f}"
        )

        return {"route": decision.agent}

    async def run_git_agent(state: OrchestratorState) -> dict:
        nonlocal git_agent

        try:
            if git_agent is None:
                git_agent = await create_git_agent(
                    llm,
                    repo_path,
                )

            query = (
                state.get("memory_context", "")
                + state["query"]
            )

            response = await get_git_agent_response(
                git_agent,
                query,
            )

        except Exception as error:
            response = f"Git Agent Error: {error}"

        return {"response": response}

    async def run_task_agent(state: OrchestratorState) -> dict:
        query = (
            state.get("memory_context", "")
            + state["query"]
        )

        response = await get_task_agent_response(
            task_agent,
            query,
        )

        return {"response": response}

    async def run_rag_agent(state: OrchestratorState) -> dict:
        try:
            response = await rag_pipeline.ask(state["query"])
        except Exception as error:
            response = f"RAG Agent Error: {error}"
        return {"response": response}

    async def save_memory(state: OrchestratorState) -> dict:
        await long_term_memory.add(
            state["query"],
            state["response"],
        )
        return {}

    def select_agent(state: OrchestratorState) -> str:
        return state["route"]

    graph = StateGraph(OrchestratorState)

    graph.add_node("load_memory", load_memory)
    graph.add_node("route_request", route_request)
    graph.add_node("git", run_git_agent)
    graph.add_node("task", run_task_agent)
    graph.add_node("rag", run_rag_agent)
    graph.add_node("save_memory", save_memory)

    graph.add_edge(START, "load_memory")
    graph.add_edge("load_memory", "route_request")

    graph.add_conditional_edges(
        "route_request",
        select_agent,
        {
            "git": "git",
            "task": "task",
            "rag": "rag",
        },
    )

    graph.add_edge("git", "save_memory")
    graph.add_edge("task", "save_memory")
    graph.add_edge("rag", "save_memory")
    graph.add_edge("save_memory", END)

    return graph.compile()


async def get_orchestrator_response(orchestrator, query: str) -> str:
    result = await orchestrator.ainvoke(
        {"query": query}
    )

    return result.get(
        "response",
        "No response generated."
    )


__all__ = [
    "create_orchestrator",
    "get_orchestrator_response",
]