"""Voice Notes to Brief

Record yourself thinking out loud about a problem, then hand over the audio file. It transcribes the
ramble and turns it into a scannable brief: what you decided, open questions, action items and the
places where you changed your mind. Anything the model inferred, rather than heard, is clearly
marked.
"""
from army import Agent
from army.voice import transcribe_audio

META = {
    "category": "voice",
    "description": "Turns a rambling voice memo into decisions, open questions and actions; inferences clearly marked.",
    "example": "Transcript: we should ship the beta Friday, actually Monday, and ask Priya to review pricing first",
    "needs": "OPENAI_API_KEY (or any OpenAI-compatible speech-to-text server via OPENAI_BASE_URL).",
}
EVALS = [{"input": "Transcript: ok so I think we launch in March, no wait, April is safer because of the audit. Need to ask Sam about budget. Also book the venue by Friday.", "must_contain": ["Decisions", "Actions", "April"], "max_seconds": 120}]


def build(llm=None):
    return Agent(
        name="voice-notes-brief",
        instructions="""Transcribe the audio with `transcribe_audio` (if the user pasted a transcript instead, use that).
Write the brief from what was actually said:
## In one line
## Decisions  ## Open questions  ## Actions (| Action | When | Notes |)
## Changed my mind  (places the speaker reversed a position, quoting both sides)
## My guesses  (anything you inferred rather than heard, kept separate)""",
        tools=[transcribe_audio],
        llm=llm,
    )
