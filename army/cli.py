"""army: list, run, evaluate, validate, serve, schedule and export agent templates."""
from __future__ import annotations

import argparse
import importlib.util
import inspect
import json
import os
import sys
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from . import __version__
from .llm import get_llm

ROOT = Path(__file__).resolve().parent.parent

CATEGORIES = {
    "starter": "Starter agents",
    "research": "Research agents",
    "business": "Business & strategy agents",
    "marketing": "Marketing & content agents",
    "engineering": "Engineering & coding agents",
    "teams": "Multi-agent teams",
    "rag": "RAG (retrieval-augmented generation)",
    "chat": "Chat with your data",
    "memory": "Agents with long-term memory",
    "mcp": "MCP (Model Context Protocol) agents",
    "voice": "Voice agents",
    "games": "Game-playing agents",
    "always-on": "Always-on & scheduled agents",
    "ui": "Generative UI agents",
    "optimize": "Cost & context optimization",
    "finetune": "Fine-tuning & dataset builders",
}
REQUIRED_META = ("category", "description", "example")


def templates_dir() -> Path:
    return Path(os.environ.get("ARMY_TEMPLATES", ROOT / "templates"))


@dataclass
class Template:
    path: Path
    module: object

    @property
    def name(self) -> str:
        return self.path.stem.replace("_", "-")

    @property
    def meta(self) -> dict:
        return getattr(self.module, "META", {})

    @property
    def evals(self) -> list[dict]:
        return getattr(self.module, "EVALS", [])

    @property
    def title(self) -> str:
        return (inspect.getdoc(self.module) or self.name).split("\n")[0].strip()

    @property
    def about(self) -> str:
        doc = inspect.getdoc(self.module) or ""
        return doc.split("\n", 1)[1].strip() if "\n" in doc else ""

    @property
    def options(self) -> dict:
        sig = inspect.signature(self.module.build)
        return {k: p.default for k, p in sig.parameters.items() if k != "llm" and p.default is not inspect.Parameter.empty}

    def build(self, **options):
        return self.module.build(**options)


