from langchain_mcp_adapters.client import MultiServerMCPClient
import os

async def get_git_tools(repo_path: str):

    print("Repo path:", repo_path)
    print("Exists:", os.path.exists(repo_path))

    client = MultiServerMCPClient(
        {
            "git": {
                "command": "mcp-server-git",
                "args": ["-r", repo_path],
                "transport": "stdio",
            }
        }
    )

    print("Loading tools...")
    tools = await client.get_tools()
    print("Loaded tools:", len(tools))

    return tools