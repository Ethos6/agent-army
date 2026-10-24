# How Agent Army works

Agent Army is under 900 lines of Python. This page walks through each one.

```
army/
  llm.py     one chat() interface over every provider (stdlib HTTP only)
  agent.py   Tool, @tool, Agent loop, Pipeline, parse_action
  tools.py   sandboxed built-in tools
  rag.py     BM25 retrieval with file:line citations
  cli.py     army list | run | eval | validate | catalog | new
templates/   one folder per agent: agent.toml + agent.py + README.md
```

## 1. Models: `army/llm.py`

Every provider implements one method:

```python
def chat(self, system: str, messages: list[dict]) -> str
```

`get_llm("provider:model")` returns the right adapter. If you pass nothing, it reads `ARMY_MODEL`. If that is not set either, it uses whichever API key it finds, and falls back to a local Ollama server when there are none. OpenAI, Ollama, DeepSeek, Groq, OpenRouter and any vLLM/LM Studio server all go through the same `OpenAICompatible` adapter. Anthropic and Gemini have small dedicated adapters.

There are no SDKs, so there are no version conflicts. The `Mock` provider replays scripted replies, which is how the whole test suite runs offline.

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

**Why JSON instead of native function calling?** Native tool calling differs between vendors and is missing or unreliable on many open models. One plain-text JSON protocol works the same everywhere, so a template you test on Claude behaves the same on Llama. `parse_action` accepts raw JSON, JSON inside code fences, or JSON inside prose, and it ignores JSON objects that are not actions.

**Tools** are typed Python functions:

```python
@tool
def fetch_url(url: str) -> str:
    """Download a web page and return its title and readable text."""
```

The decorator turns the signature and the first docstring line into the spec the model sees: `- fetch_url(url: str): Download a web page...`. Observations are capped at `max_observation_chars` so one large page cannot blow the context window.

**Pipelines** chain agents. Each agent receives the original request plus the previous agent's output, and the `Result.steps` trace covers every agent, so you can see which one introduced a problem.

## 3. Tools and safety: `army/tools.py`

| Tool | Safety measure |
| --- | --- |
| `read_file`, `list_files`, CSV tools | Paths are resolved and must stay inside `ARMY_WORKDIR` (default: the current folder). `../../etc/passwd` raises `PermissionError`. |
| `calculate` | Parses the expression's syntax tree and allows only numbers and arithmetic operators. No `eval`, and huge exponents are refused. |
| `fetch_url` | http(s) only, 30 s timeout, 3 MB read cap. Scripts, styles and navigation are stripped. |
| `git_diff` | Fixed argv (no shell) and rejects refs that look like flags. |

## 4. Retrieval: `army/rag.py`

`BM25Index.from_folder()` splits text files into overlapping 30-line chunks and remembers each chunk's file and line range. `search_tool(index)` exposes it to an agent, and every passage comes back tagged like `[pricing.md:3-12]`, so answers can be traced to the source. Indexing a few thousand files takes seconds and needs no database. If you want embeddings, write a tool with the same signature that calls your vector store.

## 5. Templates and evals

```toml
# templates/docs-qa/agent.toml
name = "docs-qa"
title = "Docs Q&A Agent (RAG)"
category = "rag"
description = "..."
example = "What is the refund window on the Pro plan?"

[[evals]]
input = "Who is the CEO's favourite football team?"
must_contain = ["Not in the knowledge base"]   # refusing correctly is tested too
max_seconds = 120
```

- `army validate` (runs in CI) checks each manifest for required fields, a folder name that matches, at least one eval, a README, and a `build()` that succeeds.
- `army eval [template] --model ...` runs the cases against a real model and exits non-zero on failure, so you can gate a model upgrade on it.
- `army catalog` regenerates the README table from the manifests, so the docs cannot drift from the code.

## Writing a new template

```bash
army new churn-risk
# edit templates/churn-risk/agent.py, agent.toml and README.md
army validate && python -m unittest discover -s tests
army eval churn-risk --model ollama:llama3.2
army catalog
```
