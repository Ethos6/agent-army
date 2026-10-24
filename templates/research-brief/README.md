# Research Brief Agent

Give it a question and a few URLs. It fetches each page, pulls out the claims that carry numbers, dates and names, checks any arithmetic with an exact calculator, and writes a brief with four fixed sections: **Bottom line**, **Key findings** (each one cited), **What is uncertain**, and **Sources**.

```bash
army run research-brief "Compare https://a.com/report and https://b.com/report on market size" -v
```

**Tools:** `fetch_url`, `calculate`. **Option:** `--opt max_sources=6`.

Why it is trustworthy: findings must name their source, and the brief has a section just for what is uncertain, so the reader can tell where the evidence stops and the agent's inference begins.
