# Security policy

## Reporting a vulnerability

Please don't open a public issue. Use GitHub's **Report a vulnerability** button (Security tab, then Advisories), or email **marketing@atomesus.com** with the subject `SECURITY: agent-forge`. We aim to reply within 3 business days.

## Built-in protections

- File tools are sandboxed to `FORGE_WORKDIR`.
- The calculator parses expressions into a syntax tree and only allows arithmetic. There is no `eval`.
- No tool runs shell commands. `git_diff` uses a fixed argument list.
- Tool output is size-capped before it reaches the model.
- API keys are read from environment variables only and are never logged.
- The `main` branch is protected against force pushes and deletion.

## Prompt injection

Web pages and documents that tools read can contain instructions aimed at the model. Templates treat tool output as data, but no LLM agent is immune. Don't give agents tools that can take irreversible actions unless a human approves each one.
