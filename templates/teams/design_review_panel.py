"""Design Review Panel

Three expert reviewers critique a web page or product description independently (a usability
expert, an accessibility expert and a visual and brand designer), then a design lead merges their
findings into one prioritized list with severity, so you get the breadth of a panel without the
meeting.
"""
from army import Agent, Panel
from army.tools import fetch_url

META = {
    "category": "teams",
    "description": "Usability, accessibility and visual experts review a page independently; a lead prioritizes fixes.",
    "example": "Review https://www.python.org",
}
EVALS = [{"input": "Review https://www.wikipedia.org", "must_contain": ["Severity", "accessibility"], "max_seconds": 300}]

REVIEWERS = {
    "usability-expert": "a usability expert applying Nielsen's heuristics: navigation, clarity, feedback, error prevention",
    "accessibility-expert": "a WCAG 2.2 accessibility expert: structure, headings, alt text, contrast cues, link text, keyboard paths",
    "visual-designer": "a visual and brand designer: hierarchy, typography, spacing, consistency, trust signals",
}


def build(llm=None):
    members = [
        Agent(name, f"You are {desc}. Read the page with `fetch_url`. List findings with evidence (quote the page) and a fix.",
              tools=[fetch_url], llm=llm)
        for name, desc in REVIEWERS.items()
    ]
    lead = Agent("design-lead", """Merge the reviews into:
| # | Finding | Area (usability/accessibility/visual) | Severity (critical/major/minor) | Fix |
Sort by severity, merge duplicates, then ## Quick wins and ## Bigger redesign ideas.""", llm=llm)
    return Panel(members, lead, name="design-review-panel")
