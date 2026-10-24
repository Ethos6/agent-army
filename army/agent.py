"""The agent loop: a model, a few tools, and a JSON action protocol any model can follow."""
from __future__ import annotations

import inspect
import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from .llm import LLM, get_llm

PROTOCOL = """\
You can use these tools:
{tools}

Work step by step. Each reply must be exactly ONE JSON object and nothing else:
  {{"thought": "<short reasoning>", "tool": "<tool name>", "args": {{...}}}}   to call a tool
  {{"thought": "<short reasoning>", "final": "<your complete answer>"}}         when you are done
After a tool call you will receive its result as an Observation. Never invent observations."""

PROTOCOL_REMINDER = (
    'Reply with exactly ONE JSON object: {"tool": "<name>", "args": {...}} to use a tool, '
    'or {"final": "<your complete answer>"} if you are done.'
)


@dataclass
class Tool:
    name: str
    description: str
    fn: Callable[..., Any]
    params: dict[str, str]

    def __call__(self, **kwargs) -> Any:
        return self.fn(**kwargs)

    def spec(self) -> str:
        args = ", ".join(f"{k}: {v}" for k, v in self.params.items())
        return f"- {self.name}({args}): {self.description}"


def tool(fn: Callable | None = None, *, name: str | None = None):
    """Turn a typed, documented function into a Tool. The first docstring line is its description."""

    def wrap(f: Callable) -> Tool:
        params = {}
        for k, p in inspect.signature(f).parameters.items():
            ann = p.annotation
            label = getattr(ann, "__name__", None) if ann is not inspect.Parameter.empty else None
            params[k] = (label or str(ann) if ann is not inspect.Parameter.empty else "str") + (
                "" if p.default is inspect.Parameter.empty else f" = {p.default!r}"
            )
        doc = (inspect.getdoc(f) or "").strip().split("\n")[0]
        return Tool(name or f.__name__, doc, f, params)

    return wrap(fn) if fn else wrap


@dataclass
class Step:
    agent: str
    kind: str  # "tool" | "final"
    content: str
    tool: str | None = None
    args: dict | None = None
    seconds: float = 0.0


@dataclass
class Result:
    output: str
    steps: list[Step] = field(default_factory=list)

    def __str__(self) -> str:
        return self.output


_FENCE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def parse_action(text: str) -> dict | None:
    """Find the first JSON object containing "tool" or "final". Tolerates prose and code fences."""
    candidates = [m.group(1) for m in _FENCE.finditer(text)]
    decoder = json.JSONDecoder()
    for blob in candidates:
        try:
            obj = json.loads(blob)
            if isinstance(obj, dict) and ("tool" in obj or "final" in obj):
                return obj
        except json.JSONDecodeError:
            pass
    for i, ch in enumerate(text):
        if ch != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(text[i:])
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and ("tool" in obj or "final" in obj):
            return obj
    return None


def _as_text(value: Any) -> str:
    return value if isinstance(value, str) else json.dumps(value, indent=2, ensure_ascii=False)


