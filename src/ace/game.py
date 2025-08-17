"""
- Provides the board and ruleset to check legality of moves and game states.
- Calls the engine and stores it in PGN, the text format used for storing chess games.
- This makes it possible to remember the game and all moves made so far rather than making moves with no memory.
"""

from __future__ import annotations
import chess
import chess.pgn
from .uci import Engine
from .pgn_io import save_pgn
from .logging_setup import setup_logging

log = setup_logging("ace.game")

def _format_pv(pv: list[chess.Move], limit: int = 6) -> str:
    return " ".join(str(m) for m in pv[:limit])

def play_self(depth_white: int = 12, depth_black: int = 12, max_moves: int = 300) -> str:
    """Stockfish vs Stockfish; returns PGN filepath."""
    board = chess.Board()
    game = chess.pgn.Game()
    game.headers["Event"] = "ACE Self-Play"
    game.headers["Site"] = "Local"
    game.headers["White"] = f"Stockfish(d{depth_white})"
    game.headers["Black"] = f"Stockfish(d{depth_black})"

    node = game
    with Engine() as eng_w, Engine() as eng_b:
        ply = 0
        while not board.is_game_over() and ply < max_moves:
            eng = eng_w if board.turn == chess.WHITE else eng_b
            depth = depth_white if board.turn == chess.WHITE else depth_black
            res = eng.analyse(board, depth=depth)
            move = res.best_move
            if move not in board.legal_moves:
                # Safety net
                move = next(iter(board.legal_moves))

            board.push(move)
            node = node.add_variation(move)

            parts = []
            if res.score_cp is not None:
                parts.append(f"eval_cp={res.score_cp}")
            if res.score_mate is not None:
                parts.append(f"mate_in={res.score_mate}")
            if res.pv:
                parts.append(f"pv={_format_pv(res.pv)}")
            node.comment = " | ".join(parts)
            ply += 1

    result = board.result()
    game.headers["Result"] = result
    out = save_pgn(game, name_prefix="tier1_selfplay")
    log.info("Finished self-play: result=%s pgn=%s", result, out)
    return str(out)
