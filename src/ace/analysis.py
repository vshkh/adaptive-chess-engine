import random
import chess.pgn
import matplotlib.pyplot as plt
from pathlib import Path
from src.ace.game import play_self

def load_game(pgn_path: str | Path):
    """Load the first game from a PGN file."""
    with open(pgn_path, encoding="utf-8") as f:
        return chess.pgn.read_game(f)

def extract_eval_curve(game) -> list[int | None]:
    """Return a list of centipawn evals (from comments) for the mainline."""
    evals = []
    board = game.board()
    for node in game.mainline():
        comment = node.comment
        if "eval_cp=" in comment:
            try:
                part = comment.split("eval_cp=")[1]
                val = part.split()[0]     # grab number before space or pipe
                evals.append(int(val))
            except Exception:
                evals.append(None)
        else:
            evals.append(None)
        board.push(node.move)
    return evals

def plot_eval_curve(evals: list[int | None], title="Evaluation Curve"):
    xs = list(range(1, len(evals) + 1))
    ys = [e if e is not None else 0 for e in evals]
    plt.figure(figsize=(10, 5))
    plt.plot(xs, ys, marker="o", markersize=3, linewidth=1)
    plt.axhline(0, color="k", linestyle="--")
    plt.xlabel("Ply (half-moves)")
    plt.ylabel("Evaluation (centipawns)")
    plt.title(title)
    plt.show()

def plot_histogram_deltas(game, title="Move Quality Histogram"):
    """Histogram of eval differences between chosen move and PV[0]."""
    deltas = []
    board = game.board()
    for node in game.mainline():
        comment = node.comment
        if "eval_cp=" in comment:
            try:
                val = int(comment.split("eval_cp=")[1].split()[0])
                deltas.append(val)
            except:
                continue
        board.push(node.move)

    if not deltas:
        print("No eval deltas found.")
        return

    plt.figure(figsize=(8, 5))
    plt.hist(deltas, bins=30, color="steelblue", edgecolor="black")
    plt.xlabel("Evaluation (centipawns)")
    plt.ylabel("Frequency")
    plt.title(title)
    plt.show()

def batch_selfplay(n_games=10, depth=6, max_moves=80, out_dir="data") -> list[str]:
    """Run N self-play games and return list of PGN paths."""
    paths = []
    for i in range(n_games):
        fname = play_self(depth_white=depth, depth_black=depth, max_moves=max_moves)
        paths.append(fname)
    return paths

def outcome_counts(pgn_paths: list[str]) -> dict[str, int]:
    """Count 1-0, 0-1, 1/2-1/2, * across PGNs."""
    counts = {"1-0": 0, "0-1": 0, "1/2-1/2": 0, "*": 0}
    for path in pgn_paths:
        with open(path, encoding="utf-8") as f:
            game = chess.pgn.read_game(f)
            res = game.headers.get("Result", "*")
            counts[res] = counts.get(res, 0) + 1
    return counts

def plot_outcomes(counts: dict[str, int], title="Self-Play Outcomes"):
    labels = list(counts.keys())
    values = list(counts.values())
    plt.figure(figsize=(6, 4))
    plt.bar(labels, values, color=["#4caf50", "#f44336", "#2196f3", "#9e9e9e"])
    plt.ylabel("Frequency")
    plt.title(title)
    plt.show()
