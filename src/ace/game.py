"""
- Provides the board and ruleset to check legality of moves and game states.
- Calls the engine and stores it in PGN, the text format used for storing chess games.
- This makes it possible to remember the game and all moves made so far rather than making moves with no memory.
"""

from __future__ import annotations
import math, random
import chess
import chess.pgn
from .uci import Engine, Candidate
from .pgn_io import save_pgn
from .logging_setup import setup_logging

log = setup_logging("ace.game")

def aggressive_score(c: Candidate, mean_score: float) -> float:
    base = (c.score_cp or -10000)
    bonus = 0.0
    if c.is_capture: bonus += 80.0   # favor taking (increased)
    if c.gives_check: bonus += 50.0  # favor forcing moves (increased)
    # small nudge toward sharp lines (bigger spread from mean)
    bonus += 0.02 * abs((c.score_cp or 0) - mean_score)
    return base + bonus

def defensive_score(c: Candidate, mean_score: float) -> float:
    base = (c.score_cp or -10000)
    bonus = 0.0
    if c.is_castle: bonus += 50.0            # king safety
    if not c.is_capture: bonus += 20.0       # quiet, solid moves (increased)
    if c.gives_check: bonus -= 15.0          # avoid forcing unless clearly good (increased penalty)
    bonus -= 0.03 * abs((c.score_cp or 0) - mean_score)  # shrink toward mean (risk-averse): penalize outliers (increased)
    return base + bonus

def calculative_score(c: Candidate, mean_score: float) -> float:
    base = (c.score_cp or -10000)
    # prefer moves that are near the consensus (low dispersion),
    # and slightly prefer higher depth PVs (proxy for "confidence")
    dispersion_pen = 0.03 * abs((c.score_cp or 0) - mean_score)
    depth_bonus = 0.5 * (c.depth or 0)
    # avoid noisy tactics unless clearly good
    tactic_pen = 8.0 if (c.is_capture or c.gives_check) and (c.score_cp or 0) < 50 else 0.0
    return base - dispersion_pen + depth_bonus - tactic_pen

SCORERS = {
    "aggressive": aggressive_score,
    "defensive": defensive_score,
    "calculative": calculative_score,
    "hesitant": calculative_score,  # alias
    "cautious": calculative_score,  # alias
}

def _format_pv(pv: list[chess.Move], limit: int = 6) -> str:
    return " ".join(str(m) for m in pv[:limit])

def play_self(depth_white: int = 12, depth_black: int = 12, max_moves: int = 300,
              persona_white: str | None = None, persona_black: str | None = None) -> str:
    """Play a game with optional personalities; returns PGN filepath."""
    board = chess.Board()
    game = chess.pgn.Game()
    game.headers["Event"] = "ACE Self-Play"
    game.headers["Site"] = "Local"
    game.headers["White"] = f"Stockfish(d{depth_white}, {persona_white or 'pure'})"
    game.headers["Black"] = f"Stockfish(d{depth_black}, {persona_black or 'pure'})"

    node = game
    with Engine(persona_name=persona_white) as eng_w, Engine(persona_name=persona_black) as eng_b:
        ply = 0
        while not board.is_game_over(claim_draw=True) and ply < max_moves:
            if board.turn == chess.WHITE:
                eng, depth = eng_w, depth_white
            else:
                eng, depth = eng_b, depth_black

            # Get the move selection style from the engine's loaded persona
            style = eng.move_selection_style

            # choose move + metadata (has chosen_cp/best_cp)
            move, meta = choose_move_with_style(board, eng, depth=depth, style=style, k=4)

            # safe fallback if something went sideways
            legal = list(board.legal_moves)
            if move not in legal:
                if not legal:  # terminal (checkmate/stalemate)
                    break
                move = random.choice(legal)

            # compute features for THIS final move
            is_cap = board.is_capture(move)
            is_chk = board.gives_check(move)
            is_cas = board.is_castling(move)

            # snapshot the pre-move position for feature checks
            pre_board = board.copy(stack=False)

            # push and annotate the move node once
            board.push(move)
            node = node.add_variation(move)

            eval_cp = meta.get("chosen_cp")
            parts = []
            if eval_cp is not None:
                parts.append(f"eval_cp={eval_cp}")
            parts.append(f"style={meta.get('style')}")
            if "best" in meta:
                parts.append(f"best={meta['best']}({meta.get('best_cp')})")
            parts.append(f"chosen={meta.get('chosen')}({meta.get('chosen_cp')})")
            parts.append(f"delta_cp={meta.get('delta_cp')}")
            parts.append(f"feat={'C' if is_cap else '-'}{'K' if is_chk else '-'}{'O' if is_cas else '-'}")
            node.comment = " | ".join(str(p) for p in parts)

            ply += 1

    # stamp result and save
    result = board.result(claim_draw=True)
    game.headers["Result"] = result
    out = save_pgn(game, name_prefix="tier2_selfplay")
    log.info("Finished self-play: result=%s pgn=%s", result, out)
    return str(out)

def choose_move_with_style(board: chess.Board, eng: Engine, depth: int, style: str, k: int = 4) -> tuple[chess.Move, dict]:
    """
    Returns (chosen_move, meta) where meta includes best_move, delta_cp, and debug info.
    Styles: 'aggressive', 'defensive', 'calculative', 'random'
    """
    cands = eng.analyse_candidates(board, depth=depth, k=k)

    # Safety: if engine gave nothing, fall back
    if not cands:
        legal = list(board.legal_moves)
        if not legal:
            return None, {"style": "fallback", "chosen_cp": None, "best_cp": None, "delta_cp": None}
        m = random.choice(legal)
        return m, {
            "style": "fallback",
            "best": str(m),
            "best_cp": None,
            "chosen": str(m),
            "chosen_cp": None,
            "delta_cp": None,
            "k": 0,
        }

    # Use top candidate as "pure Stockfish best"
    best = cands[0]

    # Aggregate stats for personality scoring
    scores = [c.score_cp if c.score_cp is not None else -10_000 for c in cands]
    mean_score = sum(scores) / len(scores) if scores else 0.0

    style = style.lower()
    if style in SCORERS:
        f = SCORERS[style]
        scored = [f(c, mean_score) for c in cands]
        idx = max(range(len(scored)), key=scored.__getitem__)
    elif style == "random":
        vals = [float(c.score_cp or -10000) for c in cands]
        idx = softmax_select(vals, T=150.0)
    else:
        # pure Stockfish path
        return best.move, {
            "style": "pure",
            "best": str(best.move),
            "best_cp": best.score_cp,
            "chosen": str(best.move),
            "chosen_cp": best.score_cp,
            "delta_cp": 0,
            "k": len(cands),
        }

    chosen = cands[idx]
    delta = (chosen.score_cp or 0) - (best.score_cp or 0)
    meta = {
        "style": style,
        "best": str(best.move),
        "best_cp": best.score_cp,
        "chosen": str(chosen.move),
        "chosen_cp": chosen.score_cp,
        "delta_cp": delta,
        "k": len(cands),
    }
    return chosen.move, meta

def softmax_select(vals: list[float], T: float = 120.0) -> int:
    # higher T = more random; vals are in centipawns scale
    exps = [math.exp(v / max(T, 1e-6)) for v in vals]
    s = sum(exps)
    r = random.random() * s
    acc = 0.0
    return next((i for i, e in enumerate(exps) if (acc := acc + e) >= r), len(vals) - 1)
