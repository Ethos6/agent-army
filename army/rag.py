"""Zero-dependency retrieval: BM25 over line-numbered chunks, so every answer can cite file:line."""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .agent import Tool, tool

TEXT_SUFFIXES = {".md", ".txt", ".rst", ".py", ".js", ".ts", ".html", ".csv", ".json", ".toml", ".yaml", ".yml"}
_WORD = re.compile(r"\w+")
_CJK = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af]")
STOP = set("a an and are as at be by for from has have in is it of on or that the to was were will with".split())


def tokenize(text: str) -> list[str]:
    """Lower-cased Unicode words; Chinese/Japanese/Korean runs (no spaces) become character bigrams."""
    out = []
    for w in _WORD.findall(text.lower()):
        if w in STOP:
            continue
        if _CJK.search(w):
            chars = [c for c in w if not c.isspace()]
            out += chars if len(chars) == 1 else ["".join(chars[i:i + 2]) for i in range(len(chars) - 1)]
        else:
            out.append(w)
    return out


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
    def from_folder(cls, folder: str | Path, lines_per_chunk: int = 12, overlap: int = 3) -> "BM25Index":
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


def search_tool(index, name: str = "search_docs") -> Tool:
    @tool(name=name)
    def search(query: str, k: int = 4) -> str:
        """Search the knowledge base. Returns passages tagged with [file:lines] for citation."""
        hits = index.search(query, int(k))
        if not hits:
            return "No matching passages. Try different keywords."
        return "\n\n".join(f"[{c.cite}] (score {s:.2f})\n{c.text}" for s, c in hits)

    return search


# ---------------------------------------------------------------- embeddings (optional)
import json as _json
import os as _os
import urllib.request as _ur


def embed(texts: list[str], spec: str | None = None) -> list[list[float]]:
    """Embed texts with ARMY_EMBED_MODEL="provider:model" (openai, gemini, ollama, or any OpenAI-compatible)."""
    spec = spec or _os.environ.get("ARMY_EMBED_MODEL") or (
        "openai:text-embedding-3-small" if _os.environ.get("OPENAI_API_KEY")
        else "gemini:text-embedding-004" if _os.environ.get("GEMINI_API_KEY")
        else "ollama:nomic-embed-text"
    )
    provider, _, model = spec.partition(":")

    def post(url, payload, headers):
        req = _ur.Request(url, data=_json.dumps(payload).encode(), headers={"content-type": "application/json", **headers})
        with _ur.urlopen(req, timeout=120) as r:
            return _json.loads(r.read())

    out: list[list[float]] = []
    for i in range(0, len(texts), 64):
        batch = texts[i : i + 64]
        if provider == "gemini":
            r = post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:batchEmbedContents",
                {"requests": [{"model": f"models/{model}", "content": {"parts": [{"text": t}]}} for t in batch]},
                {"x-goog-api-key": _os.environ["GEMINI_API_KEY"]},
            )
            out += [e["values"] for e in r["embeddings"]]
        elif provider == "ollama":
            base = _os.environ.get("OLLAMA_HOST", "http://localhost:11434")
            out += post(f"{base}/api/embed", {"model": model, "input": batch}, {})["embeddings"]
        else:
            base = _os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
            r = post(f"{base}/embeddings", {"model": model, "input": batch}, {"authorization": f"Bearer {_os.environ.get('OPENAI_API_KEY', '')}"})
            out += [d["embedding"] for d in sorted(r["data"], key=lambda d: d["index"])]
    return out


def _cos(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


class VectorIndex:
    """Semantic search over the same chunks as a BM25Index. Embeds lazily on first search."""

    def __init__(self, chunks: list[Chunk], spec: str | None = None):
        self.chunks, self.spec, self.vectors = chunks, spec, None

    def search(self, query: str, k: int = 4) -> list[tuple[float, Chunk]]:
        if self.vectors is None:
            self.vectors = embed([c.text for c in self.chunks], self.spec)
        qv = embed([query], self.spec)[0]
        scored = sorted(((_cos(qv, v), c) for v, c in zip(self.vectors, self.chunks)), key=lambda x: -x[0])
        return scored[:k]


class HybridIndex:
    """Reciprocal-rank fusion of keyword (BM25) and semantic (embedding) results."""

    def __init__(self, bm25: BM25Index, spec: str | None = None, k_rrf: int = 60):
        self.bm25, self.vec, self.k_rrf = bm25, VectorIndex(bm25.chunks, spec), k_rrf
        self.chunks = bm25.chunks

    def search(self, query: str, k: int = 4) -> list[tuple[float, Chunk]]:
        scores: dict[int, float] = {}
        ref: dict[int, Chunk] = {}
        for results in (self.bm25.search(query, k * 3), self.vec.search(query, k * 3)):
            for rank, (_, c) in enumerate(results):
                scores[id(c)] = scores.get(id(c), 0) + 1 / (self.k_rrf + rank + 1)
                ref[id(c)] = c
        return sorted(((s, ref[i]) for i, s in scores.items()), key=lambda x: -x[0])[:k]


_REPO = Path(__file__).resolve().parent.parent


def resolve_folder(docs: str | Path) -> Path:
    """Resolve a docs folder relative to the current directory, falling back to the repo root (for bundled examples)."""
    p = Path(docs)
    if p.is_dir():
        return p
    if (_REPO / p).is_dir():
        return _REPO / p
    raise FileNotFoundError(f"docs folder not found: {docs}")


def index_folder(docs: str | Path, **kw) -> BM25Index:
    return BM25Index.from_folder(resolve_folder(docs), **kw)
