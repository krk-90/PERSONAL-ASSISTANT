from langchain_mcp_adapters.client import MultiServerMCPClient
import os
import shutil


async def get_git_tools(repo_path: str):

    print("=" * 50)
    print("REPO PATH:", repo_path)
    print("EXISTS:", os.path.exists(repo_path))
    print("git:", shutil.which("git"))
    print("mcp-server-git:", shutil.which("mcp-server-git"))
    print("=" * 50)

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

    for tool in tools:
        print("Tool:", tool.name)

    return tools