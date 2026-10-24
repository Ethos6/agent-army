"""Audio Tour Guide

Creates a self-guided audio tour of a place for your interests and walking pace. It researches the
stops, orders them into a sensible walking route, writes a narration segment for each with stories
and things to look for, and saves each segment as an MP3 you can play on the go.
"""
from army import Agent
from army.voice import text_to_speech
from army.web import web_search, wikipedia

META = {
    "category": "voice",
    "description": "A researched walking tour with one narrated MP3 per stop, tuned to your interests and pace.",
    "example": "A 60-minute architecture-focused audio tour of central Barcelona",
    "needs": "OPENAI_API_KEY (or an OpenAI-compatible text-to-speech server).",
}
EVALS = [{"input": "A 20-minute history tour of the Roman Forum", "must_contain": ["Stop 1", ".mp3"], "max_seconds": 400}]


def build(llm=None, stops: str = "5"):
    return Agent(
        name="audio-tour-guide",
        instructions=f"""You are an expert local guide. Research with `wikipedia` and `web_search`. Choose {stops} stops in a walkable order.
For each stop write a 60-120 second narration (story, what to look at, one surprising fact), then save it with
`text_to_speech` (filename stop_<n>.mp3).
Final answer: route overview, then per stop: ### Stop N: name, walking time from previous, file path, narration text.""",
        tools=[wikipedia, web_search, text_to_speech],
        llm=llm,
        max_steps=max(1, int(float(stops))) * 2 + 6,
    )
