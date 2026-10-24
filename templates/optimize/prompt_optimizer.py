"""Prompt Optimizer

Improves a prompt by testing it, not guessing. It writes a few test inputs, runs your original
prompt and two rewritten candidates on the configured model, scores each output against the stated
goal, and returns the winning prompt with the evidence and a shorter variant that saves tokens.
"""
from army import Agent, tool

META = {
    "category": "optimize",
    "description": "Rewrites a prompt, tests original vs candidates on real inputs, and returns the measured winner.",
    "example": "Optimize: 'Summarize this customer email.' Goal: 2-line summary with sentiment and the action needed",
}
EVALS = [{"input": "Optimize: 'Write a product description.' Goal: 50-word benefit-led copy", "must_contain": ["Winner", "Scores"], "max_seconds": 400}]


def build(llm=None):
    agent = Agent("prompt-optimizer", "", llm=llm, max_steps=16)

    @tool
    def run_prompt(prompt: str, test_input: str) -> str:
        """Run a candidate prompt (as the system prompt) on one test input with the configured model; returns the output."""
        return agent.llm.chat(prompt, [{"role": "user", "content": test_input}])[:3000]

    agent.instructions = """You are a prompt engineer who measures.
1. From the goal, write 3 varied, realistic test inputs.
2. Write 2 improved candidates (clear role, task, constraints, output format, one example if useful).
3. Run the original and both candidates on every test input with `run_prompt`.
4. Score each output 1-5 against the goal with a one-line reason.
Output: ## Scores (| Prompt | Test 1 | Test 2 | Test 3 | Total |), ## Winner (full prompt text), ## Why it wins,
## Token-saving variant (shorter version of the winner)."""
    agent.tools = {run_prompt.name: run_prompt}
    return agent
