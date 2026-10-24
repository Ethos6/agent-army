"""Web Data Extractor

Describe what you want from a website in plain English ("every product name and price", "all
speakers and talk titles"). The agent reads the page (and linked pages on the same site if needed),
extracts exactly those fields, and saves a clean CSV or JSON file to outputs/.
"""
from army import Agent
from army.web import crawl_site
from army.tools import fetch_url, write_file

META = {
    "category": "starter",
    "description": "Turns any web page into a clean CSV/JSON of the fields you describe, saved to outputs/.",
    "example": "Extract every heading and its first sentence from https://en.wikipedia.org/wiki/Web_scraping as CSV",
}
EVALS = [{"input": "List the section headings of https://en.wikipedia.org/wiki/Web_scraping as JSON", "must_contain": ["saved"], "max_seconds": 180}]


def build(llm=None):
    return Agent(
        name="web-extractor",
        instructions="""You extract structured data from websites.

1. `fetch_url` the page. If the data spans several pages on the same site, use `crawl_site`.
2. Extract ONLY the fields the user asked for. Keep values exactly as written on the page. Use "" for missing values; never invent.
3. Save with `write_file`: CSV (header row, comma-separated, quoted when needed) unless the user asks for JSON.
4. Final answer: the file path, row count, the first 5 rows as a Markdown table, and any fields that were often missing.""",
        tools=[fetch_url, crawl_site, write_file],
        llm=llm,
    )
