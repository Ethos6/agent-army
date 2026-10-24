"""Offline test suite: no API keys or network needed. Run with `python -m unittest discover -s tests -v`."""
import json
import os
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
from pathlib import Path
from unittest import mock

TMP_HOME = tempfile.mkdtemp()
os.environ["ARMY_HOME"] = TMP_HOME  # keep memory files out of the real home directory

from army import Agent, Mock, Panel, Pipeline, agent_tool, get_llm, parse_action, tool  # noqa: E402
from army import cli, web  # noqa: E402
from army.mcp import MCPServer  # noqa: E402
from army.memory import Memory  # noqa: E402
from army.rag import HybridIndex, index_folder, search_tool  # noqa: E402
from army.tools import calculate, read_transcript, safe_path, search_mailbox, sql_query, sql_schema  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)


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
        self.assertIn("42", llm.calls[1][1][-1]["content"])

    def test_tool_errors_are_reported_not_raised(self):
        llm = Mock(['{"tool": "nope", "args": {}}', '{"tool": "calculate", "args": {"expression": "1/0"}}', '{"final": "ok"}'])
        result = Agent("t", "x", [calculate], llm=llm).run("go")
        self.assertIn("unknown tool", result.steps[0].content)
        self.assertIn("ZeroDivisionError", result.steps[1].content)

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


class Orchestration(unittest.TestCase):
    def test_pipeline_passes_output_forward(self):
        b_llm = Mock(["final v2"])
        result = Pipeline(Agent("a", "x", llm=Mock(["draft v1"])), Agent("b", "y", llm=b_llm)).run("brief")
        self.assertEqual(result.output, "final v2")
        self.assertIn("draft v1", b_llm.calls[0][1][0]["content"])

    def test_panel_judge_sees_every_answer(self):
        judge = Mock(["merged"])
        panel = Panel([Agent("m1", "x", llm=Mock(["alpha"])), Agent("m2", "x", llm=Mock(["beta"]))], Agent("j", "x", llm=judge))
        self.assertEqual(panel.run("q").output, "merged")
        self.assertIn("alpha", judge.calls[0][1][0]["content"])
        self.assertIn("beta", judge.calls[0][1][0]["content"])

    def test_manager_delegates_to_worker(self):
        worker = Agent("worker", "x", llm=Mock(["worker result 7"]))
        manager_llm = Mock(['{"tool": "ask_worker", "args": {"task": "do it"}}', '{"final": "done"}'])
        Agent("manager", "x", tools=[agent_tool(worker, "does work")], llm=manager_llm).run("go")
        self.assertIn("worker result 7", manager_llm.calls[1][1][-1]["content"])


