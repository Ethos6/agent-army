"""A tiny MCP server over stdio used by the test suite (no Node.js needed)."""
import json
import sys

TOOLS = [
    {"name": "echo", "description": "Echo text back.", "inputSchema": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}},
    {"name": "add", "description": "Add two numbers.", "inputSchema": {"type": "object", "properties": {"a": {"type": "number"}, "b": {"type": "number"}}}},
]

for line in sys.stdin:
    msg = json.loads(line)
    if "id" not in msg:
        continue  # notification
    method, params = msg["method"], msg.get("params", {})
    if method == "initialize":
        result = {"protocolVersion": params.get("protocolVersion"), "capabilities": {"tools": {}}, "serverInfo": {"name": "fake", "version": "1"}}
    elif method == "tools/list":
        result = {"tools": TOOLS}
    elif method == "tools/call":
        args = params.get("arguments", {})
        if params["name"] == "echo":
            text = args.get("text", "")
        elif params["name"] == "add":
            text = str(args.get("a", 0) + args.get("b", 0))
        else:
            print(json.dumps({"jsonrpc": "2.0", "id": msg["id"], "error": {"code": -32602, "message": "unknown tool"}}), flush=True)
            continue
        result = {"content": [{"type": "text", "text": text}]}
    else:
        result = {}
    print("log line that is not json", flush=True)  # servers sometimes print noise; the client must skip it
    print(json.dumps({"jsonrpc": "2.0", "id": msg["id"], "result": result}), flush=True)
