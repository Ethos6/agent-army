"""Voice Support Agent

A customer-support voice agent grounded in your documentation. It transcribes a caller's recorded
question, answers it from your knowledge base with citations (never from general knowledge), and
speaks the answer back as an MP3. If the docs don't cover it, it says it will escalate to a human.
"""
from army import Agent
from army.rag import index_folder, search_tool
from army.voice import text_to_speech, transcribe_audio

META = {
    "category": "voice",
    "description": "Transcribes a caller's question, answers from your docs with citations, and replies as audio.",
    "example": "Caller asks (transcript): can I get a refund on the Pro plan?",
    "needs": "OPENAI_API_KEY (or OpenAI-compatible speech servers).",
}
EVALS = [{"input": "Caller asks (transcript): how do I rotate my API key?", "must_contain": ["security.md", ".mp3"], "max_seconds": 240}]


def build(llm=None, docs: str = "examples/knowledge-base"):
    return Agent(
        name="voice-support",
        instructions="""You are a friendly phone-support agent.
1. If given an audio file, `transcribe_audio` it; if given a transcript, use it.
2. Answer ONLY from `search_docs` results. If they don't cover it, the answer is: "I'll connect you with a specialist."
3. Write the spoken answer: under 80 words, plain sentences, no markdown. Save it with `text_to_speech` (reply.mp3).
Final answer: Transcript, Spoken answer, Sources [file:lines], Audio file path.""",
        tools=[transcribe_audio, search_tool(index_folder(docs)), text_to_speech],
        llm=llm,
    )