class Safety(unittest.TestCase):
    def test_calculator_rejects_code(self):
        for bad in ["__import__('os')", "open('x')", "2**10000"]:
            with self.assertRaises(Exception):
                calculate(expression=bad)
        self.assertEqual(calculate(expression="(1200-950)/950*100")[:5], "26.31")

    def test_sandbox_blocks_escape(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.dict(os.environ, {"ARMY_WORKDIR": d}):
            with self.assertRaises(PermissionError):
                safe_path("../../etc/passwd")

    def test_sql_is_read_only(self):
        with self.assertRaises(PermissionError):
            sql_query(db="examples/data/shop.db", sql="DELETE FROM orders")
        self.assertIn("orders", sql_schema(db="examples/data/shop.db"))
        out = sql_query(db="examples/data/shop.db", sql="SELECT country, COUNT(*) FROM customers c JOIN orders o ON o.customer_id=c.id GROUP BY country ORDER BY 2 DESC LIMIT 1")
        self.assertIn("India | 4", out)


class Data(unittest.TestCase):
    def test_bm25_finds_and_cites(self):
        index = index_folder("examples/knowledge-base")
        self.assertEqual(index.search("refund window pro plan")[0][1].source, "pricing.md")
        self.assertIn("security.md:", search_tool(index)(query="rotate api key"))

    def test_hybrid_fuses_keyword_and_vector(self):
        index = index_folder("examples/knowledge-base")
        fake = lambda texts, spec=None: [[1.0, 0.0] if "refund" in t.lower() else [0.0, 1.0] for t in texts]
        with mock.patch("army.rag.embed", fake):
            hits = HybridIndex(index).search("refund", 2)
        self.assertEqual(hits[0][1].source, "pricing.md")

    def test_transcript_and_mailbox(self):
        self.assertIn("[01:02]", read_transcript(path="examples/talks/keynote.vtt"))
        self.assertIn("INV-2291", search_mailbox(path="examples/mail/sample.mbox", query="invoice overdue"))

    def test_feed_and_search_parsers(self):
        rss = '<rss><channel><item><title>Hello</title><link>https://x.test/1</link><pubDate>Mon</pubDate><description>&lt;p&gt;Body&lt;/p&gt;</description></item></channel></rss>'
        with mock.patch("army.web.http_get", lambda *a, **k: rss):
            self.assertIn("https://x.test/1", web.read_feed(url="https://x.test/feed"))
        html = '<a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fa.test%2Fp">A <b>title</b></a> <a class="result__snippet" href="#">snip</a>'
        with mock.patch("army.web.http_get", lambda *a, **k: html):
            self.assertEqual(web._ddg("q", 3)[0]["url"], "https://a.test/p")


class MemoryTest(unittest.TestCase):
    def test_remember_recall_forget_persist(self):
        path = Path(TMP_HOME) / "t.json"
        m = Memory(path=path)
        i = m.add("User is vegetarian", "preference")
        m.add("User lives in Pune")
        self.assertEqual(m.search("food vegetarian")[0]["id"], i)
        self.assertEqual(Memory(path=path).search("Pune")[0]["text"], "User lives in Pune")  # persisted
        self.assertTrue(m.remove(i))
        self.assertEqual(m.add("User lives in Pune"), 2)  # no duplicates


class MCP(unittest.TestCase):
    def test_client_against_fake_server(self):
        server = MCPServer([sys.executable, str(ROOT / "tests" / "fake_mcp_server.py")], name="fake", timeout=20)
        try:
            listing, call = server.tools()
            self.assertIn("echo(text: string)", listing())
            self.assertEqual(call(tool_name="add", arguments={"a": 2, "b": 3}), "5")
            self.assertEqual({t.name for t in server.as_tools()}, {"echo", "add"})
        finally:
            server.close()


class Providers(unittest.TestCase):
    def test_spec_parsing(self):
        self.assertEqual(repr(get_llm("openai:gpt-4o-mini")), "openai:gpt-4o-mini")
        self.assertEqual(get_llm("ollama").model, "llama3.2")
        with self.assertRaises(Exception):
            get_llm("nonsense:x")


class Templates(unittest.TestCase):
    def test_validate_reports_no_problems(self):
        self.assertEqual(cli.validate_all(), [])

    def test_every_template_runs_offline(self):
        templates = cli.load_templates()
        self.assertGreaterEqual(len(templates), 100)
        for t in templates:
            with self.subTest(t.name):
                self.assertTrue(t.build(llm=Mock()).run(t.meta["example"]).output)

    def test_games_end_even_with_illegal_moves(self):
        for name in ("tic-tac-toe-arena", "connect-four-arena"):
            out = cli.find(name).build(llm=Mock(["not a move"] * 500), seed="1").run("play").output
            self.assertIn("Result:", out)

    def test_generated_files_are_current(self):
        self.assertIn(cli.render_catalog(), (ROOT / "README.md").read_text(), "run `army catalog`")
        self.assertEqual(cli.render_docs() + "\n", (ROOT / "docs" / "TEMPLATES.md").read_text(), "run `army docs`")


class CLI(unittest.TestCase):
    def test_export_skill(self):
        with tempfile.TemporaryDirectory() as d:
            cli.main(["export-skill", "docs-qa", "--out", d])
            text = (Path(d) / "docs-qa" / "SKILL.md").read_text()
        self.assertTrue(text.startswith("---\nname: docs-qa\n"))

    def test_schedule_once_to_file(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "log.md"
            cli.main(["schedule", "email-writer", "ask for a day off", "--times", "1", "--out", str(out), "--model", "mock"])
            self.assertIn("mock answer", out.read_text())

    def test_playground_api(self):
        from army.playground import serve

        port = 8799
        threading.Thread(target=serve, args=("127.0.0.1", port), daemon=True).start()
        for _ in range(50):
            try:
                catalog = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/api/templates").read())
                break
            except OSError:
                time.sleep(0.1)
        self.assertGreaterEqual(len(catalog), 100)
        req = urllib.request.Request(f"http://127.0.0.1:{port}/api/run", data=json.dumps(
            {"template": "email-writer", "task": "hi", "model": "mock"}).encode(), headers={"content-type": "application/json"})
        self.assertEqual(json.loads(urllib.request.urlopen(req).read())["output"], "mock answer")
        self.assertIn(b"Agent Army", urllib.request.urlopen(f"http://127.0.0.1:{port}/").read())


if __name__ == "__main__":
    unittest.main()


class LiveFormats(unittest.TestCase):
    """Parsers checked against real responses captured from each public API (tests/fixtures.json)."""

    F = json.loads((ROOT / "tests" / "fixtures.json").read_text())

    def route(self, url, *a, **k):
        F = self.F
        for key, frag in (("geo", "geocoding-api"), ("forecast", "api.open-meteo"), ("fx", "er-api"), ("wiki_search", "list=search"),
                          ("wiki_extract", "prop=extracts"), ("yahoo", "finance.yahoo"), ("hn_ids", "topstories"), ("hn_item", "/item/")):
            if frag in url:
                return F[key]
        raise AssertionError(f"unexpected url {url}")

    def test_json_apis(self):
        with mock.patch("army.web.http_json", self.route):
            self.assertIn("Lisbon, Portugal", web.weather(place="Lisbon"))
            self.assertIn("2026-10-24: 10-22C, rain 0%", web.weather(place="Lisbon"))
            self.assertIn("100.00 USD = 9,503.65 INR", web.exchange_rate(base="usd", target="inr", amount=100))
            self.assertIn("change=+1.4%", web.stock_history(symbol="AAPL", period="5d"))
            self.assertIn("RAG", web.wikipedia(topic="RAG"))
            self.assertIn("[900 pts, 461 comments] Example story", web.hacker_news(n=1))

    def test_arxiv_atom(self):
        with mock.patch("army.web.http_get", lambda *a, **k: self.F["arxiv"]):
            out = web.arxiv_search(query="rag", n=1)
        self.assertIn("RAG System for Supporting Japanese Litigation Procedures (2025-11-28)", out)
        self.assertIn("Yuya Ishihara, Atsushi Keyaki", out)
