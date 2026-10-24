"""Reader Panel

Simulates how real readers experience your draft before you publish. Three distinct reader personas
read it independently and report where they got bored, confused or stopped, and what they remember
afterwards; an editor then combines their reports into a heat map of the draft. It never rewrites
your text; it tells you where it loses people.
"""
from army import Agent, Panel
from army.tools import fetch_url, read_file

META = {
    "category": "marketing",
    "description": "Three simulated reader personas report where your draft loses them; nothing gets rewritten.",
    "example": "Panel-read examples/knowledge-base/pricing.md as if it were a blog post for small-business owners",
}
EVALS = [{"input": "Panel-read this: 'Our new feature is here. It does many things. You will like it. Try it.'", "must_contain": ["Drop-off", "Remembered"], "max_seconds": 240}]

PERSONAS = [
    ("skimmer", "a busy reader who skims on a phone and leaves at the first dull paragraph"),
    ("skeptic", "an expert skeptic who stops trusting the text at the first unsupported claim"),
    ("newcomer", "a newcomer who gets lost at undefined jargon or skipped steps"),
]


def build(llm=None, audience: str = ""):
    who = f" The target audience is {audience}." if audience else ""
    members = [
        Agent(name, f"""You are {desc}.{who} Read the draft (use `read_file` or `fetch_url` if a path or URL is given).
Do NOT rewrite it. Report honestly:
- Drop-off: the exact sentence where you would stop or skim, and why
- Confusing: quotes of unclear parts
- Remembered: the 1-3 things you'd recall tomorrow
- Trust: claims you didn't believe""", tools=[read_file, fetch_url], llm=llm)
        for name, desc in PERSONAS
    ]
    editor = Agent("editor", """Combine the reader reports. Do not rewrite the draft.
## Heat map (section by section: holds / sags / loses readers, with which personas)
## Drop-off points (quotes)
## Remembered vs intended message
## Top 3 fixes (described, not written)""", llm=llm)
    return Panel(members, editor, name="reader-panel")
