"""Chess Arena

Two AI players, optionally different models, play a full game of chess refereed by a built-in rules
engine verified with perft: castling, en passant, promotion, check, checkmate, stalemate, the
50-move rule, threefold repetition and insufficient material are all enforced. Each turn a player
sees the board, the FEN and the list of legal moves; illegal answers get three retries before a
random legal move is played and the illegal attempt is logged. You get the move list and the final
result in PGN-like form.
"""
import random

from army import Agent, Result, get_llm, parse_action
from army.agent import Step
from army.chess import Position

META = {
    "category": "games",
    "description": "Two models play real chess, refereed by a perft-verified rules engine; full move log and result.",
    "example": "Play a game",
}
EVALS = [{"input": "Play a game", "must_contain": ["Result:"], "max_seconds": 1800}]

RULES = """You are a strong chess player. Think about checks, captures and threats for both sides before choosing.
Reply with JSON {"final": "<move in UCI notation, e.g. e2e4 or e7e8q>"} choosing ONLY from the legal moves listed."""


class Arena:
    name = "chess-arena"
    tools: dict = {}

    def __init__(self, white: Agent, black: Agent, max_plies: int = 200, seed=None, fen: str | None = None):
        self.players = {"w": white, "b": black}
        self.max_plies, self.rng, self.fen = max_plies, random.Random(seed), fen

    def choose(self, pos: Position, log: list[str]):
        legal = pos.legal_moves()
        legal_uci = " ".join(sorted(Position.uci(m) for m in legal))
        recent = " ".join(log[-12:]) or "(game start)"
        side = "White (uppercase)" if pos.turn == "w" else "Black (lowercase)"
        prompt = (f"You play {side}.\nBoard:\n{pos.ascii()}\nFEN: {pos.fen()}\nRecent moves: {recent}\n"
                  f"{'You are in CHECK. ' if pos.in_check() else ''}Legal moves: {legal_uci}")
        player = self.players[pos.turn]
        for attempt in range(3):
            reply = player.llm.chat(player.instructions, [{"role": "user", "content": prompt}])
            action = parse_action(reply) or {}
            move = pos.parse(str(action.get("final", "")))
            if move:
                return move, attempt
            prompt += f"\nThat was not a legal move. Choose exactly one of: {legal_uci}"
        return self.rng.choice(legal), 3

    def run(self, task: str = "", verbose: bool = False) -> Result:
        pos = Position.from_fen(self.fen) if self.fen else Position.from_fen()
        log, steps, numbered = [], [], []
        while (outcome := pos.result()) is None and len(log) < self.max_plies:
            move, retries = self.choose(pos, log)
            uci = Position.uci(move)
            if pos.turn == "w":
                numbered.append(f"{pos.full}. {uci}")
            else:
                numbered[-1:] = [(numbered[-1] if numbered else f"{pos.full}...") + f" {uci}"]
            note = uci + (f" (random after {retries} illegal tries)" if retries == 3 else "")
            steps.append(Step(self.players[pos.turn].name, "tool", note, "move", {"uci": uci}))
            if verbose:
                print(pos.turn, note)
            log.append(uci)
            pos = pos.play(move)
        outcome = outcome or f"move limit ({self.max_plies} plies) - draw"
        forced = sum(1 for s in steps if "random" in s.content)
        summary = (f"White: {self.players['w'].name}\nBlack: {self.players['b'].name}\n\n" + " ".join(numbered) +
                   f"\n\nFinal position:\n{pos.ascii()}\nFEN: {pos.fen()}\n\nResult: {outcome}\n"
                   f"Plies: {len(log)}, forced random moves: {forced}")
        return Result(summary, steps)


def build(llm=None, white_model: str = "", black_model: str = "", max_plies: str = "200", seed: str = "", fen: str = ""):
    white = Agent(f"White ({white_model or 'default'})", RULES, llm=get_llm(white_model) if white_model else llm)
    black = Agent(f"Black ({black_model or 'default'})", RULES, llm=get_llm(black_model) if black_model else llm)
    return Arena(white, black, int(max_plies), int(seed) if seed else None, fen or None)
