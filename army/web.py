"""Network tools (stdlib only). None of them need an API key; optional keys improve web search."""
from __future__ import annotations

import base64
import json
import os
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from html import unescape

from .agent import tool
from .tools import html_to_text

UA = {"user-agent": "Mozilla/5.0 (agent-army)"}


def http_get_bytes(url: str, headers: dict | None = None, timeout: int = 30, limit: int = 3_000_000) -> tuple[bytes, str | None]:
    req = urllib.request.Request(url, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read(limit), resp.headers.get_content_charset()


def decode(raw: bytes, charset: str | None) -> str:
    try:
        return raw.decode(charset or "utf-8", "replace")
    except LookupError:  # server sent an unknown charset name
        return raw.decode("utf-8", "replace")


def http_get(url: str, headers: dict | None = None, timeout: int = 30, limit: int = 3_000_000) -> str:
    return decode(*http_get_bytes(url, headers, timeout, limit))


def http_json(url: str, headers: dict | None = None, data: dict | None = None, timeout: int = 30):
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(
        url, data=body, headers={**UA, "content-type": "application/json", **(headers or {})}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def q(s: str) -> str:
    return urllib.parse.quote(s, safe="")


# ---------------------------------------------------------------- search
def _ddg(query: str, n: int) -> list[dict]:
    html = http_get("https://html.duckduckgo.com/html/?q=" + q(query))
    out = []
    for m in re.finditer(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>.*?class="result__snippet"[^>]*>(.*?)</a>', html, re.S):
        href, title, snippet = m.groups()
        target = urllib.parse.parse_qs(urllib.parse.urlparse(unescape(href)).query).get("uddg", [unescape(href)])[0]
        strip = lambda s: unescape(re.sub(r"<[^>]+>", "", s)).strip()
        out.append({"title": strip(title), "url": target, "snippet": strip(snippet)})
        if len(out) >= n:
            break
    return out


def _brave(query: str, n: int) -> list[dict]:
    r = http_json(
        f"https://api.search.brave.com/res/v1/web/search?count={n}&q=" + q(query),
        {"x-subscription-token": os.environ["BRAVE_API_KEY"], "accept": "application/json"},
    )
    return [{"title": x["title"], "url": x["url"], "snippet": x.get("description", "")} for x in r["web"]["results"][:n]]


def _tavily(query: str, n: int) -> list[dict]:
    r = http_json("https://api.tavily.com/search", data={"api_key": os.environ["TAVILY_API_KEY"], "query": query, "max_results": n})
    return [{"title": x["title"], "url": x["url"], "snippet": x.get("content", "")[:300]} for x in r["results"]]


def search(query: str, n: int = 6) -> list[dict]:
    """Web search with graceful fallback: Tavily -> Brave -> DuckDuckGo -> Wikipedia."""
    errors = []
    for env, fn in (("TAVILY_API_KEY", _tavily), ("BRAVE_API_KEY", _brave), (None, _ddg)):
        if env and not os.environ.get(env):
            continue
        try:
            hits = fn(query, n)
            if hits:
                return hits
        except Exception as e:  # try the next backend
            errors.append(f"{fn.__name__}: {e}")
    hits = _wiki_search(query, n)
    if hits:
        return hits
    raise RuntimeError("all search backends failed: " + "; ".join(errors))


@tool
def web_search(query: str, n: int = 6) -> str:
    """Search the web. Returns numbered results with title, URL and snippet."""
    hits = search(query, int(n))
    return "\n".join(f"{i}. {h['title']}\n   {h['url']}\n   {h['snippet']}" for i, h in enumerate(hits, 1)) or "no results"


# ---------------------------------------------------------------- wikipedia
def _wiki_search(query: str, n: int) -> list[dict]:
    r = http_json("https://en.wikipedia.org/w/api.php?action=query&list=search&format=json&srlimit=%d&srsearch=%s" % (n, q(query)))
    return [
        {
            "title": x["title"],
            "url": "https://en.wikipedia.org/wiki/" + q(x["title"].replace(" ", "_")),
            "snippet": unescape(re.sub(r"<[^>]+>", "", x["snippet"])),
        }
        for x in r["query"]["search"]
    ]


@tool
def wikipedia(topic: str) -> str:
    """Get the plain-text Wikipedia article for the best match to a topic (first ~8,000 characters)."""
    hits = _wiki_search(topic, 1)
    if not hits:
        return "no article found"
    title = hits[0]["title"]
    r = http_json("https://en.wikipedia.org/w/api.php?action=query&prop=extracts&explaintext=1&format=json&redirects=1&titles=" + q(title))
    page = next(iter(r["query"]["pages"].values()))
    return f"TITLE: {page['title']}\nURL: {hits[0]['url']}\n\n{page.get('extract', '')[:8000]}"


# ---------------------------------------------------------------- arxiv
@tool
def arxiv_search(query: str, n: int = 5) -> str:
    """Search arXiv papers. Returns title, authors, date, abstract and link for each."""
    xml = http_get(f"https://export.arxiv.org/api/query?max_results={int(n)}&sortBy=relevance&search_query=all:" + q(query))
    ns = {"a": "http://www.w3.org/2005/Atom"}
    out = []
    for e in ET.fromstring(xml).findall("a:entry", ns):
        g = lambda tag: " ".join((e.findtext(tag, "", ns) or "").split())
        authors = ", ".join(a.findtext("a:name", "", ns) for a in e.findall("a:author", ns)[:4])
        out.append(f"- {g('a:title')} ({g('a:published')[:10]})\n  {authors}\n  {g('a:id')}\n  {g('a:summary')[:700]}")
    return "\n".join(out) or "no papers found"


# ---------------------------------------------------------------- hacker news
@tool
def hacker_news(n: int = 15) -> str:
    """Current top Hacker News stories with score, comment count and link."""
    ids = http_json("https://hacker-news.firebaseio.com/v0/topstories.json")[: int(n)]
    lines = []
    for i in ids:
        s = http_json(f"https://hacker-news.firebaseio.com/v0/item/{i}.json") or {}
        lines.append(f"- [{s.get('score', 0)} pts, {s.get('descendants', 0)} comments] {s.get('title')} :: {s.get('url') or 'https://news.ycombinator.com/item?id=%d' % i}")
    return "\n".join(lines)


# ---------------------------------------------------------------- github
def _gh(path: str):
    headers = {"accept": "application/vnd.github+json"}
    if os.environ.get("GITHUB_TOKEN"):
        headers["authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    return http_json("https://api.github.com/" + path.lstrip("/"), headers)


def _repo(repo: str) -> str:
    """Accept owner/name or any github.com URL (including /tree/..., /blob/..., .git)."""
    path = re.sub(r"^(https?://)?(www\.)?github\.com/", "", repo.strip()).strip("/")
    parts = path.split("/")
    if len(parts) < 2 or not all(re.fullmatch(r"[\w.-]+", x) for x in parts[:2]):
        raise ValueError("repo must look like owner/name or a github.com URL")
    return f"{parts[0]}/{parts[1].removesuffix('.git')}"


@tool
def github_repo(repo: str) -> str:
    """Overview of a GitHub repo (owner/name): description, stars, languages, file tree and README."""
    r = _repo(repo)
    info = _gh(f"repos/{r}")
    tree = _gh(f"repos/{r}/git/trees/{info['default_branch']}?recursive=1").get("tree", [])
    files = [t["path"] for t in tree if t["type"] == "blob"]
    try:
        readme = base64.b64decode(_gh(f"repos/{r}/readme")["content"]).decode("utf-8", "replace")
    except Exception:
        readme = "(no README)"
    return (
        f"{info['full_name']}: {info.get('description')}\nstars={info['stargazers_count']} forks={info['forks_count']} "
        f"language={info.get('language')} license={(info.get('license') or {}).get('spdx_id')} updated={info['pushed_at']}\n"
        f"\nFILES ({len(files)}):\n" + "\n".join(files[:150]) + f"\n\nREADME:\n{readme[:6000]}"
    )


@tool
def github_file(repo: str, path: str) -> str:
    """Read one file from a GitHub repo (owner/name) by path."""
    data = _gh(f"repos/{_repo(repo)}/contents/{path.lstrip('/')}")
    if isinstance(data, list):  # a directory, not a file
        return "This is a directory. Entries:\n" + "\n".join(f"{x['type']}: {x['path']}" for x in data)
    if data.get("content"):
        return base64.b64decode(data["content"]).decode("utf-8", "replace")[:20000]
    return http_get(data["download_url"])[:20000]  # files over 1 MB come without inline content


@tool
def github_releases(repo: str, n: int = 5) -> str:
    """Latest releases of a GitHub repo (owner/name) with dates and release notes."""
    rel = _gh(f"repos/{_repo(repo)}/releases?per_page={int(n)}")
    return "\n\n".join(f"## {x.get('name') or x['tag_name']} ({x['published_at'][:10]})\n{(x.get('body') or '')[:2500]}" for x in rel) or "no releases"


# ---------------------------------------------------------------- weather, money, markets
@tool
def weather(place: str) -> str:
    """7-day weather forecast for a place name (daily high/low in C and chance of rain)."""
    g = http_json("https://geocoding-api.open-meteo.com/v1/search?count=1&name=" + q(place)).get("results")
    if not g:
        return f"place not found: {place}"
    g = g[0]
    f = http_json(
        "https://api.open-meteo.com/v1/forecast?timezone=auto&forecast_days=7"
        f"&latitude={g['latitude']}&longitude={g['longitude']}"
        "&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max"
    )["daily"]
    rows = [
        f"{d}: {lo:.0f}-{hi:.0f}C, rain {p}%"
        for d, hi, lo, p in zip(f["time"], f["temperature_2m_max"], f["temperature_2m_min"], f["precipitation_probability_max"])
    ]
    return f"{g['name']}, {g.get('country', '')}\n" + "\n".join(rows)


@tool
def exchange_rate(base: str, target: str, amount: float = 1.0) -> str:
    """Convert an amount between currencies using today's reference rates (e.g. USD to INR)."""
    r = http_json(f"https://open.er-api.com/v6/latest/{base.upper()}")
    rate = r["rates"][target.upper()]
    return f"{float(amount):,.2f} {base.upper()} = {float(amount) * rate:,.2f} {target.upper()} (rate {rate}, updated {r.get('time_last_update_utc', '?')})"


@tool
def stock_history(symbol: str, period: str = "6mo") -> str:
    """Daily closing prices summary for a stock ticker (period: 1mo|3mo|6mo|1y|5y). Unofficial public endpoint."""
    r = http_json(f"https://query1.finance.yahoo.com/v8/finance/chart/{q(symbol.upper())}?interval=1d&range={q(period)}")
    res = r["chart"]["result"][0]
    closes = [c for c in res["indicators"]["quote"][0]["close"] if c is not None]
    meta = res["meta"]
    if not closes:
        return "no data"
    first, last = closes[0], closes[-1]
    return (
        f"{symbol.upper()} ({meta.get('currency')}, {meta.get('exchangeName')}) over {period}: "
        f"start={first:.2f} last={last:.2f} change={(last - first) / first * 100:+.1f}% "
        f"high={max(closes):.2f} low={min(closes):.2f}\nlast 10 closes: {[round(c, 2) for c in closes[-10:]]}"
    )


@tool
def pypi_package(name: str) -> str:
    """Latest version, release date, Python requirement and yanked status for a PyPI package."""
    r = http_json(f"https://pypi.org/pypi/{q(name)}/json")
    info, releases = r["info"], r["releases"]
    latest = info["version"]
    files = releases.get(latest, [])
    date = files[0]["upload_time"][:10] if files else "?"
    yanked = [v for v, fs in releases.items() if fs and all(f.get("yanked") for f in fs)]
    return f"{info['name']} latest={latest} ({date}) requires_python={info.get('requires_python')} yanked_versions={yanked[-10:]} summary={info.get('summary')}"


# ---------------------------------------------------------------- feeds and sites
@tool
def read_feed(url: str, n: int = 10) -> str:
    """Read an RSS or Atom feed (blogs, newsletters, news). Returns latest items with date, link and summary."""
    raw, _ = http_get_bytes(url)
    root = ET.fromstring(raw)  # bytes, so the XML declaration's own encoding is honoured
    items = []
    for el in root.iter():
        tag = el.tag.split("}")[-1]
        if tag not in ("item", "entry"):
            continue
        get = lambda *names: next((c for c in el if c.tag.split("}")[-1] in names), None)
        links = [c for c in el if c.tag.split("}")[-1] == "link"]
        alt = next((c for c in links if c.get("rel") in (None, "alternate")), links[0] if links else None)
        link = (alt.get("href") or alt.text or "") if alt is not None else ""
        date = get("pubDate", "published", "updated")
        summary = get("description", "summary", "content")
        text = html_to_text(summary.text or "")[1] if summary is not None else ""
        title_el = get("title")
        title = (title_el.text or "").strip() if title_el is not None else "(untitled)"
        items.append(f"- {title} ({((date.text or '') if date is not None else '')[:25]})\n  {link or ''}\n  {text[:400]}")
        if len(items) >= int(n):
            break
    return "\n".join(items) or "no items"


@tool
def crawl_site(url: str, max_pages: int = 6) -> str:
    """Read a website: the start page plus up to max_pages linked pages on the same domain."""
    start = urllib.parse.urlparse(url)
    queue, seen, out = [url], set(), []
    while queue and len(seen) < int(max_pages):
        u = queue.pop(0).split("#")[0]
        if u in seen:
            continue
        seen.add(u)
        try:
            html = http_get(u, limit=1_500_000)
        except Exception as e:
            out.append(f"## {u}\n(error: {e})")
            continue
        title, text = html_to_text(html)
        out.append(f"## {title or u}\n{u}\n{text[:2500]}")
        for href in re.findall(r'href="([^"#]+)"', html):
            nxt = urllib.parse.urljoin(u, href)
            p = urllib.parse.urlparse(nxt)
            if p.netloc == start.netloc and p.scheme in ("http", "https") and not re.search(r"\.(png|jpe?g|gif|svg|pdf|zip|css|js)$", p.path):
                queue.append(nxt)
    return "\n\n".join(out)
