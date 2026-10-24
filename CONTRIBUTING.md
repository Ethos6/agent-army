# Contributing

Thanks for helping grow the army.

## Add an agent

1. `army new <category> <name>`. Categories: starter, research, business, marketing, engineering, teams, rag, chat, memory, mcp, voice, games, always-on, ui, optimize, finetune.
2. Edit `templates/<category>/<name>.py`:
   - a module docstring: a title line, a blank line, then 2-4 sentences on what it delivers and why it can be trusted
   - `META` with `category`, `description` (one line), `example` (a runnable task), plus optional `requires` (pip packages) and `needs` (keys or runtimes)
   - `EVALS` with at least one case (`input`, `must_contain`, `max_seconds`)
   - `build(llm=None, **options)` returning an `Agent`, `Pipeline`, `Panel`, or any object with `.run(task)`
3. Run the checks:

```bash
python -m unittest discover -s tests -v
army validate
army eval <name> --model <a real model>
army catalog && army docs
```

## Standards

- **It solves a real job**, not a demo of an API.
- **It works on any model.** Don't use provider-specific features in an agent file.
- **It is grounded.** Numbers come from tools, claims cite sources, and it says when it doesn't know.
- **It is safe.** New tools must sandbox file access, avoid `shell=True` and `eval`, cap output size, and never take irreversible actions without the user asking.
- **It is original.** Write your own prompts and code. Don't paste code from other projects unless their license allows it and you keep their notices.
- **It is small.** Shared logic belongs in `army/`; agent files stay short.

## Pull requests

Keep each PR focused. CI must pass. The `main` branch is protected: force pushes and branch deletion are blocked.
