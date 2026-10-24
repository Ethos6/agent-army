# How Agent Army works

Agent Army is a small Python package (`army/`, standard library only) plus 109 agents in `templates/`, one file each.

```
army/
  llm.py        one chat() interface over every provider
  agent.py      Tool, @tool, Agent loop, Pipeline, Panel, agent_tool, parse_action
  tools.py      local tools: sandboxed files, CSV, SQLite, PDF, mailbox, transcripts, git, calculator
  web.py        network tools: search, fetch, crawl, RSS, arXiv, Hacker News, GitHub, weather, FX, stocks, PyPI
  rag.py        BM25 index, embeddings, vector and hybrid search, citations
  memory.py     long-term memory store exposed as tools
  mcp.py        Model Context Protocol client (stdio)
  voice.py      speech-to-text and text-to-speech
  playground.py `army serve` web UI
  cli.py        army list | info | run | eval | validate | catalog | docs | new | export-skill | schedule | serve
templates/<category>/<agent>.py
```

## 1. Models: `army/llm.py`

Every provider implements one method:

```python
def chat(self, system: str, messages: list[dict]) -> str
```

`get_llm("provider:model")` returns the right adapter. With no argument it reads `ARMY_MODEL`; if that isn't set, it uses whichever API key it finds, and falls back to a local Ollama server when there are none. OpenAI, Ollama, DeepSeek, Groq, OpenRouter and any vLLM or LM Studio server share one `OpenAICompatible` adapter; Anthropic and Gemini have small dedicated adapters. There are no SDKs, so there are no version conflicts. The `Mock` provider replays scripted replies, which is how the whole test suite runs offline.

## 2. The loop: `army/agent.py`

```
messages = [task]
repeat up to max_steps:
    reply  = llm.chat(system_prompt, messages)
    action = parse_action(reply)
    if no action or "final" in action: return the answer
    observation = run the tool (errors become text, never exceptions)
    messages += [reply, "Observation from <tool>: ..."]
if steps run out: ask the model for its final answer
```

**Why JSON instead of native function calling?** Native tool calling differs between vendors and is missing or unreliable on many open models. One plain-text JSON protocol behaves the same everywhere, so an agent you test on Claude behaves the same on Llama. `parse_action` accepts raw JSON, JSON in code fences, or JSON inside prose, and ignores JSON objects that aren't actions.

**Tools** are typed Python functions. `@tool` turns the signature and the first docstring line into the spec the model sees. Observations are capped so one huge page can't blow the context window.

## 3. Teams

| Pattern | Class | Example agents |
| --- | --- | --- |
| Sequential hand-off: each agent sees the request plus the previous output | `Pipeline(a, b, c)` | content-team, legal-team, deep-research |
| Independent answers, then a judge | `Panel([a, b, c], judge)` | mixture-of-models, reader-panel, design-review-panel |
| Manager delegates to workers as tools | `worker.as_tool("...")` / `agent_tool(...)` | finance-team, travel-team |
| Custom control flow | any object with `.run(task)` | tic-tac-toe-arena, twenty-questions |

Every agent in a team can use a different model, for example `debate-panel --opt models=anthropic:...,openai:...,gemini:...`.

## 4. Tools and safety

| Tool group | Safety measure |
| --- | --- |
| Files, CSV, PDF, mailbox, transcripts | Paths must resolve inside `ARMY_WORKDIR` (default: the current folder). `write_file` only writes to `outputs/`. |
| SQLite | Opened in read-only mode, and only `SELECT` / `WITH` queries are accepted. |
| `calculate` | Parses the expression's syntax tree and allows only numbers and arithmetic operators, with no `eval`. Huge exponents are refused. |
| git tools | Fixed argument lists (no shell); refs that look like flags are rejected. |
| Web tools | http(s) only, timeouts, read-size caps; scripts and navigation are stripped from pages. |
| MCP | Servers run as subprocesses you name explicitly; agents are instructed to describe write actions before taking them. |
| Memory | Plain JSON at `~/.army/memory/`, which you can read and edit; agents are told never to store secrets. |

## 5. Retrieval: `army/rag.py`

`index_folder()` splits text files into overlapping 12-line chunks that remember their file and line range. `search_tool(index)` exposes any index to an agent, and every passage comes back tagged like `[pricing.md:3-12]`.

- **BM25Index**: keyword search; instant, with no API needed.
- **VectorIndex**: embeddings from `ARMY_EMBED_MODEL` (OpenAI, Gemini or Ollama), computed lazily, kept in memory.
- **HybridIndex**: reciprocal-rank fusion of both.

## 6. Memory, MCP and voice

- `Memory("travel").tools()` gives an agent `remember`, `recall` and `forget`. Several agents, even on different models, can share one store.
- `MCPServer("npx -y <server>").tools()` gives an agent `<name>_list_tools` and `<name>_call`, so it can use any MCP server without knowing its tools in advance. The server starts only on first use.
- `army.voice` adds `transcribe_audio` and `text_to_speech` over any OpenAI-compatible audio endpoint.

## 7. Agent files and evals

```python
"""Docs Q&A                                   <- title (first line)

What it does and why it can be trusted.      <- description (rendered into docs/TEMPLATES.md)
"""
META = {"category": "rag", "description": "...", "example": "..."}
EVALS = [{"input": "...", "must_contain": ["30", "pricing.md"], "max_seconds": 120}]

def build(llm=None, docs: str = "examples/knowledge-base"):   # keyword args become --opt options
    return Agent(...)
```

- `army validate` (run in CI) checks metadata, docstring, eval cases, folder/category match and a working `build()` for every agent.
- `army eval [agent] [--category c] --model ...` runs the cases against a real model and exits non-zero on failure.
- `army catalog` and `army docs` regenerate the README table and `docs/TEMPLATES.md` from the code, and CI fails if they drift.

## 8. Running agents everywhere

- **CLI:** `army run <agent> "<task>" --model ... --opt key=value -v`
- **Playground:** `army serve` opens a local web UI listing every agent, with a step trace for each run.
- **Schedules:** `army schedule <agent> "<task>" --every 60 --webhook https://hooks...` posts each report to Slack, Discord or Teams incoming webhooks (or `--out report.md`).
- **Coding agents:** `army export-skill <agent|all>` writes SKILL.md files that coding agents can load as skills.
