"""
UCI - Universal Chess Interface

- This is a finite-state communication protocol to communicate with our choice of a chess engine (Stockfish).
- The client sends commands, like uci, isready, position, go depth, and the engine responds with a relevant state.

"""

from __future__ import annotations
import contextlib
from dataclasses import dataclass
import chess
import chess.engine
from .config import CFG
from .logging_setup import setup_logging

log = setup_logging("ace.uci")

@dataclass
class EvalResult:
    best_move: chess.Move
    ponder: chess.Move | None
    score_cp: int | None        # centipawns from side-to-move POV
    score_mate: int | None      # plies to mate (positive = good for side to move)
    depth: int
    pv: list[chess.Move]
    info_raw: dict

class Engine:
    def __init__(self, exe_path: str | None = None):
        path = str(CFG.stockfish_path if exe_path is None else exe_path)
        log.info("Launching Stockfish: %s", path)
        self._engine = chess.engine.SimpleEngine.popen_uci(path)
        self._set_options()

    def _set_options(self):
        opts = {
            "Skill Level": CFG.skill_level,
            "Threads": CFG.threads,
            "Hash": CFG.hash_mb,
        }
        for k, v in opts.items():
            try:
                self._engine.configure({k: v})
            except Exception as e:
                log.warning("Could not set option %s=%s (%s)", k, v, e)

    def analyse(self, board: chess.Board, depth: int | None = None, movetime_ms: int | None = None) -> EvalResult:
        secs = (movetime_ms or CFG.movetime_ms)
        if secs:
            secs = secs / 1000.0  # convert ms → seconds

        limit = chess.engine.Limit(
            depth=depth or CFG.default_depth,
            time=secs
        )
        info = self._engine.analyse(board, limit, multipv=1)
        # Handle both dict and list return types
        if isinstance(info, list):
            info = info[0]

        pv = info.get("pv", [])

        best = pv[0] if pv else None
        ponder = pv[1] if len(pv) > 1 else None

        score = info.get("score")
        score_cp = score.white().score(mate_score=100000) if score is not None else None
        score_mate = score.white().mate() if score is not None else None

        # Convert White-POV to side-to-move POV
        if board.turn is chess.BLACK:
            if score_cp is not None:
                score_cp = -score_cp
            if score_mate is not None:
                score_mate = -score_mate

        if best is None:
            # Fallback: ask engine to play
            res = self._engine.play(board, chess.engine.Limit(depth=limit.depth, movetime=limit.movetime))
            best = res.move

        return EvalResult(
            best_move=best,
            ponder=ponder,
            score_cp=score_cp,
            score_mate=score_mate,
            depth=info.get("depth", limit.depth or 0),
            pv=pv,
            info_raw=dict(info)
        )

    def play_best(self, board: chess.Board, depth: int | None = None) -> chess.Move:
        return self.analyse(board, depth=depth).best_move

    def close(self):
        with contextlib.suppress(Exception):
            self._engine.quit()

    def __enter__(self): return self
    def __exit__(self, exc_type, exc, tb): self.close()
