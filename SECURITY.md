# Security policy

## Reporting a vulnerability

Please don't open a public issue. Use GitHub's **Report a vulnerability** button (Security tab, then Advisories). We aim to reply within 3 business days.

## Built-in protections

- File tools are sandboxed to `ARMY_WORKDIR`; `write_file` only writes to `outputs/`.
- SQLite is opened read-only and only `SELECT` / `WITH` queries are accepted.
- The calculator parses expressions into a syntax tree and only allows arithmetic. There is no `eval`.
- No tool runs shell commands. Git tools use fixed argument lists.
- MCP servers only run when you name them explicitly, and agents are told to describe write actions before taking them.
- Memory is stored as plain JSON in `~/.army/memory/`; agents are told never to store secrets.
- Tool output is size-capped before it reaches the model.
- API keys are read from environment variables only and are never logged.
- The `main` branch is protected against force pushes and deletion.

## Prompt injection

Web pages and documents that tools read can contain instructions aimed at the model. Templates treat tool output as data, but no LLM agent is immune. Don't give agents tools that can take irreversible actions unless a human approves each one.
