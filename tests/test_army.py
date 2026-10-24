"""Offline test suite: no API keys or network needed. Run with `python -m unittest discover -s tests -v`."""
import json
import os
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
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

    def test_prose_reply_gets_one_protocol_reminder(self):
        llm = Mock(["I think the answer is 42", '{"tool": "calculate", "args": {"expression": "6*7"}}', '{"final": "42"}'])
        result = Agent("t", "x", [calculate], llm=llm).run("6*7?")
        self.assertEqual(result.output, "42")
        self.assertIn("exactly ONE JSON object", llm.calls[1][1][-1]["content"])

    def test_tool_call_wins_over_empty_final(self):
        llm = Mock(['{"tool": "calculate", "args": {"expression": "2+2"}, "final": ""}', '{"final": "4"}'])
        result = Agent("t", "x", [calculate], llm=llm).run("2+2?")
        self.assertEqual([s.kind for s in result.steps], ["tool", "final"])

    def test_json_mode_requested_for_ollama_only(self):
        seen = []
        fake = lambda url, payload, headers, timeout=None: seen.append(payload) or {"choices": [{"message": {"content": '{"final": "ok"}'}}]}
        with mock.patch("army.llm._post", fake), mock.patch.dict(os.environ, {"OPENAI_API_KEY": "test"}):
            Agent("t", "x", [calculate], llm=get_llm("ollama:qwen2.5:3b")).run("q")
            Agent("t", "x", [calculate], llm=get_llm("openai:gpt-4o-mini")).run("q")
            Agent("t", "x", llm=get_llm("ollama:qwen2.5:3b")).run("q")
        self.assertEqual(seen[0]["response_format"], {"type": "json_object"})
        self.assertEqual(seen[0]["model"], "qwen2.5:3b")
        self.assertNotIn("response_format", seen[1])
        self.assertNotIn("response_format", seen[2])

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
        with mock.patch("army.web.http_get_bytes", lambda *a, **k: (rss.encode(), None)):
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
        html = urllib.request.urlopen(f"http://127.0.0.1:{port}/").read().decode()
        self.assertIn("Agent Army", html)
        token = html.split("const TOKEN=")[1].split(";")[0].strip('"')
        body = json.dumps({"template": "email-writer", "task": "hi", "model": "mock"}).encode()

        def post(headers):
            req = urllib.request.Request(f"http://127.0.0.1:{port}/api/run", data=body, headers=headers)
            try:
                return urllib.request.urlopen(req).status, None
            except urllib.error.HTTPError as e:
                return e.code, e.read()

        ok = urllib.request.Request(f"http://127.0.0.1:{port}/api/run", data=body,
                                    headers={"content-type": "application/json", "x-army-token": token})
        self.assertEqual(json.loads(urllib.request.urlopen(ok).read())["output"], "mock answer")
        # cross-site style requests are refused: no token, wrong content type, or a rebinding Host header
        self.assertEqual(post({"content-type": "text/plain"})[0], 403)
        self.assertEqual(post({"content-type": "text/plain", "x-army-token": token})[0], 415)
        self.assertEqual(post({"content-type": "application/json", "x-army-token": token, "host": "evil.example"})[0], 403)


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


class Chess(unittest.TestCase):
    """Standard perft node counts: the usual proof that castling, en passant, promotion and pins are correct."""

    def test_perft(self):
        from army.chess import START, Position, perft

        cases = [
            (START, [20, 400, 8902]),
            ("r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1", [48, 2039]),
            ("8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1", [14, 191, 2812]),
            ("r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1", [6, 264, 9467]),
            ("rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8", [44, 1486]),
        ]
        for fen, expected in cases:
            with self.subTest(fen):
                pos = Position.from_fen(fen)
                self.assertEqual([perft(pos, d) for d in range(1, len(expected) + 1)], expected)
                self.assertEqual(pos.fen(), fen)

    def test_results(self):
        from army.chess import Position

        p = Position.from_fen()
        for m in ["f2f3", "e7e5", "g2g4", "d8h4"]:
            p = p.play(p.parse(m))
        self.assertEqual(p.result(), "checkmate - Black wins")
        self.assertEqual(Position.from_fen("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1").result(), "stalemate - draw")
        self.assertEqual(Position.from_fen("8/8/4k3/8/8/4K3/4B3/8 w - - 0 1").result(), "insufficient material - draw")
        p = Position.from_fen()
        for m in ["g1f3", "g8f6", "f3g1", "f6g8"] * 2:
            p = p.play(p.parse(m))
        self.assertEqual(p.result(), "threefold repetition - draw")

    def test_arena_rejects_illegal_moves(self):
        script = ['{"final":"f2f3"}', '{"final":"e7e5"}', '{"final":"e1e8"}', '{"final":"g2g4"}', '{"final":"d8h4"}']
        out = cli.find("chess-arena").build(llm=Mock(script)).run("play").output
        self.assertIn("1. f2f3 e7e5 2. g2g4 d8h4", out)
        self.assertIn("Result: checkmate - Black wins", out)


