"""Connect Four Arena

Two AI players drop discs into a 7x6 grid; the engine validates moves, detects four-in-a-row in any
direction and logs every turn. Connect Four needs more lookahead than tic-tac-toe, so it separates
models that plan from models that react. Pit different models with --opt red_model=... --opt
yellow_model=....
"""
import random

from army import Agent, Result, get_llm, parse_action
from army.agent import Step

META = {
    "category": "games",
    "description": "Two models play Connect Four with engine-validated moves and win detection; full game log.",
    "example": "Play a game",
}
EVALS = [{"input": "Play a game", "must_contain": ["Result"], "max_seconds": 600}]
COLS, ROWS = 7, 6


def render(g):
    return "\n".join(" ".join(g[r][c] or "." for c in range(COLS)) for r in range(ROWS)) + "\n" + " ".join(map(str, range(COLS)))


def drop(g, col, disc):
    for r in range(ROWS - 1, -1, -1):
        if not g[r][col]:
            g[r][col] = disc
            return r
    return -1


def four(g, disc):
    for r in range(ROWS):
        for c in range(COLS):
            for dr, dc in ((0, 1), (1, 0), (1, 1), (1, -1)):
                if all(0 <= r + i * dr < ROWS and 0 <= c + i * dc < COLS and g[r + i * dr][c + i * dc] == disc for i in range(4)):
                    return True
    return False


class Arena:
    name = "connect-four-arena"
    tools: dict = {}

    def __init__(self, red: Agent, yellow: Agent, seed=None):
        self.players = {"R": red, "Y": yellow}
        self.rng = random.Random(seed)

    def choose(self, disc, g):
        legal = [c for c in range(COLS) if not g[0][c]]
        prompt = f"You are {disc}. Grid (top row first, '.' empty):\n{render(g)}\nLegal columns: {legal}\n" \
                 'Think about threats, then reply with JSON {"final": <column>}.'
        for attempt in range(3):
            reply = self.players[disc].llm.chat(self.players[disc].instructions, [{"role": "user", "content": prompt}])
            a = parse_action(reply) or {}
            try:
                col = int(str(a.get("final", "")).strip())
            except ValueError:
                col = -1
            if col in legal:
                return col, attempt
            prompt += f"\nColumn {col} is not legal. Choose from {legal}."
        return self.rng.choice(legal), 3

    def run(self, task="", verbose=False) -> Result:
        g = [[""] * COLS for _ in range(ROWS)]
        log, steps, disc = [], [], "R"
        for _ in range(COLS * ROWS):
            col, retries = self.choose(disc, g)
            drop(g, col, disc)
            note = f"{disc} -> column {col}" + (f" (after {retries} illegal tries)" if retries else "")
            log.append(note)
            steps.append(Step(disc, "tool", note, "drop", {"column": col}))
            if verbose:
                print(note)
            if four(g, disc):
                return Result("\n".join(log) + f"\n\n{render(g)}\n\nResult: {disc} wins ({self.players[disc].name})", steps)
            disc = "Y" if disc == "R" else "R"
        return Result("\n".join(log) + f"\n\n{render(g)}\n\nResult: draw", steps)


def build(llm=None, red_model: str = "", yellow_model: str = "", seed: str = ""):
    rules = "You are a strong Connect Four player: win immediately if possible, block the opponent's immediate win, prefer centre columns, avoid moves that let the opponent win next turn."
    red = Agent(f"Red ({red_model or 'default'})", rules, llm=get_llm(red_model) if red_model else llm)
    yellow = Agent(f"Yellow ({yellow_model or 'default'})", rules, llm=get_llm(yellow_model) if yellow_model else llm)
    return Arena(red, yellow, int(seed) if seed else None)
