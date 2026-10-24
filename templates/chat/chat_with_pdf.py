"""Chat with PDF

Ask questions about any PDF: contracts, papers, manuals, reports. The PDF is extracted page by page
and indexed on first use, so answers cite page numbers like [p. 4]. Long documents are searched
instead of stuffed into the prompt, which keeps answers grounded and cheap.
"""
from army import Agent, tool
from army.rag import BM25Index, Chunk
from army.tools import read_pdf

META = {
    "category": "chat",
    "description": "Questions about any PDF answered with page citations; long files are searched, not stuffed.",
    "example": "What budget does examples/docs/field-report.pdf request, and for what?",
    "requires": ["pypdf"],
}
EVALS = [{"input": "By how much did delivery times fall in examples/docs/field-report.pdf?", "must_contain": ["18", "p. 1"], "max_seconds": 180}]


def build(llm=None):
    cache: dict[str, BM25Index] = {}

    @tool
    def search_pdf(path: str, query: str, k: int = 4) -> str:
        """Search a PDF for passages relevant to the query. Results are tagged with page numbers."""
        if path not in cache:
            text = read_pdf(path=path, max_pages=500)
            chunks = []
            for block in text.split("[page ")[1:]:
                num, _, body = block.partition("]")
                paras = [p for p in body.split("\n\n") if p.strip()] or [body]
                for j in range(0, len(paras), 3):
                    chunks.append(Chunk(f"p. {num}", int(num), int(num), "\n\n".join(paras[j:j + 3])))
            cache[path] = BM25Index(chunks)
        hits = cache[path].search(query, int(k))
        return "\n\n".join(f"[{c.source}]\n{c.text[:1500]}" for _, c in hits) or "no matching passages"

    return Agent(
        name="chat-with-pdf",
        instructions="""Answer questions about the user's PDF using `search_pdf` (try 2+ phrasings). For a summary, search for
the abstract/introduction/conclusion. Cite pages like [p. 4] after every claim. If the PDF doesn't say, say so.""",
        tools=[search_pdf],
        llm=llm,
        max_steps=8,
    )
