"""Chat with Your Email

Ask questions of an email export (.mbox, which most mail apps and account-export tools produce):
"what do I owe and to whom?", "what's due this week?", "summarize the launch thread". It searches
locally (nothing is uploaded except the passages sent to your chosen model) and cites sender, date
and subject.
"""
from army import Agent
from army.tools import search_mailbox

META = {
    "category": "chat",
    "description": "Ask an .mbox email export about deadlines, invoices and threads, citing sender, date and subject.",
    "example": "What deadlines and payments are pending in examples/mail/sample.mbox?",
}
EVALS = [{"input": "Is any invoice overdue in examples/mail/sample.mbox?", "must_contain": ["INV-2291", "1,240"], "max_seconds": 120}]


def build(llm=None, mailbox: str = "examples/mail/sample.mbox"):
    return Agent(
        name="chat-with-email",
        instructions=f"""Answer questions about the user's email (default mailbox: {mailbox}). Use `search_mailbox` with short keyword
queries (try several: e.g. "invoice", "due", "deadline", a person's name). Cite each fact as (From, Date, Subject).
For "what needs action" questions, output a table: | Item | Due | From | Action |.""",
        tools=[search_mailbox],
        llm=llm,
        max_steps=8,
    )
