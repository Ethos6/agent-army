"""Live checks against real services. Skipped unless ARMY_LIVE=1 (CI runs them in a separate job).

ARMY_LIVE=1      real public APIs used by army.web (no keys needed)
ARMY_LIVE_MCP=1  real MCP servers started with npx (needs Node.js)
"""
import os
import unittest
from pathlib import Path

from army import web
from army.tools import fetch_url

ROOT = Path(__file__).resolve().parent.parent
LIVE = os.environ.get("ARMY_LIVE") == "1"
LIVE_MCP = os.environ.get("ARMY_LIVE_MCP") == "1"


@unittest.skipUnless(LIVE, "set ARMY_LIVE=1 to call real services")
class LiveWeb(unittest.TestCase):
    def check(self, out, *needles):
        print("\n" + str(out)[:300])
        for n in needles:
            self.assertIn(n.lower(), str(out).lower())

    def test_wikipedia(self):
        self.check(web.wikipedia(topic="Retrieval-augmented generation"), "retrieval")

    def test_web_search(self):
        hits = web.search("python asyncio tutorial", 5)
        self.assertTrue(hits and all(h["url"].startswith("http") for h in hits))

    def test_weather(self):
        self.check(web.weather(place="Lisbon"), "Lisbon", "rain")

    def test_exchange_rate(self):
        self.check(web.exchange_rate(base="USD", target="EUR", amount=10), "USD =", "EUR")

    def test_hacker_news(self):
        self.check(web.hacker_news(n=3), "pts")

    def test_arxiv(self):
        self.check(web.arxiv_search(query="retrieval augmented generation", n=2), "arxiv.org")

    def test_github(self):
        self.check(web.github_repo(repo="psf/requests"), "psf/requests", "sessions.py")
        self.check(web.github_releases(repo="psf/requests", n=1), "##")

    def test_pypi(self):
        self.check(web.pypi_package(name="requests"), "latest=")

    def test_feed(self):
        self.check(web.read_feed(url="https://hnrss.org/frontpage", n=2), "http")

    def test_fetch_and_crawl(self):
        self.check(fetch_url(url="https://www.python.org"), "Python")
        self.check(web.crawl_site(url="https://www.python.org", max_pages=2), "python.org")

    def test_stock_history(self):
        try:
            out = web.stock_history(symbol="AAPL", period="1mo")
        except Exception as e:  # unofficial endpoint: rate limits on shared CI IPs are common
            self.skipTest(f"market data endpoint unavailable from this runner: {e}")
        self.check(out, "AAPL", "change=")


@unittest.skipUnless(LIVE_MCP, "set ARMY_LIVE_MCP=1 to start real MCP servers (needs npx)")
class LiveMCP(unittest.TestCase):
    def test_filesystem_server(self):
        from army.mcp import MCPServer

        folder = str(ROOT / "examples")
        server = MCPServer(["npx", "-y", "@modelcontextprotocol/server-filesystem", folder], name="fs", timeout=180)
        try:
            listing, call = server.tools()
            tools = listing()
            print("\n" + tools[:500])
            self.assertIn("list_directory", tools)
            out = call(tool_name="list_directory", arguments={"path": str(ROOT / "examples" / "knowledge-base")})
            self.assertIn("pricing.md", out)
        finally:
            server.close()

    def test_memory_server(self):
        from army.mcp import MCPServer

        server = MCPServer(["npx", "-y", "@modelcontextprotocol/server-memory"], name="memory", timeout=180)
        try:
            names = {t.name for t in server.as_tools()}
            print("\n", sorted(names))
            self.assertIn("create_entities", names)
        finally:
            server.close()


if __name__ == "__main__":
    unittest.main()
