"""Call edammcp tools over stdio, no LLM. Usage: edam_smoke.py <edammcp-dir>"""
import asyncio, json, re, sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

URI = re.compile(r"edamontology\.org/((?:topic|operation|data|format)_\d{4})")


async def call(s, tool, request):
    res = await s.call_tool(tool, {"request": request})
    assert not res.isError, res.content
    return res.content[0].text


async def main():
    params = StdioServerParameters(command="uv", args=["--directory", sys.argv[1], "run", "edam-mcp"])
    async with stdio_client(params) as (r, w), ClientSession(r, w) as s:
        await s.initialize()
        names = {t.name for t in (await s.list_tools()).tools}
        assert "map_to_edam_concept_tool" in names, names
        mapped = await call(s, "map_to_edam_concept_tool", {"description": "sequence alignment tool"})
        ids = URI.findall(mapped)
        print("map ->", ids[:5])
        assert ids, mapped[:500]
        if "--offline" not in sys.argv:
            bwa = await call(s, "query_biotools_by_text_exact_match_tool", {"biotools_id": "bwa"})
            print("biotools ->", bwa[:200])
            assert "bwa" in bwa.lower(), bwa[:500]
        print("ok")


asyncio.run(main())
