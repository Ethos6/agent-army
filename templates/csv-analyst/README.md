# CSV Analyst Agent

Ask a question about a spreadsheet in plain English. The agent first inspects the real columns, then gets every number from a tool: grouped sums, means, min/max and an exact calculator. It never does mental math, so the numbers it reports are the numbers in your file.

```bash
army run csv-analyst "What is the cost per signup by channel in examples/data/campaigns.csv?" -v
```

**Tools:** `list_files`, `describe_csv`, `aggregate_csv`, `calculate`. File access is sandboxed to `ARMY_WORKDIR` (the current folder by default).
