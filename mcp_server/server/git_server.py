import os
from langchain_mcp_adapters.client import MultiServerMCPClient

async def get_git_tools():
    client = MultiServerMCPClient(
        {
            "git": {
                "command": "mcp-server-git",
                "args": ["-r", os.getcwd()],
                "transport": "stdio",
            }
        }
    )

    return await client.get_tools()