import chess
import chess.engine
from pathlib import Path

# Adjust path if different
STOCKFISH = Path(r"C:\Users\visha\OneDrive\Documents\stockfish\stockfish-windows-x86-64-avx2.exe")

board = chess.Board()

with chess.engine.SimpleEngine.popen_uci(str(STOCKFISH)) as engine:
    result = engine.play(board, chess.engine.Limit(time=0.1))
    print("Best move:", result.move)
