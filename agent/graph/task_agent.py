import sys
from pathlib import Path

if __package__ in {None, ""}:
	sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import StructuredTool

from mcp_server.tools import (
	add_task,
	complete_task,
	delete_task,
	get_task,
	get_tasks,
	update_task,
)


def _get_task_tools() -> list[StructuredTool]:
	return [
		StructuredTool.from_function(add_task),
		StructuredTool.from_function(get_tasks),
		StructuredTool.from_function(get_task),
		StructuredTool.from_function(update_task),
		StructuredTool.from_function(complete_task),
		StructuredTool.from_function(delete_task),
	]


async def create_task_agent(llm):
	tools = _get_task_tools()

	prompt = ChatPromptTemplate.from_messages(
		[
			(
				"system",
				"""
You are an expert task manager assistant.

Available tools:
- add_task: create a task
- get_tasks: list tasks, optionally filtered by status or priority
- get_task: retrieve one task by id
- update_task: update task fields
- complete_task: mark a task as completed
- delete_task: delete a task by id

Rules:
- Automatically choose the most appropriate task tool.
- Use tools before answering questions about task data.
- Ask for missing information when a task action needs it.
- Never invent a task id or claim an action succeeded without using the tool.
- Summarize tool results clearly and concisely.
""",
			),
			("human", "{input}"),
			("placeholder", "{agent_scratchpad}"),
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
		handle_parsing_errors=True,
		max_iterations=8,
	)


async def get_task_agent_response(agent: AgentExecutor, query: str) -> str:
	try:
		response = await agent.ainvoke({"input": query})
		return response.get("output", "No response generated.")
	except Exception as error:
		return f"Task Agent Error: {error}"


__all__ = ["create_task_agent", "get_task_agent_response"]
