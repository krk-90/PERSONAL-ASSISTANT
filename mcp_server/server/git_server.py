from langchain_mcp_adapters.client import MultiServerMCPClient


async def get_git_tools(repo_path: str):
    client = MultiServerMCPClient(
        {
            "git": {
                "command": "mcp-server-git",
                "args": ["-r", repo_path],
                "transport": "stdio",
            }
        }
    )

    return await client.get_tools()