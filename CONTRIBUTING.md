# Contributing

Thanks for helping make Agent Army better.

## Add a template

1. `army new <name>` (lowercase, dashes).
2. Write `agent.py` with a `build(llm=None, **options)` function that returns an `Agent` or a `Pipeline`.
3. Fill in `agent.toml`: `title`, a `category` (research, data, rag, engineering, marketing or business), a one-line `description`, an `example` task, and at least one `[[evals]]` case.
4. Explain in the template's `README.md` what it does, how to run it, and why it can be trusted.
5. Run the checks:

```bash
python -m unittest discover -s tests -v
army validate
army eval <name>          # against at least one real model
army catalog              # refresh the README table
```

## Standards for a template

- **It solves a real job**, not a demo of an API.
- **It works on any model.** Don't use provider-specific features in `agent.py`.
- **It is grounded.** Numbers come from tools, claims cite sources, and it says when it doesn't know.
- **It is safe.** New tools must sandbox file access, avoid `shell=True` and `eval`, and cap output size.
- **It is small.** If `agent.py` grows past about 80 lines, move reusable pieces into `army/tools.py`.

## Pull requests

Keep each PR focused. CI must pass. The `main` branch is protected: force pushes and branch deletion are blocked.
