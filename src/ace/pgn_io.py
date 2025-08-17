from __future__ import annotations
from datetime import datetime
from pathlib import Path
import chess.pgn
from .config import PATHS

def save_pgn(game: chess.pgn.Game, name_prefix: str = "tier1_game") -> Path:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = PATHS.data / f"{name_prefix}_{ts}.pgn"
    with open(out, "w", encoding="utf-8") as f:
        exporter = chess.pgn.FileExporter(f)
        game.accept(exporter)
    return out