class Regressions(unittest.TestCase):
    """One test per bug fixed, so it can't come back."""

    def test_github_repo_urls(self):
        for raw in ["psf/requests", "https://github.com/psf/requests", "github.com/psf/requests/",
                    "https://github.com/psf/requests/tree/main/src", "https://github.com/psf/requests.git"]:
            self.assertEqual(web._repo(raw), "psf/requests", raw)
        with self.assertRaises(ValueError):
            web._repo("not a repo")

    def test_feed_item_without_title_and_atom_links(self):
        rss = b"<rss><channel><item><link>https://x.test/1</link></item></channel></rss>"
        with mock.patch("army.web.http_get_bytes", lambda *a, **k: (rss, None)):
            self.assertIn("(untitled)", web.read_feed(url="u"))
        atom = (b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>T</title>'
                b'<link rel="self" href="https://x.test/self"/><link rel="alternate" href="https://x.test/post"/></entry></feed>')
        with mock.patch("army.web.http_get_bytes", lambda *a, **k: (atom, None)):
            self.assertIn("https://x.test/post", web.read_feed(url="u"))

    def test_feed_honours_declared_encoding(self):
        xml = "<?xml version='1.0' encoding='ISO-8859-1'?><rss><channel><item><title>Café</title></item></channel></rss>"
        with mock.patch("army.web.http_get_bytes", lambda *a, **k: (xml.encode("latin-1"), None)):
            self.assertIn("Café", web.read_feed(url="u"))

    def test_unknown_charset_falls_back_to_utf8(self):
        self.assertEqual(web.decode("ok".encode(), "x-made-up-charset"), "ok")

    def test_exported_skill_frontmatter_is_valid_with_colons(self):
        with tempfile.TemporaryDirectory() as d:
            cli.main(["export-skill", "code-reviewer", "--out", d])
            head = (Path(d) / "code-reviewer" / "SKILL.md").read_text().split("---")[1]
        desc_line = next(l for l in head.splitlines() if l.startswith("description:"))
        self.assertEqual(json.loads(desc_line.split(":", 1)[1]), cli.find("code-reviewer").meta["description"])

    def test_sql_missing_database_is_a_clear_error(self):
        with self.assertRaises(FileNotFoundError):
            sql_schema(db="examples/data/missing.db")

    def test_chat_typeerror_is_not_retried_silently(self):
        class Broken:
            calls = 0

            def chat(self, system, messages, **kw):
                Broken.calls += 1
                raise TypeError("bug inside the provider")

        with self.assertRaises(TypeError):
            Agent("t", "x", [calculate], llm=Broken()).run("q")
        self.assertEqual(Broken.calls, 1)

    def test_custom_llm_without_kwargs_still_works(self):
        class Plain:
            def chat(self, system, messages):
                return '{"final": "fine"}'

        self.assertEqual(Agent("t", "x", [calculate], llm=Plain()).run("q").output, "fine")

    def test_mcp_timeout_does_not_swallow_next_reply(self):
        server = MCPServer([sys.executable, str(ROOT / "tests" / "fake_mcp_server.py")], name="fake", timeout=0.5)
        try:
            server.list_tools()
            with self.assertRaises(Exception):
                server.call("slow", {"seconds": 1.5})  # times out; its late reply must be discarded
            server.timeout = 10
            time.sleep(1.5)
            self.assertEqual(server.call("echo", {"text": "next"}), "next")
        finally:
            server.close()


