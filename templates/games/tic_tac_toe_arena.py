"""Tic-Tac-Toe Arena

Two AI players, optionally different models, play tic-tac-toe against each other. The game engine
validates every move: illegal moves are rejected and the player gets up to three retries before a
random legal move is played for them. You get the full move log, the board after each move and the
result, which makes it a quick benchmark of model reasoning.
"""
import random

from army import Agent, Result, get_llm, parse_action
from army.agent import Step

META = {
    "category": "games",
    "description": "Two models play tic-tac-toe with engine-validated moves; full move log and result.",
    "example": "Play a game",
}
EVALS = [{"input": "Play a game", "must_contain": ["Result"], "max_seconds": 300}]

LINES = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6)]


def show(b):
    return "\n".join(" ".join(b[r * 3 + c] or str(r * 3 + c) for c in range(3)) for r in range(3))


def winner(b):
    for a, c, d in LINES:
        if b[a] and b[a] == b[c] == b[d]:
            return b[a]
    return "draw" if all(b) else None


class Arena:
    name = "tic-tac-toe-arena"
    tools: dict = {}

    def __init__(self, x: Agent, o: Agent, seed: int | None = None):
        self.players = {"X": x, "O": o}
        self.rng = random.Random(seed)

    def move(self, mark, board, log):
        legal = [i for i, v in enumerate(board) if not v]
        prompt = f"You are {mark}. Board (numbers are free squares):\n{show(board)}\nLegal moves: {legal}\n" \
                 'Reply with JSON {"final": <square number>}.'
        for attempt in range(3):
            reply = self.players[mark].llm.chat(self.players[mark].instructions, [{"role": "user", "content": prompt}])
            action = parse_action(reply) or {}
            try:
                sq = int(str(action.get("final", reply)).strip().split()[0])
            except (ValueError, IndexError):
                sq = -1
            if sq in legal:
                return sq, attempt
            prompt += f"\n{sq} is illegal. Choose from {legal}."
        return self.rng.choice(legal), 3

    def run(self, task: str = "", verbose: bool = False) -> Result:
        board, log, steps, mark = [""] * 9, [], [], "X"
        while not winner(board):
            sq, retries = self.move(mark, board, log)
            board[sq] = mark
            note = f"{mark} -> {sq}" + (f" (after {retries} illegal tries)" if retries else "")
            log.append(note + "\n" + show(board))
            steps.append(Step(mark, "tool", note, "move", {"square": sq}))
            if verbose:
                print(log[-1], "\n")
            mark = "O" if mark == "X" else "X"
        w = winner(board)
        result = "Result: draw" if w == "draw" else f"Result: {w} wins ({self.players[w].name})"
        return Result("\n\n".join(log) + "\n\n" + result, steps)


def build(llm=None, x_model: str = "", o_model: str = "", seed: str = ""):
    rules = "You play tic-tac-toe perfectly: win if you can, block the opponent's win, take the centre, then corners."
    x = Agent(f"X ({x_model or 'default'})", rules, llm=get_llm(x_model) if x_model else llm)
    o = Agent(f"O ({o_model or 'default'})", rules, llm=get_llm(o_model) if o_model else llm)
    return Arena(x, o, int(seed) if seed else None)
