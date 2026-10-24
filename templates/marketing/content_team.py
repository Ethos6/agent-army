"""Content Team

Three specialists run in order. A strategist reads your source material and writes a creative brief
(audience, proof points, hooks, tone), a writer drafts the piece to the brief, and an editor tightens
it, checks every claim against the brief, and returns publish-ready copy with edit notes.
"""
from army import Agent, Pipeline
from army.tools import fetch_url

META = {
    "category": "marketing",
    "description": "Strategist writes the brief, writer drafts, editor cuts it to publish-ready copy with edit notes.",
    "example": "Announce our new open-source agent framework to developers",
}
EVALS = [{"input": "Announce a new open-source AI agent framework that runs on any model", "must_contain": ["## Final", "## Edit notes"], "max_seconds": 240}]


def build(llm=None, channel: str = "LinkedIn post"):
    strategist = Agent("strategist", """You are a content strategist. From the request (fetch any URL it contains), produce a creative brief:
- Audience and the one thing they should believe afterwards
- Three proof points (facts, numbers, examples) taken from the material
- Three hook options and the one you recommend
- Tone and words to avoid""", tools=[fetch_url], llm=llm)
    writer = Agent("writer", f"""You are a senior copywriter. Write a {channel} that executes the creative brief exactly.
Lead with the recommended hook, use every proof point, end with one clear call to action.
No hashtag spam and no emojis unless the brief asks for them.""", llm=llm)
    editor = Agent("editor", """You are an exacting editor. Improve the draft: cut filler, sharpen the hook, check every claim
matches the brief's proof points, and remove anything that sounds like generic AI writing.
Return exactly two sections:
## Final
<the publish-ready copy>
## Edit notes
<3 bullets on what you changed and why>""", llm=llm)
    return Pipeline(strategist, writer, editor, name="content-team")
