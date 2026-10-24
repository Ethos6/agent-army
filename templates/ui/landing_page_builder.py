"""Landing Page Builder

Turns a product description (or your existing site) into a conversion-focused landing page: a clear
headline, benefit-led sections, social-proof placeholders, FAQ and one primary call to action. It
writes a single responsive HTML file with no external dependencies.
"""
from army import Agent
from army.tools import fetch_url, write_file

META = {
    "category": "ui",
    "description": "Product description or URL in, a responsive, conversion-focused single-file landing page out.",
    "example": "Landing page for a meal-prep delivery service for busy parents in Austin",
}
EVALS = [{"input": "Landing page for a dog-walking app", "must_contain": ["saved", ".html"], "max_seconds": 240}]


def build(llm=None):
    return Agent(
        name="landing-page-builder",
        instructions="""You are a conversion copywriter and front-end developer. If a URL is given, read it with `fetch_url`.
Plan the page: headline (outcome, under 10 words), subheadline, 3 benefit sections, how it works (3 steps), proof
(clearly marked placeholders, never fake testimonials), FAQ (5), final CTA.
Write ONE self-contained responsive HTML file (inline CSS, system fonts, no external assets, light/dark aware) and save
with `write_file` (landing.html). Final answer: path and the page copy outline.""",
        tools=[fetch_url, write_file],
        llm=llm,
    )
