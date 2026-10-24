"""Minimal Model Context Protocol client (stdio transport), stdlib only.

    server = MCPServer(["npx", "-y", "@modelcontextprotocol/server-filesystem", "."])
    agent = Agent(..., tools=server.tools())          # lazy: the server starts on first use

`tools()` returns two generic tools (list + call) so the agent can use any MCP server without
knowing its tools in advance. `as_tools()` instead starts the server now and wraps each MCP tool.
"""
from __future__ import annotations

import json
import os
import queue
import shlex
import subprocess
import threading

from .agent import Tool, tool

PROTOCOL_VERSION = "2024-11-05"


class MCPError(RuntimeError):
    pass


class MCPServer:
    def __init__(self, command: list[str] | str, env: dict | None = None, name: str = "mcp", timeout: float = 60):
        self.command = shlex.split(command) if isinstance(command, str) else list(command)
        self.env = {**os.environ, **(env or {})}
        self.name = name
        self.timeout = timeout
        self.proc: subprocess.Popen | None = None
        self._id = 0
        self._lock = threading.Lock()
        self._start_lock = threading.Lock()  # concurrent first calls must start exactly one server
        self._ready = False
        self._waiting: dict[int, queue.Queue] = {}
        self._tools: list[dict] | None = None

    # -- transport
    def _start(self):
        with self._start_lock:
            if self.proc and self.proc.poll() is None and self._ready:
                return
            if self.proc:  # dead, or alive but never finished initializing: start fresh
                self.close()
            try:
                self.proc = subprocess.Popen(
                    self.command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                    text=True, bufsize=1, env=self.env,
                )
            except FileNotFoundError:
                raise MCPError(f"cannot start MCP server: {self.command[0]} not found") from None
            # One reader thread per process routes each reply to the request waiting for it,
            # so a request that timed out can never swallow the reply meant for the next one.
            self._waiting = {}
            threading.Thread(target=self._read_loop, args=(self.proc, self._waiting), daemon=True).start()
            try:
                self._request("initialize", {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": "agent-army", "version": "1"},
                })
                self._notify("notifications/initialized")
            except Exception:
                self.close()  # never leave a half-initialized server behind
                raise
            self._ready = True

    def _read_loop(self, proc, waiting: dict):
        try:
            for line in proc.stdout:
                self._route(line, waiting)
        except (ValueError, OSError):  # stdout closed by close()
            pass
        for box in list(waiting.values()):  # server exited: wake everyone waiting on THIS process
            box.put({"error": {"message": "server exited"}})

    @staticmethod
    def _route(line: str, waiting: dict):
        line = line.strip()
        if not line:
            return
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            return  # servers sometimes log to stdout
        if isinstance(msg, dict) and ("result" in msg or "error" in msg):
            box = waiting.pop(msg.get("id"), None)
            if box:
                box.put(msg)

    def _write(self, msg: dict):
        try:
            self.proc.stdin.write(json.dumps(msg) + "\n")
            self.proc.stdin.flush()
        except (BrokenPipeError, OSError):
            raise MCPError(f"{self.name}: server is not running") from None

    def _notify(self, method: str, params: dict | None = None):
        self._write({"jsonrpc": "2.0", "method": method, **({"params": params} if params else {})})

    def _request(self, method: str, params: dict | None = None):
        with self._lock:
            self._id += 1
            rid = self._id
        box: queue.Queue = queue.Queue(maxsize=1)
        waiting = self._waiting
        waiting[rid] = box
        try:
            self._write({"jsonrpc": "2.0", "id": rid, "method": method, "params": params or {}})
        except MCPError:
            waiting.pop(rid, None)
            raise
        try:
            result = box.get(timeout=self.timeout)
        except queue.Empty:
            waiting.pop(rid, None)
            raise MCPError(f"{self.name}: no response to {method} within {self.timeout}s") from None
        if "error" in result:
            raise MCPError(f"{self.name}: {result['error'].get('message')}")
        return result["result"]

    # -- API
    def list_tools(self) -> list[dict]:
        self._start()
        if self._tools is None:
            self._tools = self._request("tools/list").get("tools", [])
        return self._tools

    def call(self, name: str, arguments: dict | None = None) -> str:
        self._start()
        r = self._request("tools/call", {"name": name, "arguments": arguments or {}})
        parts = []
        for c in r.get("content", []):
            parts.append(c.get("text") if c.get("type") == "text" else f"[{c.get('type')} content]")
        text = "\n".join(p for p in parts if p)
        return ("ERROR: " if r.get("isError") else "") + text

    def close(self):
        self._ready = False
        if self.proc:
            if self.proc.poll() is None:
                self.proc.terminate()
                try:
                    self.proc.wait(5)
                except subprocess.TimeoutExpired:
                    self.proc.kill()
            for stream in (self.proc.stdin, self.proc.stdout):
                if stream:
                    stream.close()
            self.proc = None

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    def tools(self) -> list[Tool]:
        server = self

        @tool(name=f"{self.name}_list_tools")
        def list_tools() -> str:
            """List the tools this MCP server offers, with their argument schemas."""
            lines = []
            for t in server.list_tools():
                props = (t.get("inputSchema") or {}).get("properties", {})
                req = set((t.get("inputSchema") or {}).get("required", []))
                args = ", ".join(f"{k}{'' if k in req else '?'}: {v.get('type', 'any')}" for k, v in props.items())
                lines.append(f"- {t['name']}({args}): {(t.get('description') or '').splitlines()[0][:200] if t.get('description') else ''}")
            return "\n".join(lines) or "no tools"

        @tool(name=f"{self.name}_call")
        def call(tool_name: str, arguments: dict = {}) -> str:  # noqa: B006 - schema default only
            """Call one of this MCP server's tools by name with a JSON object of arguments."""
            return server.call(tool_name, arguments)

        return [list_tools, call]

    def as_tools(self) -> list[Tool]:
        out = []
        for t in self.list_tools():
            props = (t.get("inputSchema") or {}).get("properties", {})
            name = t["name"]
            fn = (lambda n: lambda **kw: self.call(n, kw))(name)
            out.append(Tool(name, (t.get("description") or "").split("\n")[0], fn, {k: v.get("type", "any") for k, v in props.items()}))
        return out