def _load(path: Path) -> Template:
    spec = importlib.util.spec_from_file_location(f"army_template_{path.stem}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return Template(path, module)


_CACHE: list[Template] | None = None


def load_templates() -> list[Template]:
    global _CACHE
    if _CACHE is None:
        files = sorted(p for p in templates_dir().glob("*/*.py") if not p.name.startswith("_"))
        _CACHE = [_load(p) for p in files]
    return _CACHE


def find(name: str) -> Template:
    for t in load_templates():
        if t.name == name:
            return t
    sys.exit(f"No template named '{name}'. Run `army list`.")


def parse_options(pairs: list[str] | None) -> dict:
    opts = {}
    for pair in pairs or []:
        key, sep, value = pair.partition("=")
        if not sep:
            sys.exit(f"--opt expects key=value, got '{pair}'")
        opts[key.replace("-", "_")] = value
    return opts


def build_from_args(t: Template, args, extra: dict | None = None):
    llm = get_llm(args.model) if getattr(args, "model", None) else None
    return t.build(llm=llm, **{**(extra or {}), **parse_options(getattr(args, "opt", None))})


# ------------------------------------------------------------------ commands
def cmd_list(args):
    by_cat: dict[str, list[Template]] = {}
    for t in load_templates():
        by_cat.setdefault(t.meta.get("category", "?"), []).append(t)
    for cat, title in CATEGORIES.items():
        if args.category and cat != args.category:
            continue
        items = by_cat.get(cat, [])
        if items:
            print(f"\n{title.upper()} ({len(items)})")
            for t in items:
                print(f"  {t.name:<26} {t.meta['description'][:90]}")
    print(f"\n{len(load_templates())} templates. Run one: army run <name> \"<task>\"")


def cmd_info(args):
    t = find(args.template)
    print(f"{t.title}\n{'=' * len(t.title)}\n\n{t.about}\n")
    print(f"category: {t.meta['category']}\nexample:  army run {t.name} \"{t.meta['example']}\"")
    if t.options:
        print("options:  " + ", ".join(f"--opt {k}={v}" for k, v in t.options.items()))
    if t.meta.get("requires"):
        print("requires: pip install " + " ".join(t.meta["requires"]))


def cmd_run(args):
    t = find(args.template)
    agent = build_from_args(t, args)
    started = time.time()
    result = agent.run(args.task, verbose=args.verbose)
    print(result.output)
    if args.verbose:
        calls = sum(1 for s in result.steps if s.kind == "tool")
        print(f"\n-- {len(result.steps)} steps, {calls} tool calls, {time.time() - started:.1f}s", file=sys.stderr)


def cmd_eval(args):
    failures = total = 0
    targets = [find(args.template)] if args.template else [
        t for t in load_templates() if not args.category or t.meta["category"] == args.category
    ]
    for t in targets:
        for case in t.evals:
            total += 1
            started = time.time()
            try:
                agent = build_from_args(t, args, case.get("options"))
                out = agent.run(case["input"]).output
                missing = [w for w in case.get("must_contain", []) if w.lower() not in out.lower()]
                slow = not args.ignore_time and time.time() - started > case.get("max_seconds", 600)
                ok, reason = not missing and not slow, (f"missing {missing}" if missing else "too slow" if slow else "")
            except Exception as e:
                ok, reason = False, f"{type(e).__name__}: {e}"
            failures += not ok
            line = f"{'PASS' if ok else 'FAIL'}  {t.name:<26} {time.time() - started:5.1f}s  {reason}"
            print(line, flush=True)
            if args.report:
                with open(args.report, "a") as f:
                    f.write(f"| {'PASS' if ok else 'FAIL'} | {t.name} | {time.time() - started:.0f}s | {reason or '-'} |\n")
    print(f"\n{total - failures}/{total} eval cases passed")
    sys.exit(1 if failures else 0)


def validate_all() -> list[str]:
    problems, names = [], set()
    for t in load_templates():
        where = f"{t.path.parent.name}/{t.path.name}"
        missing = [k for k in REQUIRED_META if k not in t.meta]
        if missing:
            problems.append(f"{where}: META missing {missing}")
        cat = t.meta.get("category")
        if cat not in CATEGORIES:
            problems.append(f"{where}: unknown category {cat!r}")
        elif t.path.parent.name != cat:
            problems.append(f"{where}: file must live in templates/{cat}/")
        if t.name in names:
            problems.append(f"{where}: duplicate name")
        names.add(t.name)
        if not inspect.getdoc(t.module) or not t.about:
            problems.append(f"{where}: needs a module docstring (title line + description)")
        if not t.evals:
            problems.append(f"{where}: add at least one EVALS case")
        try:
            agent = t.build()
            if not hasattr(agent, "run"):
                problems.append(f"{where}: build() must return something with .run()")
        except Exception as e:
            problems.append(f"{where}: build() failed: {type(e).__name__}: {e}")
    return problems


def cmd_validate(_):
    problems = validate_all()
    for p in problems:
        print("x", p)
    print(f"{len(load_templates())} templates checked, {len(problems)} problems")
    sys.exit(1 if problems else 0)


START, END = "<!-- catalog:start -->", "<!-- catalog:end -->"


def render_catalog() -> str:
    by_cat: dict[str, list[Template]] = {}
    for t in load_templates():
        by_cat.setdefault(t.meta["category"], []).append(t)
    parts = [f"**{len(load_templates())} templates in {len(by_cat)} categories.** Full docs: [docs/TEMPLATES.md](docs/TEMPLATES.md)\n"]
    for cat, title in CATEGORIES.items():
        items = by_cat.get(cat)
        if not items:
            continue
        parts.append(f"\n### {title} ({len(items)})\n\n| Template | What it does |\n|---|---|")
        for t in items:
            parts.append(f"| [**{t.title}**](templates/{cat}/{t.path.name}) `{t.name}` | {t.meta['description']} |")
    return "\n".join(parts)


def render_docs() -> str:
    out = ["# Template reference", "", "Generated by `army docs` from each template's docstring and metadata.", ""]
    for cat, title in CATEGORIES.items():
        items = [t for t in load_templates() if t.meta["category"] == cat]
        if not items:
            continue
        out += [f"## {title}", ""]
        for t in items:
            agent = t.build()
            tools = sorted(getattr(agent, "tools", {}) or {})
            out += [f"### {t.title}", "", t.about, "", "```bash", f'army run {t.name} "{t.meta["example"]}"', "```", ""]
            if t.options:
                out.append("**Options:** " + ", ".join(f"`{k}` (default `{v}`)" for k, v in t.options.items()) + "  ")
            if tools:
                out.append("**Tools:** " + ", ".join(f"`{x}`" for x in tools) + "  ")
            if t.meta.get("requires"):
                out.append("**Requires:** `pip install " + " ".join(t.meta["requires"]) + "`  ")
            if t.meta.get("needs"):
                out.append(f"**Needs:** {t.meta['needs']}  ")
            out += [f"[source](../templates/{cat}/{t.path.name})", ""]
    return "\n".join(out)


def _sync(path: Path, new: str, check: bool, label: str):
    old = path.read_text() if path.exists() else ""
    if check:
        if old != new:
            sys.exit(f"{label} is stale. Run `army catalog && army docs` and commit.")
        print(f"{label} up to date")
    else:
        path.write_text(new)
        print(f"{label} updated")


def cmd_catalog(args):
    readme = ROOT / "README.md"
    text = readme.read_text()
    head, _, rest = text.partition(START)
    _, _, tail = rest.partition(END)
    _sync(readme, f"{head}{START}\n{render_catalog()}\n{END}{tail}", args.check, "README catalog")


def cmd_docs(args):
    _sync(ROOT / "docs" / "TEMPLATES.md", render_docs() + "\n", args.check, "docs/TEMPLATES.md")


SCAFFOLD = '''"""{title}

Explain in two or three sentences what this agent delivers, how it works, and why it can be trusted.
"""
from army import Agent
from army.tools import calculate
from army.web import web_search

META = {{
    "category": "{category}",
    "description": "One line: what this agent delivers.",
    "example": "Describe a task for it",
}}
EVALS = [{{"input": "Describe a task for it", "must_contain": []}}]


def build(llm=None):
    return Agent(
        name="{name}",
        instructions="""You are ... Produce ...""",
        tools=[web_search, calculate],
        llm=llm,
    )
'''


def cmd_new(args):
    if args.category not in CATEGORIES:
        sys.exit(f"category must be one of: {', '.join(CATEGORIES)}")
    path = templates_dir() / args.category / (args.name.replace("-", "_") + ".py")
    if path.exists():
        sys.exit(f"{path} already exists")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(SCAFFOLD.format(title=args.name.replace("-", " ").title(), category=args.category, name=args.name))
    print(f"Created {path}. Edit it, then run `army validate`.")


def cmd_export_skill(args):
    targets = load_templates() if args.template == "all" else [find(args.template)]
    out_root = Path(args.out)
    for t in targets:
        agent = t.build()
        instructions = getattr(agent, "instructions", None) or "\n\n".join(
            f"## Step: {a.name}\n{a.instructions}" for a in getattr(agent, "agents", getattr(agent, "members", []))
        )
        folder = out_root / t.name
        folder.mkdir(parents=True, exist_ok=True)
        desc = t.meta["description"].replace("\n", " ")
        (folder / "SKILL.md").write_text(
            f"---\nname: {t.name}\ndescription: {desc}\n---\n\n# {t.title}\n\n{t.about}\n\n"
            f"## How to do this task\n\n{instructions}\n\n"
            f"## Run it as a standalone agent\n\n```bash\npip install agent-army\narmy run {t.name} \"<task>\"\n```\n"
        )
    print(f"exported {len(targets)} skill(s) to {out_root}/")


def cmd_schedule(args):
    t = find(args.template)
    runs = 0
    while True:
        started = time.strftime("%Y-%m-%d %H:%M")
        try:
            output = build_from_args(t, args).run(args.task).output
        except Exception as e:
            output = f"run failed: {type(e).__name__}: {e}"
        report = f"# {t.title} - {started}\n\n{output}\n"
        if args.out:
            with open(args.out, "a") as f:
                f.write(report + "\n")
        if args.webhook:  # Slack/Discord/Teams-style incoming webhooks accept {"text": ...}
            req = urllib.request.Request(args.webhook, data=json.dumps({"text": report[:39000], "content": report[:1900]}).encode(),
                                         headers={"content-type": "application/json"})
            urllib.request.urlopen(req, timeout=30).read()
        if not args.out and not args.webhook:
            print(report)
        runs += 1
        if args.times and runs >= args.times:
            break
        time.sleep(args.every * 60)


def cmd_serve(args):
    from .playground import serve

    serve(args.host, args.port)


def main(argv=None):
    p = argparse.ArgumentParser(prog="army", description="Agent Army: production-grade AI agents for any model")
    p.add_argument("--version", action="version", version=f"army {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("list", help="list templates")
    s.add_argument("--category", choices=list(CATEGORIES))
    s.set_defaults(fn=cmd_list)

    s = sub.add_parser("info", help="show a template's description and options")
    s.add_argument("template")
    s.set_defaults(fn=cmd_info)

    def run_args(s):
        s.add_argument("--model", help='e.g. "anthropic:claude-sonnet-4-5" (default: $ARMY_MODEL)')
        s.add_argument("--opt", action="append", help="template option key=value (repeatable)")

    s = sub.add_parser("run", help="run a template")
    s.add_argument("template")
    s.add_argument("task")
    run_args(s)
    s.add_argument("-v", "--verbose", action="store_true")
    s.set_defaults(fn=cmd_run)

    s = sub.add_parser("eval", help="run eval cases against a real model")
    s.add_argument("template", nargs="?")
    s.add_argument("--category", choices=list(CATEGORIES))
    s.add_argument("--ignore-time", action="store_true", help="don't fail cases for exceeding max_seconds (slow local models)")
    s.add_argument("--report", help="append a Markdown table row per case to this file")
    run_args(s)
    s.set_defaults(fn=cmd_eval)

    sub.add_parser("validate", help="check every template").set_defaults(fn=cmd_validate)

    for name, fn, helptext in (("catalog", cmd_catalog, "regenerate the README catalog"), ("docs", cmd_docs, "regenerate docs/TEMPLATES.md")):
        s = sub.add_parser(name, help=helptext)
        s.add_argument("--check", action="store_true")
        s.set_defaults(fn=fn)

    s = sub.add_parser("new", help="scaffold a new template")
    s.add_argument("category")
    s.add_argument("name")
    s.set_defaults(fn=cmd_new)

    s = sub.add_parser("export-skill", help="export template(s) as SKILL.md for coding agents")
    s.add_argument("template", help='template name or "all"')
    s.add_argument("--out", default="skills")
    s.set_defaults(fn=cmd_export_skill)

    s = sub.add_parser("schedule", help="run a template every N minutes and deliver the result")
    s.add_argument("template")
    s.add_argument("task")
    s.add_argument("--every", type=float, default=1440, help="minutes between runs (default: daily)")
    s.add_argument("--times", type=int, default=0, help="stop after N runs (0 = forever)")
    s.add_argument("--webhook", help="incoming-webhook URL to post each report to")
    s.add_argument("--out", help="append each report to this file")
    run_args(s)
    s.set_defaults(fn=cmd_schedule)

    s = sub.add_parser("serve", help="open the web playground for all templates")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8765)
    s.set_defaults(fn=cmd_serve)

    args = p.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
