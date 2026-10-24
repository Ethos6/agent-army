"""Podcast Generator

From an article URL or topic to a finished audio episode. A writer researches and writes a tight
narrated script, then the producer converts it to speech and saves an MP3 in outputs/. Voice and
models are configurable with ARMY_TTS_MODEL and ARMY_TTS_VOICE.
"""
from army import Agent, Pipeline
from army.tools import fetch_url
from army.voice import text_to_speech
from army.web import web_search

META = {
    "category": "voice",
    "description": "Article or topic in, narrated MP3 episode out: researched script plus text-to-speech.",
    "example": "Make a 3-minute episode about how vaccines train the immune system",
    "needs": "OPENAI_API_KEY (or an OpenAI-compatible text-to-speech server).",
}
EVALS = [{"input": "A 1-minute episode about why leaves change colour", "must_contain": ["saved", ".mp3"], "max_seconds": 300}]


def build(llm=None, minutes: str = "3"):
    writer = Agent("script-writer", f"""Write a {minutes}-minute narrated podcast script (~{int(minutes) * 150} words), single narrator,
conversational, with a hook, three clear segments and a recap. Research with `web_search` / `fetch_url` and only use facts
you found. Output only the words to be spoken.""", tools=[web_search, fetch_url], llm=llm)
    producer = Agent("producer", """Take the script from the previous step and call `text_to_speech` with the full script text and a
short descriptive filename ending in .mp3. Final answer: the saved file path and the episode title.""",
                     tools=[text_to_speech], llm=llm)
    return Pipeline(writer, producer, name="podcast-generator")