class Agent:
    def __init__(
        self,
        name: str,
        instructions: str,
        tools: list[Tool] | tuple = (),
        llm: LLM | None = None,
        max_steps: int = 10,
        max_observation_chars: int = 12_000,
    ):
        self.name = name
        self.instructions = instructions.strip()
        self.tools = {t.name: t for t in tools}
        self._llm = llm
        self.max_steps = max_steps
        self.max_observation_chars = max_observation_chars

    @property
    def llm(self) -> LLM:
        if self._llm is None:
            self._llm = get_llm()
        return self._llm

    @property
    def system_prompt(self) -> str:
        if not self.tools:
            return self.instructions
        specs = "\n".join(t.spec() for t in self.tools.values())
        return f"{self.instructions}\n\n{PROTOCOL.format(tools=specs)}"

    def _call_tool(self, name: str, args: Any) -> str:
        t = self.tools.get(name)
        if t is None:
            return f"Error: unknown tool '{name}'. Available tools: {', '.join(self.tools)}"
        if not isinstance(args, dict):
            return "Error: 'args' must be a JSON object."
        try:
            return _as_text(t(**args))[: self.max_observation_chars]
        except Exception as e:  # tool errors are shown to the model so it can recover
            return f"Error: {type(e).__name__}: {e}"

    def _chat(self, messages: list[dict]) -> str:
        # Ask for strict JSON when the model supports it (agents with tools speak JSON). Custom LLM classes
        # written as chat(system, messages) without **kwargs still work: we only pass the flag if accepted.
        params = inspect.signature(self.llm.chat).parameters
        if "json_mode" in params or any(p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values()):
            return self.llm.chat(self.system_prompt, messages, json_mode=bool(self.tools))
        return self.llm.chat(self.system_prompt, messages)

    def run(self, task: str, verbose: bool = False) -> Result:
        messages = [{"role": "user", "content": task}]
        steps: list[Step] = []
        nudged = False
        for _ in range(self.max_steps):
            started = time.time()
            reply = self._chat(messages)
            messages.append({"role": "assistant", "content": reply})
            action = parse_action(reply)
            if not self.tools and action and not (reply.strip().startswith(("{", "```")) and "tool" not in action):
                action = None  # tool-less agents may legitimately mention JSON; only unwrap a bare {"final": ...}
            if self.tools and action is None and not nudged:
                nudged = True  # small models sometimes drift into prose: remind them of the protocol once
                messages.append({"role": "user", "content": PROTOCOL_REMINDER})
                continue
            if action is not None and action.get("tool") and not action.get("final"):
                name, args = str(action["tool"]), action.get("args", {})
                observation = self._call_tool(name, args)
                steps.append(Step(self.name, "tool", observation, name, args, time.time() - started))
                if verbose:
                    print(f"  [{self.name}] {name}({json.dumps(args)[:120]}) -> {observation[:160]!r}")
                messages.append({"role": "user", "content": f"Observation from {name}:\n{observation}"})
                continue
            output = _as_text(action["final"]) if action and "final" in action else reply.strip()
            steps.append(Step(self.name, "final", output, seconds=time.time() - started))
            return Result(output, steps)
        messages.append({"role": "user", "content": 'Step limit reached. Reply now with {"final": "<answer>"}.'})
        reply = self._chat(messages)
        action = parse_action(reply)
        output = _as_text(action["final"]) if action and "final" in action else reply.strip()
        steps.append(Step(self.name, "final", output))
        return Result(output, steps)


class Pipeline:
    """Run agents in sequence; each one sees the original request plus the previous agent's output."""

    def __init__(self, *agents: Agent, name: str = "pipeline"):
        if not agents:
            raise ValueError("Pipeline needs at least one agent")
        self.agents = agents
        self.name = name

    @property
    def tools(self) -> dict[str, Tool]:
        return {k: v for a in self.agents for k, v in a.tools.items()}

    def run(self, task: str, verbose: bool = False) -> Result:
        steps: list[Step] = []
        output, previous = task, None
        for agent in self.agents:
            prompt = task if previous is None else (
                f"Original request:\n{task}\n\nOutput from {previous}:\n{output}"
            )
            if verbose:
                print(f"-> {agent.name}")
            result = agent.run(prompt, verbose=verbose)
            steps += result.steps
            output, previous = result.output, agent.name
        return Result(output, steps)


def agent_tool(agent: "Agent | Pipeline", description: str, name: str | None = None) -> Tool:
    """Wrap an agent (or pipeline) as a tool so a manager agent can delegate work to it."""

    def delegate(task: str) -> str:
        return agent.run(task).output

    return Tool(name or f"ask_{agent.name.replace('-', '_')}", description, delegate, {"task": "str"})


Agent.as_tool = lambda self, description, name=None: agent_tool(self, description, name)  # type: ignore[attr-defined]
Pipeline.as_tool = lambda self, description, name=None: agent_tool(self, description, name)  # type: ignore[attr-defined]


class Panel:
    """Ask several agents the same task independently, then have a judge agent synthesize one answer."""

    def __init__(self, members: list[Agent], judge: Agent, name: str = "panel"):
        self.members, self.judge, self.name = members, judge, name

    @property
    def tools(self) -> dict[str, Tool]:
        return {k: v for a in [*self.members, self.judge] for k, v in a.tools.items()}

    def run(self, task: str, verbose: bool = False) -> Result:
        steps: list[Step] = []
        answers = []
        for i, member in enumerate(self.members, 1):
            if verbose:
                print(f"-> {member.name}")
            r = member.run(task, verbose=verbose)
            steps += r.steps
            answers.append(f"### Answer {i} ({member.name})\n{r.output}")
        if verbose:
            print(f"-> {self.judge.name}")
        final = self.judge.run(f"Task:\n{task}\n\nIndependent answers:\n\n" + "\n\n".join(answers), verbose=verbose)
        return Result(final.output, steps + final.steps)
