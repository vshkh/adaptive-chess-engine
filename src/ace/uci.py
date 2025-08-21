"""
UCI - Universal Chess Interface

- This is a finite-state communication protocol to communicate with our choice of a chess engine (Stockfish).
- The client sends commands, like uci, isready, position, go depth, and the engine responds with a relevant state.

"""

from __future__ import annotations
import contextlib
from dataclasses import dataclass
import json
import chess
import chess.engine
from .config import CFG, PATHS
from .logging_setup import setup_logging
from typing import List, Tuple, Optional

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

@dataclass
class Candidate:
    move: chess.Move
    score_cp: Optional[int]       # centipawns, side-to-move POV
    score_mate: Optional[int]
    depth: int
    pv: list[chess.Move]
    is_capture: bool
    gives_check: bool
    is_castle: bool

class Engine:
    def __init__(self, exe_path: str | None = None, persona_name: str | None = None):
        path = str(CFG.stockfish_path if exe_path is None else exe_path)
        log.info("Launching Stockfish: %s", path)
        self._engine = chess.engine.SimpleEngine.popen_uci(path)
        
        self.persona = None
        if persona_name:
            persona_path = PATHS.personas / f"{persona_name}.json"
            if persona_path.exists():
                log.info("Loading persona: %s", persona_path)
                with open(persona_path, "r") as f:
                    self.persona = json.load(f)
            else:
                log.warning("Persona file not found: %s", persona_path)

        self._set_options()

    @property
    def move_selection_style(self) -> str:
        if self.persona and "move_selection_style" in self.persona:
            return self.persona["move_selection_style"]
        return "pure"

    def _set_options(self):
        # Start with base options
        opts = {
            "Skill Level": CFG.skill_level,
            "Threads": CFG.threads,
            "Hash": CFG.hash_mb,
        }
        # Override with persona options if they exist
        if self.persona and "uci_options" in self.persona:
            opts.update(self.persona["uci_options"])

        log.info("Configuring engine with options: %s", opts)
        for k, v in opts.items():
            try:
                self._engine.configure({k: v})
            except Exception as e:
                log.warning("Could not set option %s=%s (%s)", k, v, e)

    def _make_limit(self, depth: int | None, movetime_ms: int | None):
        # python-chess uses "time" (seconds), not "movetime"
        t = (movetime_ms / 1000.0) if movetime_ms else None
        return chess.engine.Limit(depth=depth or CFG.default_depth, time=t)


    def analyse(self, board: chess.Board, depth: int | None = None, movetime_ms: int | None = None) -> EvalResult:
        secs = (movetime_ms or CFG.movetime_ms)
        if secs:
            secs = secs / 1000.0  # convert ms → seconds

        limit = self._make_limit(depth, movetime_ms or CFG.movetime_ms)

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
    
    def analyse_candidates(self, board: chess.Board, depth: int | None = None, k: int = 4) -> List[Candidate]:
        """Return up to k candidate moves with evals and simple features."""
        limit = self._make_limit(depth, CFG.movetime_ms)
        infos = self._engine.analyse(board, limit, multipv=max(1, k))

        # python-chess may return dict or list
        if isinstance(infos, dict):
            infos = [infos]

        # Ensure sorted by multipv (1 = best)
        def get_mpv(d): return d.get("multipv", 1)
        infos = sorted(infos, key=get_mpv)

        cands: List[Candidate] = []
        for info in infos:
            pv = info.get("pv", [])
            if not pv:
                # Fallback: ask engine to play if pv missing
                best = self._engine.play(board, chess.engine.Limit(depth=limit.depth, movetime=limit.movetime)).move
                pv = [best]
            move = pv[0]

            score = info.get("score")
            score_cp = score.white().score(mate_score=100000) if score is not None else None
            score_mate = score.white().mate() if score is not None else None
            if board.turn is chess.BLACK:
                if score_cp is not None: score_cp = -score_cp
                if score_mate is not None: score_mate = -score_mate

            cands.append(Candidate(
                move=move,
                score_cp=score_cp,
                score_mate=score_mate,
                depth=info.get("depth", limit.depth or 0),
                pv=pv,
                is_capture=board.is_capture(move),
                gives_check=board.gives_check(move),
                is_castle=board.is_castling(move),
            ))
        return cands

    def play_best(self, board: chess.Board, depth: int | None = None) -> chess.Move:
        return self.analyse(board, depth=depth).best_move

    def close(self):
        with contextlib.suppress(Exception):
            self._engine.quit()

    def __enter__(self): return self
    def __exit__(self, exc_type, exc, tb): self.close()
