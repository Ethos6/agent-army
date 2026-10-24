"""army: list, run, evaluate, validate and scaffold agent templates."""
from __future__ import annotations

import argparse
import importlib.util
import os
import sys
import time
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from . import __version__
from .llm import get_llm

ROOT = Path(__file__).resolve().parent.parent
REQUIRED = ("name", "title", "category", "description", "example")
CATEGORIES = ("research", "data", "rag", "engineering", "marketing", "business")


def templates_dir() -> Path:
    return Path(os.environ.get("ARMY_TEMPLATES", ROOT / "templates"))


@dataclass
class Template:
    path: Path
    meta: dict
    evals: list[dict] = field(default_factory=list)

    @property
    def name(self) -> str:
        return self.meta["name"]

    def build(self, **options):
        spec = importlib.util.spec_from_file_location(f"army_template_{self.name.replace('-', '_')}", self.path / "agent.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.build(**options)


def load_templates() -> list[Template]:
    out = []
    for manifest in sorted(templates_dir().glob("*/agent.toml")):
        data = tomllib.loads(manifest.read_text())
        out.append(Template(manifest.parent, data, data.pop("evals", [])))
    return out


def find(name: str) -> Template:
    for t in load_templates():
        if t.name == name:
            return t
    sys.exit(f"No template named '{name}'. Run `army list`.")


def parse_options(pairs: list[str]) -> dict:
    opts = {}
    for pair in pairs or []:
        key, sep, value = pair.partition("=")
        if not sep:
            sys.exit(f"--opt expects key=value, got '{pair}'")
        opts[key.replace("-", "_")] = value
    return opts


def cmd_list(_):
    for cat in CATEGORIES:
        items = [t for t in load_templates() if t.meta["category"] == cat]
        if items:
            print(f"\n{cat.upper()}")
            for t in items:
                print(f"  {t.name:<20} {t.meta['description']}")


def cmd_run(args):
    t = find(args.template)
    agent = t.build(llm=get_llm(args.model) if args.model else None, **parse_options(args.opt))
    started = time.time()
    result = agent.run(args.task, verbose=args.verbose)
    print(result.output)
    if args.verbose:
        tools_used = sum(1 for s in result.steps if s.kind == "tool")
        print(f"\n-- {len(result.steps)} steps, {tools_used} tool calls, {time.time() - started:.1f}s", file=sys.stderr)


def cmd_eval(args):
    failures = 0
    targets = [find(args.template)] if args.template else load_templates()
    for t in targets:
        for case in t.evals:
            agent = t.build(llm=get_llm(args.model) if args.model else None, **case.get("options", {}))
            started = time.time()
            try:
                out = agent.run(case["input"]).output
                missing = [w for w in case.get("must_contain", []) if w.lower() not in out.lower()]
                too_slow = time.time() - started > case.get("max_seconds", 600)
                ok = not missing and not too_slow
                reason = f"missing {missing}" if missing else ("too slow" if too_slow else "")
            except Exception as e:
                ok, reason = False, f"{type(e).__name__}: {e}"
            failures += not ok
            print(f"{'PASS' if ok else 'FAIL'}  {t.name:<20} {case['input'][:60]!r} {reason}")
    sys.exit(1 if failures else 0)


def cmd_validate(_):
    problems = []
    names = set()
    for t in load_templates():
        missing = [k for k in REQUIRED if k not in t.meta]
        if missing:
            problems.append(f"{t.path.name}: missing {missing}")
        if t.meta.get("category") not in CATEGORIES:
            problems.append(f"{t.path.name}: category must be one of {CATEGORIES}")
        if t.meta.get("name") != t.path.name:
            problems.append(f"{t.path.name}: name must match folder")
        if t.meta.get("name") in names:
            problems.append(f"{t.path.name}: duplicate name")
        names.add(t.meta.get("name"))
        if not t.evals:
            problems.append(f"{t.path.name}: add at least one [[evals]] case")
        if not (t.path / "README.md").exists():
            problems.append(f"{t.path.name}: missing README.md")
        try:
            agent = t.build(**t.meta.get("validate_options", {}))
            if not hasattr(agent, "run"):
                problems.append(f"{t.path.name}: build() must return an Agent or Pipeline")
        except Exception as e:
            problems.append(f"{t.path.name}: build() failed: {type(e).__name__}: {e}")
    for p in problems:
        print("x", p)
    print(f"{len(names)} templates checked, {len(problems)} problems")
    sys.exit(1 if problems else 0)


START, END = "<!-- catalog:start -->", "<!-- catalog:end -->"


def render_catalog() -> str:
    rows = ["| Template | What it does | Category | Try it |", "|---|---|---|---|"]
    for t in sorted(load_templates(), key=lambda t: (CATEGORIES.index(t.meta["category"]), t.name)):
        rows.append(
            f"| [**{t.meta['title']}**](templates/{t.name}) | {t.meta['description']} "
            f"| `{t.meta['category']}` | `army run {t.name} \"{t.meta['example']}\"` |"
        )
    return "\n".join(rows)


def cmd_catalog(args):
    readme = ROOT / "README.md"
    text = readme.read_text()
    head, _, rest = text.partition(START)
    _, _, tail = rest.partition(END)
    new = f"{head}{START}\n{render_catalog()}\n{END}{tail}"
    if args.check:
        if new != text:
            sys.exit("README catalog is stale. Run `army catalog` and commit.")
        print("catalog up to date")
    else:
        readme.write_text(new)
        print("README catalog updated")


SCAFFOLD_TOML = '''name = "{name}"
title = "{title}"
category = "business"
description = "One line: what this agent delivers."
example = "Describe a task for it"

[[evals]]
input = "Describe a task for it"
must_contain = []
'''

SCAFFOLD_PY = '''from army import Agent
from army.tools import calculate, fetch_url


def build(llm=None):
    return Agent(
        name="{name}",
        instructions="""You are ... Produce ...""",
        tools=[fetch_url, calculate],
        llm=llm,
    )
'''


def cmd_new(args):
    folder = templates_dir() / args.name
    if folder.exists():
        sys.exit(f"{folder} already exists")
    folder.mkdir(parents=True)
    title = args.name.replace("-", " ").title()
    (folder / "agent.toml").write_text(SCAFFOLD_TOML.format(name=args.name, title=title))
    (folder / "agent.py").write_text(SCAFFOLD_PY.format(name=args.name))
    (folder / "README.md").write_text(f"# {title}\n\nWhat it does, how it works, example output.\n")
    print(f"Created {folder}. Edit it, then run `army validate`.")


def main(argv=None):
    p = argparse.ArgumentParser(prog="army", description="Agent Army")
    p.add_argument("--version", action="version", version=f"army {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="list templates").set_defaults(fn=cmd_list)
    r = sub.add_parser("run", help="run a template")
    r.add_argument("template")
    r.add_argument("task")
    r.add_argument("--model", help='e.g. "anthropic:claude-sonnet-4-5" (default: $ARMY_MODEL)')
    r.add_argument("--opt", action="append", help="template option key=value (repeatable)")
    r.add_argument("-v", "--verbose", action="store_true")
    r.set_defaults(fn=cmd_run)
    e = sub.add_parser("eval", help="run eval cases against a real model")
    e.add_argument("template", nargs="?")
    e.add_argument("--model")
    e.set_defaults(fn=cmd_eval)
    sub.add_parser("validate", help="check every template's manifest and build()").set_defaults(fn=cmd_validate)
    c = sub.add_parser("catalog", help="regenerate the README catalog table")
    c.add_argument("--check", action="store_true")
    c.set_defaults(fn=cmd_catalog)
    n = sub.add_parser("new", help="scaffold a new template")
    n.add_argument("name")
    n.set_defaults(fn=cmd_new)
    args = p.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
