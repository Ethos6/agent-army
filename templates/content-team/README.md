# Content Team

Three specialists, run in order:

1. **Strategist**: reads your source material (it fetches any URL you include) and writes a creative brief with audience, proof points, hook options and tone.
2. **Writer**: drafts the piece to the brief.
3. **Editor**: tightens it, checks every claim against the brief, and returns `## Final` plus `## Edit notes`.

```bash
army run content-team "Launch post for https://example.com/changelog" --opt channel="X thread" -v
```

Each agent sees the original request plus the previous agent's output, so you can see exactly where the quality comes from.
