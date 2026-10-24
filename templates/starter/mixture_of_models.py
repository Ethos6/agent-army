"""Mixture of Models

Sends the same question to several different models independently, then a judge model compares
their answers, keeps what they agree on, resolves disagreements, and writes one answer that is
better than any single response. Choose the models with --opt models=a,b,c.
"""
from army import Agent, Panel, get_llm

META = {
    "category": "starter",
    "description": "Several models answer independently; a judge merges the best parts and flags disagreements.",
    "example": "What are the trade-offs between SQL and NoSQL databases for a startup?",
    "needs": "API keys for each model you list (or local Ollama models).",
}
EVALS = [{"input": "Explain why the sky is blue in three sentences", "must_contain": ["Rayleigh"], "max_seconds": 240}]


def build(llm=None, models: str = "", judge: str = ""):
    specs = [m.strip() for m in models.split(",") if m.strip()]
    members = [
        Agent(f"model-{i}", "Answer the question as well as you can. Be specific and concise.",
              llm=get_llm(spec) if spec else llm)
        for i, spec in enumerate(specs or ["", "", ""], 1)
    ]
    referee = Agent(
        "judge",
        """You are a rigorous judge. You receive several independent answers to the same task.
1. Identify points all answers agree on (high confidence).
2. Resolve disagreements: say which answer is right and why; if unsure, say so.
3. Write the single best final answer.
Format: ## Final answer, then ## Where the models disagreed (bullets, or "none").""",
        llm=get_llm(judge) if judge else llm,
    )
    return Panel(members, referee, name="mixture-of-models")
