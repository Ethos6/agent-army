"""Chat with a Video Transcript

Download the subtitles of any talk, video or meeting as .vtt or .srt (most platforms and tools can
export them) and ask questions. Answers include [mm:ss] timestamps so you can jump to the moment,
and the agent can produce chapter markers, summaries and quotable lines.
"""
from army import Agent
from army.tools import read_transcript

META = {
    "category": "chat",
    "description": "Q&A, chapters and summaries for any .vtt/.srt transcript, with [mm:ss] timestamps.",
    "example": "What does the speaker in examples/talks/keynote.vtt recommend, and when?",
}
EVALS = [{"input": "What cost saving is mentioned in examples/talks/keynote.vtt and when?", "must_contain": ["forty", "01:"], "max_seconds": 120}]


def build(llm=None):
    return Agent(
        name="chat-with-transcript",
        instructions="""Read the transcript with `read_transcript`. Answer only from it, with [mm:ss] timestamps for every claim.
If asked for chapters, give | Time | Chapter | One-line summary |. If the transcript doesn't cover it, say so.""",
        tools=[read_transcript],
        llm=llm,
    )
