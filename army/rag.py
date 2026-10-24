"""Zero-dependency retrieval: BM25 over line-numbered chunks, so every answer can cite file:line."""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .agent import Tool, tool

TEXT_SUFFIXES = {".md", ".txt", ".rst", ".py", ".js", ".ts", ".html", ".csv", ".json", ".toml", ".yaml", ".yml"}
_WORD = re.compile(r"[a-z0-9]+")
STOP = set("a an and are as at be by for from has have in is it of on or that the to was were will with".split())


def tokenize(text: str) -> list[str]:
    return [w for w in _WORD.findall(text.lower()) if w not in STOP]


@dataclass
class Chunk:
    source: str
    start: int
    end: int
    text: str

    @property
    def cite(self) -> str:
        return f"{self.source}:{self.start}-{self.end}"


class BM25Index:
    def __init__(self, chunks: list[Chunk], k1: float = 1.5, b: float = 0.75):
        self.chunks = chunks
        self.k1, self.b = k1, b
        self.tf = [Counter(tokenize(c.text)) for c in chunks]
        self.lens = [sum(t.values()) for t in self.tf]
        self.avg = (sum(self.lens) / len(self.lens)) if chunks else 0
        df = Counter(term for t in self.tf for term in t)
        n = len(chunks)
        self.idf = {term: math.log(1 + (n - f + 0.5) / (f + 0.5)) for term, f in df.items()}

    @classmethod
    def from_folder(cls, folder: str | Path, lines_per_chunk: int = 30, overlap: int = 5) -> "BM25Index":
        folder = Path(folder)
        chunks: list[Chunk] = []
        step = max(1, lines_per_chunk - overlap)
        for path in sorted(folder.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            lines = path.read_text(errors="replace").splitlines()
            rel = str(path.relative_to(folder))
            for i in range(0, max(len(lines), 1), step):
                block = lines[i : i + lines_per_chunk]
                if any(line.strip() for line in block):
                    chunks.append(Chunk(rel, i + 1, i + len(block), "\n".join(block)))
                if i + lines_per_chunk >= len(lines):
                    break
        return cls(chunks)

    def search(self, query: str, k: int = 4) -> list[tuple[float, Chunk]]:
        terms = tokenize(query)
        scored = []
        for tf, length, chunk in zip(self.tf, self.lens, self.chunks):
            s = 0.0
            for term in terms:
                if term in tf:
                    f = tf[term]
                    s += self.idf[term] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * length / self.avg))
            if s > 0:
                scored.append((s, chunk))
        return sorted(scored, key=lambda sc: -sc[0])[:k]


def search_tool(index: BM25Index, name: str = "search_docs") -> Tool:
    @tool(name=name)
    def search(query: str, k: int = 4) -> str:
        """Search the knowledge base. Returns passages tagged with [file:lines] for citation."""
        hits = index.search(query, int(k))
        if not hits:
            return "No matching passages. Try different keywords."
        return "\n\n".join(f"[{c.cite}] (score {s:.2f})\n{c.text}" for s, c in hits)

    return search
