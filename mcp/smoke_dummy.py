"""Call the dummy server over stdio without any LLM."""
import asyncio, sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    params = StdioServerParameters(command=sys.executable, args=[sys.argv[1]])
    async with stdio_client(params) as (r, w), ClientSession(r, w) as s:
        await s.initialize()
        names = sorted(t.name for t in (await s.list_tools()).tools)
        assert names == ["add", "echo", "secret_word"], names
        word = (await s.call_tool("secret_word", {})).content[0].text
        total = (await s.call_tool("add", {"a": 17, "b": 25})).content[0].text
        assert word == "PURPLE-OTTER-4217" and total == "42", (word, total)
        print("ok", names, word, total)


asyncio.run(main())
