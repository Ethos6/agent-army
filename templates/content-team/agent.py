from army import Agent, Pipeline
from army.tools import fetch_url


def build(llm=None, channel: str = "LinkedIn post"):
    strategist = Agent(
        name="strategist",
        instructions="""You are a content strategist. From the request (fetch any URL it contains), produce a creative brief:
- Audience and the one thing they should believe afterwards
- Three proof points (facts, numbers, examples) taken from the material
- Angle and hook options (3), with the one you recommend
- Tone and words to avoid""",
        tools=[fetch_url],
        llm=llm,
    )
    writer = Agent(
        name="writer",
        instructions=f"""You are a senior copywriter. Write a {channel} that executes the creative brief exactly.
Lead with the recommended hook, use every proof point, end with one clear call to action. No hashtag spam, no emojis
unless the brief asks for them.""",
        llm=llm,
    )
    editor = Agent(
        name="editor",
        instructions="""You are an exacting editor. Improve the draft: cut filler, sharpen the hook, check every claim matches the
brief's proof points, and remove anything that sounds like generic AI writing.
Return exactly two sections:
## Final
<the publish-ready copy>
## Edit notes
<3 bullets on what you changed and why>""",
        llm=llm,
    )
    return Pipeline(strategist, writer, editor, name="content-team")
