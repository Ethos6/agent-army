# Docs Q&A Agent (RAG)

Point it at a folder of Markdown, text or code. It builds a BM25 index in memory, which takes milliseconds and needs no vector database and no embedding API. Then it answers questions with a citation on every claim, like `[pricing.md:3-12]`.

```bash
army run docs-qa "How do I rotate an API key?" --opt docs=./my-docs -v
```

Two eval cases ship with it: one that must find the right answer *with* its citation, and one that must refuse because the answer is not in the docs. Refusing correctly matters as much as answering correctly.

**Want embeddings?** Write a function with the same signature as `army.rag.search_tool` that calls your vector store. Nothing else changes.
