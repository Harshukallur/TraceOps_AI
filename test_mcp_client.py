
import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    project_root = Path(__file__).resolve().parent
    python_exe = project_root / ".venv" / "Scripts" / "python.exe"

    server_params = StdioServerParameters(
        command=str(python_exe),
        args=["-m", "app.mcp_server"],
        cwd=str(project_root),
    )

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            tools = await session.list_tools()
            print("Tools discovered:", [tool.name for tool in tools.tools])

            result = await session.call_tool(
                "get_service_details",
                {"service_name": "Payment API"},
            )

            print("\nPayment API tool result:")
            for item in result.content:
                if hasattr(item, "text"):
                    print(item.text)


if __name__ == "__main__":
    asyncio.run(main())
