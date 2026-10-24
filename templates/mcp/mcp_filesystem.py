"""Filesystem MCP Agent

Organize, search and summarize files through the official filesystem MCP server, which restricts
access to the folders you allow. Ask things like "find every TODO in my notes and group them by
project" or "summarize the markdown files in this folder".
"""
from army import Agent
from army.mcp import MCPServer

META = {
    "category": "mcp",
    "description": "Search, summarize and organize files in allowed folders through the filesystem MCP server.",
    "example": "Summarize every markdown file in the examples folder",
    "needs": "Node.js (npx).",
}
EVALS = [{"input": "How many files are in the examples/knowledge-base folder and what are they about?", "must_contain": ["pricing"], "max_seconds": 180}]


def build(llm=None, folder: str = "."):
    fs = MCPServer(["npx", "-y", "@modelcontextprotocol/server-filesystem", folder], name="fs")
    return Agent(
        name="mcp-filesystem",
        instructions=f"""You manage files in {folder} via MCP. Call `fs_list_tools` first. Prefer read and search tools; before any
write, move or edit, describe exactly what you will change and only proceed if the user's request clearly asks for it.
Cite file paths in your answer.""",
        tools=fs.tools(),
        llm=llm,
        max_steps=15,
    )
