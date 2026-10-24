"""Built-in tools. Safe by default: file access is sandboxed to ARMY_WORKDIR (default: current dir)."""
from __future__ import annotations

import ast
import csv
import operator
import os
import statistics
import subprocess
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

from .agent import tool


def workdir() -> Path:
    return Path(os.environ.get("ARMY_WORKDIR", ".")).resolve()


def safe_path(path: str) -> Path:
    """Resolve a path and refuse anything outside the sandbox root."""
    root = workdir()
    p = (root / path).resolve()
    if p != root and root not in p.parents:
        raise PermissionError(f"'{path}' is outside the sandbox ({root}). Set ARMY_WORKDIR to allow it.")
    return p


class _TextExtractor(HTMLParser):
    SKIP = {"script", "style", "noscript", "svg", "nav", "footer", "header", "form"}

    def __init__(self):
        super().__init__()
        self.parts: list[str] = []
        self.title = ""
        self._skip = 0
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip += 1
        self._in_title = tag == "title"

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip:
            self._skip -= 1
        if tag in {"p", "div", "li", "h1", "h2", "h3", "h4", "tr", "br"}:
            self.parts.append("\n")
        self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data.strip()
        elif not self._skip and data.strip():
            self.parts.append(data.strip() + " ")


def html_to_text(html: str) -> tuple[str, str]:
    parser = _TextExtractor()
    parser.feed(html)
    lines = [" ".join(line.split()) for line in "".join(parser.parts).splitlines()]
    return parser.title, "\n".join(line for line in lines if line)


@tool
def fetch_url(url: str) -> str:
    """Download a web page and return its title and readable text."""
    if not url.startswith(("http://", "https://")):
        raise ValueError("url must start with http:// or https://")
    req = urllib.request.Request(url, headers={"user-agent": "Mozilla/5.0 (agent-army)"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read(3_000_000).decode(resp.headers.get_content_charset() or "utf-8", "replace")
    title, text = html_to_text(raw)
    return f"URL: {url}\nTITLE: {title}\n\n{text[:12000]}"


@tool
def read_file(path: str) -> str:
    """Read a text file inside the sandbox (returns at most 20,000 characters)."""
    return safe_path(path).read_text(errors="replace")[:20000]


@tool
def list_files(path: str = ".") -> str:
    """List files under a folder inside the sandbox (max 200 entries)."""
    root = safe_path(path)
    files = sorted(
        str(p.relative_to(workdir())) for p in root.rglob("*") if p.is_file() and ".git" not in p.parts
    )
    return "\n".join(files[:200]) or "(empty)"


_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
    ast.Pow: operator.pow, ast.Mod: operator.mod, ast.FloorDiv: operator.floordiv,
    ast.USub: operator.neg, ast.UAdd: operator.pos,
}


def _eval(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        if isinstance(node.op, ast.Pow) and abs(_eval(node.right)) > 100:
            raise ValueError("exponent too large")
        return _OPS[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.operand))
    raise ValueError("only numbers and + - * / // % ** are allowed")


@tool
def calculate(expression: str) -> str:
    """Evaluate an arithmetic expression exactly, e.g. "(1200 - 950) / 950 * 100"."""
    return str(_eval(ast.parse(expression, mode="eval").body))


def _read_rows(path: str) -> list[dict]:
    with open(safe_path(path), newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _num(v):
    try:
        return float(str(v).replace(",", "").replace("$", "").strip())
    except ValueError:
        return None


@tool
def describe_csv(path: str) -> str:
    """Show a CSV's columns, row count, sample rows and numeric summaries."""
    rows = _read_rows(path)
    if not rows:
        return "CSV is empty."
    lines = [f"rows: {len(rows)}", f"columns: {', '.join(rows[0])}", "sample:"]
    lines += [f"  {r}" for r in rows[:3]]
    for col in rows[0]:
        nums = [n for n in (_num(r[col]) for r in rows) if n is not None]
        if len(nums) >= max(1, len(rows) // 2):
            lines.append(
                f"{col}: min={min(nums):g} max={max(nums):g} mean={statistics.fmean(nums):,.2f} sum={sum(nums):g}"
            )
        else:
            distinct = {r[col] for r in rows}
            lines.append(f"{col}: {len(distinct)} distinct values, e.g. {sorted(distinct)[:5]}")
    return "\n".join(lines)


@tool
def aggregate_csv(path: str, value_column: str, group_by: str = "", op: str = "sum") -> str:
    """Aggregate a numeric column (op: sum|mean|min|max|count), optionally grouped by another column."""
    funcs = {"sum": sum, "mean": statistics.fmean, "min": min, "max": max, "count": len}
    if op not in funcs:
        raise ValueError(f"op must be one of {list(funcs)}")
    groups: dict[str, list[float]] = {}
    for r in _read_rows(path):
        n = _num(r.get(value_column))
        if n is not None:
            groups.setdefault(r.get(group_by, "") if group_by else "ALL", []).append(n)
    out = sorted(((k, funcs[op](v)) for k, v in groups.items()), key=lambda kv: -kv[1])
    return "\n".join(f"{k}: {v:,.2f}" for k, v in out) or "no numeric values found"


@tool
def git_diff(ref: str = "HEAD") -> str:
    """Show the git diff of the working tree against a ref (default HEAD)."""
    if ref.startswith("-"):
        raise ValueError("invalid ref")
    out = subprocess.run(
        ["git", "diff", "--no-color", ref, "--"], cwd=workdir(), capture_output=True, text=True, timeout=30
    )
    return (out.stdout or out.stderr or "(no changes)")[:20000]
