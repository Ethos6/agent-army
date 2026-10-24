"""Twenty Questions

One AI secretly picks a thing; another tries to identify it with at most twenty yes/no questions. The
host must answer truthfully and consistently and the game log shows every question, so you can see
how well a model narrows down a search space. Choose the secret yourself with --opt secret=... to
test the guesser alone.
"""
from army import Agent, Result, get_llm, parse_action
from army.agent import Step

META = {
    "category": "games",
    "description": "A host model hides a secret; a guesser model narrows it down with 20 yes/no questions.",
    "example": "Play with a secret animal",
}
EVALS = [{"input": "Play with the secret 'giraffe'", "must_contain": ["Result"], "max_seconds": 600}]


class Game:
    name = "twenty-questions"
    tools: dict = {}

    def __init__(self, host: Agent, guesser: Agent, secret: str = "", limit: int = 20):
        self.host, self.guesser, self.secret, self.limit = host, guesser, secret, limit

    def run(self, task: str = "", verbose=False) -> Result:
        secret = self.secret
        if not secret and "'" in task:
            secret = task.split("'")[1]
        if not secret:
            reply = self.host.llm.chat(self.host.instructions, [{"role": "user", "content": f"{task}\nPick a secret. Reply with JSON {{\"final\": \"<secret>\"}}."}])
            secret = str((parse_action(reply) or {}).get("final", reply)).strip()
        history, steps = [], []
        for n in range(1, self.limit + 1):
            q_prompt = "Questions so far:\n" + ("\n".join(history) or "(none)") + \
                f'\nAsk question {n} of {self.limit}, or guess with "Is it <thing>?". Reply with JSON {{"final": "<question>"}}.'
            raw = self.guesser.llm.chat(self.guesser.instructions, [{"role": "user", "content": q_prompt}])
            question = str((parse_action(raw) or {}).get("final", raw)).strip()
            a_prompt = f'The secret is "{secret}". Answer the question truthfully with only Yes, No, or Correct (if they named it).\nQuestion: {question}\nReply with JSON {{"final": "Yes|No|Correct"}}.'
            raw_a = self.host.llm.chat(self.host.instructions, [{"role": "user", "content": a_prompt}])
            answer = str((parse_action(raw_a) or {}).get("final", raw_a)).strip()
            history.append(f"{n}. {question} -> {answer}")
            steps.append(Step("guesser", "tool", answer, "ask", {"question": question}))
            if verbose:
                print(history[-1])
            if answer.lower().startswith("correct"):
                return Result("\n".join(history) + f"\n\nResult: guessed '{secret}' in {n} questions", steps)
        return Result("\n".join(history) + f"\n\nResult: not guessed; the secret was '{secret}'", steps)


def build(llm=None, host_model: str = "", guesser_model: str = "", secret: str = ""):
    host = Agent("host", "You host Twenty Questions. You are truthful and consistent.", llm=get_llm(host_model) if host_model else llm)
    guesser = Agent("guesser", "You play Twenty Questions. Ask questions that split the remaining possibilities in half.",
                    llm=get_llm(guesser_model) if guesser_model else llm)
    return Game(host, guesser, secret)
