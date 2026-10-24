"""Long-term memory: a small JSON store with relevance-ranked recall, exposed to agents as tools.

    mem = Memory("travel")            # stored at $ARMY_HOME/memory/travel.json (default ~/.army)
    agent = Agent(..., tools=[*mem.tools()])

Several agents (even on different models) can share one Memory to share context.
"""
from __future__ import annotations

import json
import math
import os
import tempfile
import threading
import time
from contextlib import contextmanager
from collections import Counter
from pathlib import Path

from .agent import Tool, tool
from .rag import tokenize


def army_home() -> Path:
    return Path(os.environ.get("ARMY_HOME", Path.home() / ".army"))


class Memory:
    _locks: dict[str, threading.Lock] = {}

    def __init__(self, namespace: str = "default", path: str | Path | None = None):
        self.path = Path(path) if path else army_home() / "memory" / f"{namespace}.json"
        self._lock = Memory._locks.setdefault(str(self.path.resolve()), threading.Lock())
        self.items: list[dict] = self._load()

    @contextmanager
    def _exclusive(self):
        """Thread lock plus an OS file lock, so separate processes sharing a memory don't overwrite each other."""
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(str(self.path) + ".lock", "a") as lf:
                try:
                    import fcntl

                    fcntl.flock(lf, fcntl.LOCK_EX)
                except ImportError:  # Windows: the thread lock still protects one process
                    pass
                yield

    def _load(self) -> list[dict]:
        try:
            return json.loads(self.path.read_text()) if self.path.exists() else []
        except json.JSONDecodeError:
            return []

    def _save(self):
        # write to a temp file and rename, so a crash or a concurrent reader never sees a half-written file
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=".mem-", suffix=".json")
        with os.fdopen(fd, "w") as f:
            json.dump(self.items, f, indent=1, ensure_ascii=False)
        os.replace(tmp, self.path)

    def add(self, text: str, kind: str = "fact") -> int:
        with self._exclusive():
            self.items = self._load()  # pick up what other agents sharing this memory wrote
            return self._add(text, kind)

    def _add(self, text: str, kind: str) -> int:
        text = text.strip()
        for item in self.items:  # update instead of duplicating
            if item["text"].lower() == text.lower():
                item["ts"] = time.time()
                self._save()
                return item["id"]
        new_id = max((i["id"] for i in self.items), default=0) + 1
        self.items.append({"id": new_id, "text": text, "kind": kind, "ts": time.time()})
        self._save()
        return new_id

    def search(self, query: str, k: int = 5) -> list[dict]:
        self.items = self._load()
        terms = tokenize(query)
        if not terms:
            return sorted(self.items, key=lambda i: -i["ts"])[:k]
        df = Counter(t for i in self.items for t in set(tokenize(i["text"])))
        n = len(self.items) or 1
        scored = []
        for item in self.items:
            tf = Counter(tokenize(item["text"]))
            s = sum(tf[t] * math.log(1 + n / (1 + df[t])) for t in terms if t in tf)
            if s:
                age_days = (time.time() - item["ts"]) / 86400
                scored.append((s / (1 + age_days / 365), item))
        return [i for _, i in sorted(scored, key=lambda x: -x[0])[:k]]

    def remove(self, item_id: int) -> bool:
        with self._exclusive():
            self.items = self._load()
            before = len(self.items)
            self.items = [i for i in self.items if i["id"] != int(item_id)]
            self._save()
            return len(self.items) < before

    def tools(self) -> list[Tool]:
        mem = self

        @tool
        def remember(fact: str, kind: str = "fact") -> str:
            """Save a durable fact or preference about the user for future conversations (kind: fact|preference|goal)."""
            return f"remembered #{mem.add(fact, kind)}"

        @tool
        def recall(query: str, k: int = 5) -> str:
            """Search long-term memory for facts relevant to a query (use before answering personal questions)."""
            hits = mem.search(query, int(k))
            return "\n".join(f"#{i['id']} [{i['kind']}] {i['text']}" for i in hits) or "nothing remembered yet"

        @tool
        def forget(item_id: int) -> str:
            """Delete a remembered item by its #id when the user corrects or withdraws it."""
            return "forgotten" if mem.remove(item_id) else "no such item"

        return [remember, recall, forget]


MEMORY_RULES = """Memory rules:
- At the start, call `recall` with the topic of the request.
- When the user states a lasting fact, preference or goal, call `remember` with one short sentence.
- If the user corrects something, `forget` the old item and `remember` the new one.
- Never store passwords, financial account numbers or other secrets."""
