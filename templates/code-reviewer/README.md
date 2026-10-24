# Code Review Agent

Run it inside any git repo. It reads the diff, opens surrounding files when it needs context, and reports only the problems that matter. Each finding comes with a severity, the exact input that triggers it, and the smallest fix.

```bash
cd your-project
ARMY_WORKDIR=. army run code-reviewer "Review my uncommitted changes" --opt ref=main -v
```

It ends with `Verdict: APPROVE` or `Verdict: REQUEST CHANGES`, so you can gate CI on it with `grep`.
