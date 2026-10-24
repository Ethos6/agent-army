"""Offline test suite: no API keys or network needed. Run with `python -m unittest -v`."""
import json
import os
import tempfile
import unittest
from pathlib import Path

from army import Agent, Mock, Pipeline, get_llm, parse_action, tool
from army.cli import load_templates, render_catalog
from army.rag import BM25Index, search_tool
from army.tools import calculate, safe_path

ROOT = Path(__file__).resolve().parent.parent


class ParseAction(unittest.TestCase):
    def test_plain_json(self):
        self.assertEqual(parse_action('{"final": "hi"}'), {"final": "hi"})

    def test_prose_and_fences(self):
        text = 'Sure! ```json\n{"tool": "calculate", "args": {"expression": "1+1"}}\n```'
        self.assertEqual(parse_action(text)["tool"], "calculate")

    def test_ignores_unrelated_json(self):
        self.assertIsNone(parse_action('the config is {"a": 1}'))

    def test_nested_braces(self):
        self.assertEqual(parse_action('x {"final": {"a": {"b": 1}}} y')["final"], {"a": {"b": 1}})


class AgentLoop(unittest.TestCase):
    def test_tool_then_final(self):
        llm = Mock(['{"tool": "calculate", "args": {"expression": "6*7"}}', '{"final": "It is 42"}'])
        result = Agent("t", "be precise", [calculate], llm=llm).run("6 times 7?")
        self.assertEqual(result.output, "It is 42")
        self.assertEqual([s.kind for s in result.steps], ["tool", "final"])
        self.assertIn("42", llm.calls[1][1][-1]["content"])  # observation fed back

    def test_tool_errors_are_reported_not_raised(self):
        llm = Mock(['{"tool": "nope", "args": {}}', '{"tool": "calculate", "args": {"expression": "1/0"}}', '{"final": "ok"}'])
        result = Agent("t", "x", [calculate], llm=llm).run("go")
        self.assertIn("unknown tool", result.steps[0].content)
        self.assertIn("ZeroDivisionError", result.steps[1].content)
        self.assertEqual(result.output, "ok")

    def test_step_limit_forces_final(self):
        llm = Mock(['{"tool": "calculate", "args": {"expression": "1"}}'] * 2 + ['{"final": "done"}'])
        self.assertEqual(Agent("t", "x", [calculate], llm=llm, max_steps=2).run("go").output, "done")

    def test_no_tools_returns_text(self):
        self.assertEqual(Agent("t", "x", llm=Mock(["plain answer"])).run("q").output, "plain answer")

    def test_tool_decorator_signature(self):
        @tool
        def greet(name: str, times: int = 1) -> str:
            """Say hello."""
            return "hi " * times + name

        self.assertEqual(greet.description, "Say hello.")
        self.assertIn("times: int = 1", greet.spec())


class PipelineTest(unittest.TestCase):
    def test_passes_output_forward(self):
        a_llm, b_llm = Mock(["draft v1"]), Mock(["final v2"])
        result = Pipeline(Agent("a", "x", llm=a_llm), Agent("b", "y", llm=b_llm)).run("brief")
        self.assertEqual(result.output, "final v2")
        self.assertIn("draft v1", b_llm.calls[0][1][0]["content"])
        self.assertIn("brief", b_llm.calls[0][1][0]["content"])


class Safety(unittest.TestCase):
    def test_calculator_rejects_code(self):
        for bad in ["__import__('os')", "open('x')", "2**10000"]:
            with self.assertRaises(Exception):
                calculate(expression=bad)
        self.assertEqual(calculate(expression="(1200-950)/950*100")[:5], "26.31")

    def test_sandbox_blocks_escape(self):
        with tempfile.TemporaryDirectory() as d:
            os.environ["ARMY_WORKDIR"] = d
            try:
                with self.assertRaises(PermissionError):
                    safe_path("../../etc/passwd")
                self.assertEqual(safe_path("a.txt"), Path(d).resolve() / "a.txt")
            finally:
                del os.environ["ARMY_WORKDIR"]


class Retrieval(unittest.TestCase):
    def test_bm25_finds_and_cites(self):
        index = BM25Index.from_folder(ROOT / "examples/knowledge-base")
        top = index.search("refund window pro plan")[0][1]
        self.assertEqual(top.source, "pricing.md")
        self.assertIn("pricing.md:", search_tool(index)(query="rotate api key") + top.cite)


class Providers(unittest.TestCase):
    def test_spec_parsing(self):
        self.assertEqual(repr(get_llm("openai:gpt-4o-mini")), "openai:gpt-4o-mini")
        self.assertEqual(get_llm("ollama").model, "llama3.2")
        self.assertEqual(get_llm("mock").provider, "mock")
        with self.assertRaises(Exception):
            get_llm("nonsense:x")


class Templates(unittest.TestCase):
    def test_every_template_builds_and_runs_offline(self):
        templates = load_templates()
        self.assertGreaterEqual(len(templates), 6)
        for t in templates:
            with self.subTest(t.name):
                agent = t.build(llm=Mock(['{"final": "ok"}'] * 5))
                self.assertTrue(agent.run(t.meta["example"]).output)
                self.assertTrue(t.evals, "needs eval cases")

    def test_readme_catalog_is_current(self):
        readme = (ROOT / "README.md").read_text()
        self.assertIn(render_catalog(), readme, "run `army catalog`")


if __name__ == "__main__":
    unittest.main()
