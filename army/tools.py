"""Built-in tools. Safe by default: file access is sandboxed to ARMY_WORKDIR (default: current dir)."""
from __future__ import annotations

import ast
import re
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


def outputs_dir() -> Path:
    d = workdir() / "outputs"
    d.mkdir(parents=True, exist_ok=True)
    return d


@tool
def write_file(filename: str, content: str) -> str:
    """Save text (Markdown, HTML, CSV, JSON...) to the outputs/ folder and return its path."""
    name = Path(filename).name
    if not name or name.startswith("."):
        raise ValueError("give a plain file name like report.md")
    p = outputs_dir() / name
    p.write_text(content)
    return f"saved {p.relative_to(workdir())} ({len(content):,} chars)"


@tool
def git_log(path: str = ".", n: int = 20) -> str:
    """Recent git commits touching a path: hash, date, author and message."""
    safe_path(path)
    out = subprocess.run(
        ["git", "log", f"-{int(n)}", "--date=short", "--pretty=format:%h %ad %an: %s", "--", path],
        cwd=workdir(), capture_output=True, text=True, timeout=30,
    )
    return out.stdout or out.stderr or "(no history)"


@tool
def git_blame(path: str, start: int = 1, end: int = 40) -> str:
    """Who last changed each line of a file and in which commit (line range)."""
    safe_path(path)
    out = subprocess.run(
        ["git", "blame", "--date=short", "-L", f"{int(start)},{int(end)}", "--", path],
        cwd=workdir(), capture_output=True, text=True, timeout=30,
    )
    return (out.stdout or out.stderr)[:15000]


@tool
def git_show(commit: str) -> str:
    """Show a commit's message and diff."""
    if commit.startswith("-"):
        raise ValueError("invalid commit")
    out = subprocess.run(["git", "show", "--stat", "--patch", commit, "--"], cwd=workdir(), capture_output=True, text=True, timeout=30)
    return (out.stdout or out.stderr)[:15000]


def _sqlite(db: str):
    import sqlite3

    return sqlite3.connect(f"file:{safe_path(db)}?mode=ro", uri=True)


@tool
def sql_schema(db: str) -> str:
    """List the tables and columns of a SQLite database (read-only)."""
    con = _sqlite(db)
    rows = con.execute("SELECT name, sql FROM sqlite_master WHERE type IN ('table','view') ORDER BY name").fetchall()
    con.close()
    return "\n\n".join(f"{n}:\n{s}" for n, s in rows) or "no tables"


@tool
def sql_query(db: str, sql: str) -> str:
    """Run a read-only SELECT query on a SQLite database. Returns up to 50 rows."""
    if not sql.lstrip().lower().startswith(("select", "with")):
        raise PermissionError("only SELECT / WITH queries are allowed")
    con = _sqlite(db)
    cur = con.execute(sql)
    cols = [d[0] for d in cur.description or []]
    rows = cur.fetchmany(50)
    con.close()
    return " | ".join(cols) + "\n" + "\n".join(" | ".join(map(str, r)) for r in rows)


@tool
def read_pdf(path: str, max_pages: int = 30) -> str:
    """Extract text from a PDF (needs `pip install pypdf`). Pages are marked [page N]."""
    try:
        from pypdf import PdfReader
    except ImportError:
        raise ImportError("read_pdf needs the optional package pypdf: pip install pypdf") from None
    reader = PdfReader(str(safe_path(path)))
    return "\n".join(f"[page {i}]\n{p.extract_text() or ''}" for i, p in enumerate(reader.pages[: int(max_pages)], 1))[:40000]


@tool
def search_mailbox(path: str, query: str, n: int = 10) -> str:
    """Search an .mbox email export for messages matching words in from/subject/body."""
    import mailbox

    terms = [t for t in re.findall(r"\w+", query.lower()) if len(t) > 2]
    box = mailbox.mbox(str(safe_path(path)), create=False)
    messages = list(box)
    box.close()
    scored = []
    for msg in messages:
        body = msg.get_payload(decode=True) if not msg.is_multipart() else next(
            (p.get_payload(decode=True) for p in msg.walk() if p.get_content_type() == "text/plain"), b""
        )
        body = (body or b"").decode("utf-8", "replace")
        blob = f"{msg['from']} {msg['subject']} {body}".lower()
        # rank by how many query words (or their stems) appear, so natural queries still match
        score = sum(1 for t in terms if t in blob or t[:5] in blob)
        if score:
            scored.append((score, f"From: {msg['from']}\nDate: {msg['date']}\nSubject: {msg['subject']}\n{body[:800]}"))
    hits = [text for _, text in sorted(scored, key=lambda x: -x[0])[: int(n)]]
    return "\n\n---\n\n".join(hits) or "no matching emails"


@tool
def read_transcript(path: str) -> str:
    """Read a subtitle/transcript file (.vtt or .srt) as clean text with [mm:ss] markers."""
    text = safe_path(path).read_text(errors="replace")
    out, stamp = [], ""
    for line in text.splitlines():
        line = line.strip()
        m = re.match(r"(\d{2}):(\d{2}):(\d{2})[.,]\d{3}\s+-->", line)
        if m:
            h, mi, s = map(int, m.groups())
            stamp = f"[{h * 60 + mi:02d}:{s:02d}]"
        elif line and not line.isdigit() and line != "WEBVTT":
            out.append(f"{stamp} {line}" if stamp else line)
            stamp = ""
    return "\n".join(out)[:40000]


@tool
def text_stats(text: str) -> str:
    """Word count, sentence count, average sentence length and estimated reading time."""
    words = re.findall(r"\b\w+\b", text)
    sentences = [s for s in re.split(r"[.!?]+", text) if s.strip()]
    avg = len(words) / max(1, len(sentences))
    return f"words={len(words)} sentences={len(sentences)} avg_sentence_words={avg:.1f} reading_time_min={len(words) / 230:.1f}"
