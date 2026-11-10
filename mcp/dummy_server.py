from mcp.server.fastmcp import FastMCP

mcp = FastMCP("dummy")


@mcp.tool()
def secret_word() -> str:
    """Return the secret word."""
    return "PURPLE-OTTER-4217"


@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b


@mcp.tool()
def echo(text: str) -> str:
    """Return the text unchanged."""
    return text


if __name__ == "__main__":
    mcp.run()
