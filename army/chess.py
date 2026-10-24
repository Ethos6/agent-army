"""A small, complete chess rules engine (pure Python, no dependencies).

Covers every rule needed to referee a game between AI players: legal move generation with checks
and pins, castling, en passant, promotion, checkmate, stalemate, the 50-move rule, threefold
repetition and insufficient material. Moves use UCI notation (e2e4, e7e8q). Verified with perft.
"""
from __future__ import annotations

from dataclasses import dataclass, field

FILES = "abcdefgh"
START = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
KNIGHT = [(-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1)]
KING = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
ROOK_DIRS = [(-1, 0), (1, 0), (0, -1), (0, 1)]
BISHOP_DIRS = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
# square index -> castling rights lost when a piece moves from or to it
RIGHTS_LOST = {60: "KQ", 63: "K", 56: "Q", 4: "kq", 7: "k", 0: "q"}

Move = tuple  # (from_index, to_index, promotion_letter_or_empty)


def sq(name: str) -> int:
    """'e4' -> board index (a8 = 0, h1 = 63)."""
    return (8 - int(name[1])) * 8 + FILES.index(name[0])


def name(i: int) -> str:
    return FILES[i % 8] + str(8 - i // 8)


def _on(r: int, c: int) -> bool:
    return 0 <= r < 8 and 0 <= c < 8


@dataclass
class Position:
    board: list
    turn: str = "w"
    castling: str = "KQkq"
    ep: int | None = None
    half: int = 0
    full: int = 1
    history: dict = field(default_factory=dict)

    # ---------------------------------------------------------------- FEN
    @classmethod
    def from_fen(cls, fen: str = START) -> "Position":
        parts = fen.split()
        board = []
        for ch in parts[0]:
            if ch.isdigit():
                board += ["."] * int(ch)
            elif ch != "/":
                board.append(ch)
        if len(board) != 64:
            raise ValueError("bad FEN board")
        pos = cls(board, parts[1], "" if parts[2] == "-" else parts[2],
                  None if parts[3] == "-" else sq(parts[3]), int(parts[4]), int(parts[5]))
        pos.history = {pos.key(): 1}
        return pos

    def fen(self) -> str:
        rows = []
        for r in range(8):
            row, empty = "", 0
            for p in self.board[r * 8:(r + 1) * 8]:
                if p == ".":
                    empty += 1
                else:
                    row += (str(empty) if empty else "") + p
                    empty = 0
            rows.append(row + (str(empty) if empty else ""))
        ep = name(self.ep) if self.ep is not None else "-"
        return f"{'/'.join(rows)} {self.turn} {self.castling or '-'} {ep} {self.half} {self.full}"

    def key(self) -> str:
        return "".join(self.board) + self.turn + self.castling + str(self.ep)

    def ascii(self) -> str:
        lines = [f"{8 - r} " + " ".join(self.board[r * 8:(r + 1) * 8]) for r in range(8)]
        return "\n".join(lines) + "\n  a b c d e f g h"

    # ---------------------------------------------------------------- attacks
    def attacked(self, i: int, by_white: bool) -> bool:
        b, (r, c) = self.board, divmod(i, 8)
        pawn, pr = ("P", r + 1) if by_white else ("p", r - 1)
        for dc in (-1, 1):
            if _on(pr, c + dc) and b[pr * 8 + c + dc] == pawn:
                return True
        n, k = ("N", "K") if by_white else ("n", "k")
        for dr, dc in KNIGHT:
            if _on(r + dr, c + dc) and b[(r + dr) * 8 + c + dc] == n:
                return True
        for dr, dc in KING:
            if _on(r + dr, c + dc) and b[(r + dr) * 8 + c + dc] == k:
                return True
        for dirs, pieces in ((ROOK_DIRS, "RQ"), (BISHOP_DIRS, "BQ")):
            pieces = pieces if by_white else pieces.lower()
            for dr, dc in dirs:
                rr, cc = r + dr, c + dc
                while _on(rr, cc):
                    p = b[rr * 8 + cc]
                    if p != ".":
                        if p in pieces:
                            return True
                        break
                    rr, cc = rr + dr, cc + dc
        return False

    def king(self, white: bool) -> int:
        return self.board.index("K" if white else "k")

    def in_check(self) -> bool:
        white = self.turn == "w"
        return self.attacked(self.king(white), not white)

    # ---------------------------------------------------------------- moves
    def pseudo_moves(self):
        b, white = self.board, self.turn == "w"
        own = str.isupper if white else str.islower
        enemy = str.islower if white else str.isupper
        for i, p in enumerate(b):
            if p == "." or not own(p):
                continue
            r, c = divmod(i, 8)
            t = p.upper()
            if t == "P":
                d, start, last = (-1, 6, 0) if white else (1, 1, 7)
                promos = "qrbn"
                if _on(r + d, c) and b[(r + d) * 8 + c] == ".":
                    to = (r + d) * 8 + c
                    for pr in (promos if r + d == last else [""]):
                        yield (i, to, pr)
                    if r == start and b[(r + 2 * d) * 8 + c] == ".":
                        yield (i, (r + 2 * d) * 8 + c, "")
                for dc in (-1, 1):
                    if _on(r + d, c + dc):
                        to = (r + d) * 8 + c + dc
                        if (b[to] != "." and enemy(b[to])) or to == self.ep:
                            for pr in (promos if r + d == last else [""]):
                                yield (i, to, pr)
            elif t in "NK":
                for dr, dc in (KNIGHT if t == "N" else KING):
                    if _on(r + dr, c + dc):
                        to = (r + dr) * 8 + c + dc
                        if b[to] == "." or enemy(b[to]):
                            yield (i, to, "")
                if t == "K":
                    yield from self._castles(white)
            else:
                dirs = {"B": BISHOP_DIRS, "R": ROOK_DIRS, "Q": BISHOP_DIRS + ROOK_DIRS}[t]
                for dr, dc in dirs:
                    rr, cc = r + dr, c + dc
                    while _on(rr, cc):
                        to = rr * 8 + cc
                        if b[to] == ".":
                            yield (i, to, "")
                        else:
                            if enemy(b[to]):
                                yield (i, to, "")
                            break
                        rr, cc = rr + dr, cc + dc

    def _castles(self, white: bool):
        b, them = self.board, not white
        if white and b[60] == "K":
            if "K" in self.castling and b[63] == "R" and b[61] == b[62] == "." and not any(self.attacked(s, them) for s in (60, 61, 62)):
                yield (60, 62, "")
            if "Q" in self.castling and b[56] == "R" and b[57] == b[58] == b[59] == "." and not any(self.attacked(s, them) for s in (60, 59, 58)):
                yield (60, 58, "")
        if not white and b[4] == "k":
            if "k" in self.castling and b[7] == "r" and b[5] == b[6] == "." and not any(self.attacked(s, them) for s in (4, 5, 6)):
                yield (4, 6, "")
            if "q" in self.castling and b[0] == "r" and b[1] == b[2] == b[3] == "." and not any(self.attacked(s, them) for s in (4, 3, 2)):
                yield (4, 2, "")

    def play(self, m: Move) -> "Position":
        """Return the position after move m (does not check legality; use legal_moves)."""
        f, t, pr = m
        b, white = self.board[:], self.turn == "w"
        p, captured = b[f], b[t]
        b[t], b[f] = p, "."
        if p in "Pp":
            if t == self.ep:
                b[t + 8 if white else t - 8] = "."
                captured = "p"
            if pr:
                b[t] = pr.upper() if white else pr.lower()
        if p in "Kk" and abs(t - f) == 2:
            rook_from, rook_to = {62: (63, 61), 58: (56, 59), 6: (7, 5), 2: (0, 3)}[t]
            b[rook_to], b[rook_from] = b[rook_from], "."
        castling = "".join(ch for ch in self.castling if ch not in RIGHTS_LOST.get(f, "") + RIGHTS_LOST.get(t, ""))
        ep = (f + t) // 2 if p in "Pp" and abs(t - f) == 16 else None
        nxt = Position(b, "b" if white else "w", castling, ep,
                       0 if p in "Pp" or captured != "." else self.half + 1,
                       self.full + (0 if white else 1))
        nxt.history = dict(self.history)
        nxt.history[nxt.key()] = nxt.history.get(nxt.key(), 0) + 1
        return nxt

    def legal_moves(self) -> list:
        white = self.turn == "w"
        out = []
        for m in self.pseudo_moves():
            n = self.play(m)
            if not n.attacked(n.king(white), not white):
                out.append(m)
        return out

    # ---------------------------------------------------------------- notation and results
    @staticmethod
    def uci(m: Move) -> str:
        return name(m[0]) + name(m[1]) + m[2]

    def parse(self, text: str) -> Move | None:
        text = text.strip().lower().replace("-", "")
        for m in self.legal_moves():
            if self.uci(m) == text or (len(text) == 4 and self.uci(m) == text + "q"):
                return m
        return None

    def insufficient_material(self) -> bool:
        pieces = sorted(p.upper() for p in self.board if p not in ".Kk")
        return pieces in ([], ["B"], ["N"])

    def result(self) -> str | None:
        """None while the game is on, otherwise a description like 'checkmate - White wins'."""
        if not self.legal_moves():
            if self.in_check():
                return f"checkmate - {'Black' if self.turn == 'w' else 'White'} wins"
            return "stalemate - draw"
        if self.half >= 100:
            return "50-move rule - draw"
        if self.history.get(self.key(), 0) >= 3:
            return "threefold repetition - draw"
        if self.insufficient_material():
            return "insufficient material - draw"
        return None


def perft(pos: Position, depth: int) -> int:
    if depth == 0:
        return 1
    moves = pos.legal_moves()
    if depth == 1:
        return len(moves)
    return sum(perft(pos.play(m), depth - 1) for m in moves)