class Regressions2(unittest.TestCase):
    """Second full review: each test pins one fixed bug."""

    # ---- agent loop and teams
    def test_non_json_tool_results_are_shown(self):
        import datetime

        @tool
        def today() -> str:
            """Today's date."""
            return {"date": datetime.date(2026, 1, 2), "tags": {"a"}}

        llm = Mock(['{"tool": "today", "args": {}}', '{"final": "ok"}'])
        result = Agent("t", "x", [today], llm=llm).run("q")
        self.assertIn("2026-01-02", result.steps[0].content)

    def test_step_limit_never_returns_raw_tool_call(self):
        out = Agent("t", "x", [calculate], llm=Mock(['{"tool": "calculate", "args": {"expression": "1"}}'] * 5), max_steps=2).run("q").output
        self.assertTrue(out.startswith("Stopped: step limit"))

    def test_pipeline_stages_see_all_earlier_outputs(self):
        third = Mock(["done"])
        Pipeline(Agent("a", "x", llm=Mock(["BRIEF"])), Agent("b", "x", llm=Mock(["DRAFT"])), Agent("c", "x", llm=third)).run("req")
        seen = third.calls[0][1][0]["content"]
        self.assertIn("BRIEF", seen)
        self.assertIn("DRAFT", seen)

    def test_panel_can_be_delegated_to(self):
        panel = Panel([Agent("m", "x", llm=Mock(["a"]))], Agent("j", "x", llm=Mock(["merged"])))
        self.assertEqual(panel.as_tool("ask the panel")(task="q"), "merged")

    # ---- providers
    def test_gemini_blocked_prompt_is_clear_error(self):
        from army.llm import LLMError

        with mock.patch("army.llm._post", lambda *a, **k: {"candidates": [], "promptFeedback": {"blockReason": "SAFETY"}}), \
                mock.patch.dict(os.environ, {"GEMINI_API_KEY": "k"}):
            with self.assertRaises(LLMError):
                get_llm("gemini:x").chat("s", [{"role": "user", "content": "q"}])

    def test_base_url_env_is_read_at_call_time(self):
        with mock.patch.dict(os.environ, {"OPENAI_BASE_URL": "http://localhost:9999/v1"}):
            self.assertEqual(get_llm("openai:x").base, "http://localhost:9999/v1")

    # ---- CLI
    def test_schedule_survives_webhook_failure(self):
        with tempfile.TemporaryDirectory() as d, mock.patch("urllib.request.urlopen", side_effect=OSError("dns down")):
            out = Path(d) / "log.md"
            cli.main(["schedule", "email-writer", "x", "--times", "2", "--every", "0", "--webhook", "http://hook.test",
                      "--out", str(out), "--model", "mock"])
            self.assertEqual(out.read_text().count("# Email Writer"), 2)

    def test_catalog_refuses_readme_without_markers(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "README.md").write_text("intro\n<!-- catalog:start -->\nimportant docs\n")
            with mock.patch.object(cli, "ROOT", Path(d)), self.assertRaises(SystemExit):
                cli.main(["catalog"])
            self.assertIn("important docs", (Path(d) / "README.md").read_text())

    def test_export_skill_includes_panel_judge(self):
        with tempfile.TemporaryDirectory() as d:
            cli.main(["export-skill", "reader-panel", "--out", d])
            self.assertIn("## Step: editor", (Path(d) / "reader-panel" / "SKILL.md").read_text())

    def test_fen_counters_optional(self):
        from army.chess import Position

        self.assertEqual(Position.from_fen("8/8/8/8/8/8/8/K6k w").fen(), "8/8/8/8/8/8/8/K6k w - - 0 1")

    # ---- sandbox
    def _repo_with_secret(self, d):
        import subprocess as sp

        root = Path(d)
        (root / "secret.txt").write_text("TOP SECRET")
        (root / "sub").mkdir()
        (root / "sub" / "ok.txt").write_text("fine")
        env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
        for cmd in (["git", "init", "-q"], ["git", "add", "."], ["git", "commit", "-qm", "init"]):
            sp.run(cmd, cwd=root, check=True, env=env)
        return root

    def test_git_tools_cannot_leave_the_sandbox(self):
        from army.tools import git_diff, git_show

        with tempfile.TemporaryDirectory() as d:
            root = self._repo_with_secret(d)
            with mock.patch.dict(os.environ, {"ARMY_WORKDIR": str(root / "sub")}):
                with self.assertRaises((PermissionError, RuntimeError)):
                    git_show(commit="HEAD")
                with self.assertRaises((PermissionError, RuntimeError)):
                    git_diff(ref="HEAD")
            with mock.patch.dict(os.environ, {"ARMY_WORKDIR": str(root)}):
                with self.assertRaises(ValueError):
                    git_show(commit="HEAD:secret.txt")
                self.assertIn("init", git_show(commit="HEAD"))

    def test_write_file_refuses_symlinked_outputs(self):
        from army.tools import write_file

        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as elsewhere:
            os.symlink(elsewhere, Path(d) / "outputs")
            with mock.patch.dict(os.environ, {"ARMY_WORKDIR": d}), self.assertRaises(PermissionError):
                write_file(filename="x.txt", content="x")
            self.assertEqual(os.listdir(elsewhere), [])

    def test_calculator_is_fast_and_bounded(self):
        started = time.time()
        self.assertEqual(calculate(expression="**".join(["1"] * 60)), "1")
        self.assertLess(time.time() - started, 1)
        for bad in ["((9**99)**99)**99", "(10**100)**50", "9**9**9"]:
            with self.assertRaises(ValueError):
                calculate(expression=bad)
        with self.assertRaises(ValueError):
            calculate(expression="True + 1")

    # ---- data tools
    def test_ragged_csv(self):
        from army.tools import describe_csv

        with tempfile.TemporaryDirectory() as d, mock.patch.dict(os.environ, {"ARMY_WORKDIR": d}):
            (Path(d) / "a.csv").write_text("name,city\nann,paris\nbob\n")
            (Path(d) / "b.csv").write_text("a,b\n1,2,3\n4,5\n")
            self.assertIn("rows: 2", describe_csv(path="a.csv"))
            self.assertIn("more fields than the header", describe_csv(path="b.csv"))

    def test_html_title_and_line_breaks(self):
        from army.tools import html_to_text

        title, text = html_to_text("<title>Real</title><svg><title>icon</title></svg><p>one<br>two</p>")
        self.assertEqual(title, "Real")
        self.assertEqual(text, "one\ntwo")

    def test_vtt_without_hours(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.dict(os.environ, {"ARMY_WORKDIR": d}):
            (Path(d) / "t.vtt").write_text("WEBVTT\n\n00:01.000 --> 00:04.000\nHello\n\n01:05.500 --> 01:07.000\nBye\n")
            self.assertEqual(read_transcript(path="t.vtt"), "[00:01] Hello\n[01:05] Bye")

    def test_unicode_tokens(self):
        from army.rag import tokenize

        self.assertEqual(tokenize("Jürgen naïve"), ["jürgen", "naïve"])
        self.assertIn("东京", tokenize("我在东京"))

    def test_shared_memory_instances_dont_overwrite(self):
        path = Path(TMP_HOME) / "shared.json"
        a, b = Memory(path=path), Memory(path=path)
        a.add("user lives in Paris")
        b.add("user is vegetarian")
        texts = sorted(i["text"] for i in Memory(path=path).items)
        self.assertEqual(texts, ["user is vegetarian", "user lives in Paris"])

    # ---- web tools
    def test_zero_search_results_are_not_an_error(self):
        with mock.patch("army.web.http_get", lambda *a, **k: "<html></html>"), \
                mock.patch("army.web.http_json", lambda *a, **k: {"query": {"search": []}}):
            self.assertEqual(web.web_search(query="zzqq"), "no results")

    def test_github_paths_are_safe(self):
        with self.assertRaises(ValueError):
            web._repo("../..")
        seen = []
        with mock.patch("army.web._gh", lambda path: seen.append(path) or {"content": "aGk="}):
            web.github_file(repo="psf/requests", path="docs/my notes#1.md")
        self.assertEqual(seen[0], "repos/psf/requests/contents/docs/my%20notes%231.md")

    def test_feed_xhtml_content_and_weather_nulls(self):
        atom = (b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>T</title><link href="http://x"/>'
                b'<summary type="xhtml"><div xmlns="http://www.w3.org/1999/xhtml"><p>Body text</p></div></summary></entry></feed>')
        with mock.patch("army.web.http_get_bytes", lambda *a, **k: (atom, None)):
            self.assertIn("Body text", web.read_feed(url="u"))

        def fake(url, *a, **k):
            if "geocoding" in url:
                return {"results": [{"name": "X", "latitude": 1, "longitude": 2}]}
            return {"daily": {"time": ["d"], "temperature_2m_max": [None], "temperature_2m_min": [1.0], "precipitation_probability_max": [None]}}

        with mock.patch("army.web.http_json", fake):
            self.assertIn("d: 1-?C, rain ?%", web.weather(place="X"))

    # ---- MCP
    def test_mcp_concurrent_first_use_starts_one_server(self):
        server = MCPServer([sys.executable, str(ROOT / "tests" / "fake_mcp_server.py")], name="fake", timeout=20)
        results, procs = [], set()

        def worker(i):
            results.append(server.call("echo", {"text": str(i)}))
            procs.add(id(server.proc))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
        try:
            for t in threads:
                t.start()
            for t in threads:
                t.join(30)
            self.assertEqual(sorted(results), [str(i) for i in range(8)])
            self.assertEqual(len(procs), 1)
        finally:
            server.close()

    # ---- agents
    def test_twenty_questions_ignores_apostrophes(self):
        game = cli.find("twenty-questions").build(llm=Mock(['{"final": "penguin"}'] + ['{"final": "Correct"}'] * 4))
        self.assertIn("guessed 'penguin'", game.run("Let's play, you pick an animal").output)

    def test_numeric_options_accept_decimals(self):
        for name, opt in [("podcast-generator", {"minutes": "2.5"}), ("chess-arena", {"max_plies": "10.0"}),
                          ("deep-research", {"depth": "12"}), ("audio-tour-guide", {"stops": "3.0"})]:
            cli.find(name).build(**opt)
