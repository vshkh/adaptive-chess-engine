# src/ace/analysis.py
import re
import chess.pgn
import matplotlib.pyplot as plt
import collections
import logging
import statistics as st
import itertools
import pandas as pd
from pathlib import Path
from typing import List
from src.ace.game import play_self

# Constants for PGN comment parsing
REQ_KEYS = {"style", "best", "chosen"}
PAIR_KEYS = [("best", "best_cp"), ("chosen", "chosen_cp")]

def _pct(x, n):
    """Helper to calculate percentage."""
    return 0.0 if n == 0 else 100.0 * x / n

def load_game(path):
    with open(path, "r") as f:
        return chess.pgn.read_game(f)

def parse_comment(cmt: str) -> dict:
    """Parses a PGN comment string into a dictionary."""
    items = [s.strip() for s in cmt.split("|")]
    out = {}
    for it in items:
        if not it:
            continue
        if "=" in it:
            k, v = it.split("=", 1)
            out[k.strip()] = v.strip()
    
    for k_name, k_cp in PAIR_KEYS:
        if k_name in out and "(" in out[k_name] and out[k_name].endswith(")"):
            mv, cp = out[k_name].rsplit("(", 1)
            cp = cp[:-1]
            out[k_name] = mv
            if k_cp not in out:
                out[k_cp] = cp

    for k in ["eval_cp", "best_cp", "chosen_cp", "delta_cp"]:
        if k in out and out[k] not in (None, "None", ""):
            try:
                out[k] = int(out[k])
            except (ValueError, TypeError):
                out[k] = None
    return out

def extract_eval_curve(game: chess.pgn.Game) -> list[int]:
    """Extracts eval_cp from PGN comments for plotting."""
    evals = []
    node = game
    while node.variations:
        node = node.variation(0)
        data = parse_comment(node.comment or "")
        if (eval_cp := data.get("eval_cp")) is not None:
            evals.append(eval_cp)
    return evals

def plot_eval_curve(evals: list[int], title="Evaluation Curve"):
    # Clip evaluations to a reasonable range for better visualization
    clipped_evals = [max(min(e, 1500), -1500) for e in evals]
    plt.plot(clipped_evals)
    plt.axhline(0, color="black", linestyle="--")
    plt.ylim(-1600, 1600)
    plt.title(title)
    plt.xlabel("Move")
    plt.ylabel("Eval (centipawns)")
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.show()

def plot_histogram_deltas(game: chess.pgn.Game, title="Move Quality Histogram"):
    deltas = []
    node = game
    while node.variations:
        node = node.variation(0)
        data = parse_comment(node.comment or "")
        if (delta := data.get("delta_cp")) is not None:
            deltas.append(delta)
    plt.hist(deltas, bins=20)
    plt.title(title)
    plt.xlabel("Delta eval (centipawns)")
    plt.ylabel("Frequency")
    plt.show()

def check_game(game: chess.pgn.Game) -> tuple[list[str], int]:
    """Checks a game for comment consistency and returns a list of errors."""
    errors = []
    node = game
    ply = 0
    while node.variations:
        node = node.variation(0)
        ply += 1
        cmt = node.comment or ""
        data = parse_comment(cmt)
        
        missing = [k for k in REQ_KEYS if k not in data]
        if missing:
            errors.append(f"ply {ply}: missing keys {missing} in comment '{cmt}'")
        
        bc, cc, d = data.get("best_cp"), data.get("chosen_cp"), data.get("delta_cp")
        if isinstance(bc, int) and isinstance(cc, int) and isinstance(d, int):
            if d != cc - bc:
                errors.append(f"ply {ply}: delta_cp mismatch: {d} != {cc}-{bc}")

        if "feat" in data:
            if not re.fullmatch(r"[CKO\-]{3}", data["feat"]):
                errors.append(f"ply {ply}: bad feat '{data['feat']}'")
    return errors, ply

def summarize_game(game: chess.pgn.Game) -> dict:
    """Generates a statistical summary of a game."""
    plies = 0
    caps = chks = cas = 0
    deltas = []
    agree = 0
    styles = collections.Counter()
    node = game
    while node.variations:
        node = node.variation(0)
        plies += 1
        data = parse_comment(node.comment or "")
        
        if (feat := data.get("feat")):
            caps += (feat[0] == "C")
            chks += (feat[1] == "K")
            cas += (feat[2] == "O")
            
        if (delta := data.get("delta_cp")) is not None:
            deltas.append(delta)
            
        if data.get("best") and data.get("chosen"):
            agree += int(data["best"] == data["chosen"])
            
        if (style := data.get("style")):
            styles[style] += 1
    
    return {
        "result": game.headers.get("Result", "*"),
        "plies": plies,
        "captures_pct": round(_pct(caps, plies), 1),
        "checks_pct": round(_pct(chks, plies), 1),
        "castles_pct": round(_pct(cas, plies), 1),
        "delta_avg": (round(st.mean(deltas), 1) if deltas else None),
        "delta_std": (round(st.pstdev(deltas), 1) if len(deltas) > 1 else None),
        "engine_agreement_pct": round(_pct(agree, plies), 1),
        "styles_counts": dict(styles),
    }

def analyze_move_agreement(game: chess.pgn.Game):
    """Calculates and prints the percentage of moves where the chosen move agrees with the engine's best move."""
    agree = total = 0
    node = game
    while node.variations:
        node = node.variation(0)
        data = parse_comment(node.comment or "")
        if data.get("best") and data.get("chosen"):
            agree += int(data["best"] == data["chosen"])
            total += 1
    pct = (100.0 * agree / total) if total else 0.0
    print(f"Move Agreement: {pct:.2f}%")

def outcome_counts(paths):
    counts = collections.Counter()
    for p in paths:
        g = load_game(p)
        counts[g.headers.get("Result", "*")] += 1
    return counts

def plot_outcomes(counts, title="Results Distribution"):
    labels = list(counts.keys())
    sizes = list(counts.values())
    plt.bar(labels, sizes)
    plt.title(title)
    plt.xlabel("Result")
    plt.ylabel("Count")
    plt.show()

def run_matchup(n_games: int, depth: int, max_moves: int, persona_white: str, persona_black: str) -> list[str]:
    """Run several selfplay games and return list of PGN paths"""
    pgn_paths = []
    for i in range(n_games):
        print(f"--- Playing game {i+1}/{n_games} ({persona_white} vs {persona_black}) ---")
        pgn_path = play_self(
            depth_white=depth,
            depth_black=depth,
            max_moves=max_moves,
            persona_white=persona_white,
            persona_black=persona_black,
        )
        pgn_paths.append(pgn_path)
    return pgn_paths

def run_tournament(personas: list[str], games_per_matchup: int, depth: int, max_moves: int) -> list[str]:
    """Runs a round-robin tournament between all specified personas."""
    all_pgn_paths = []
    matchups = list(itertools.permutations(personas, 2))
    print(f"Starting tournament with {len(personas)} personas and {len(matchups)} matchups.")
    
    for p_w, p_b in matchups:
        pgn_paths = run_matchup(
            n_games=games_per_matchup,
            depth=depth,
            max_moves=max_moves,
            persona_white=p_w,
            persona_black=p_b,
        )
        all_pgn_paths.extend(pgn_paths)
        
    print(f"\n--- Tournament Finished: {len(all_pgn_paths)} games played ---")
    return all_pgn_paths

def generate_crosstable(pgn_paths: List[str], personas: List[str]):
    """Generates and prints a crosstable of results from a list of PGN files."""
    df = pd.DataFrame(0.0, index=personas, columns=personas)

    for pgn_path in pgn_paths:
        game = load_game(pgn_path)
        white_header = game.headers.get("White", "")
        black_header = game.headers.get("Black", "")
        result = game.headers.get("Result", "*")

        try:
            white_persona = re.search(r", (.*?)\)", white_header).group(1)
            black_persona = re.search(r", (.*?)\)", black_header).group(1)
        except AttributeError:
            continue # Skip if persona not found in header

        if white_persona not in df.index or black_persona not in df.columns:
            continue # Skip if persona from PGN is not in the official list

        if result == "1-0":
            df.loc[white_persona, black_persona] += 1.0
        elif result == "0-1":
            # This was the bug: it should be black scoring against white
            df.loc[black_persona, white_persona] += 1.0
        elif result == "1/2-1/2":
            # Corrected logic: only add 0.5 to each player's score against the other
            df.loc[white_persona, black_persona] += 0.5
            df.loc[black_persona, white_persona] += 0.5

    # Add a total score column
    df["Total"] = df.sum(axis=1)
    print("\n--- Tournament Crosstable ---")
    print(df)

def analyze_batch(pgn_paths: list[str]):
    """Analyzes a batch of games and prints a summary of the results."""
    print("\n--- Batch Analysis ---")
    
    # Outcome distribution
    counts = outcome_counts(pgn_paths)
    print("\n--- Outcome Distribution ---")
    # sort counts by key
    sorted_counts = collections.OrderedDict(sorted(counts.items()))
    for result, count in sorted_counts.items():
        print(f"{result}: {count}")
    
    plot_outcomes(counts, title=f"{len(pgn_paths)} games batch result")

    # Aggregate summaries
    all_summaries = [summarize_game(load_game(p)) for p in pgn_paths]
    
    # Example of further analysis: average engine agreement
    agreement_scores = [s['engine_agreement_pct'] for s in all_summaries if s['engine_agreement_pct'] is not None]
    if agreement_scores:
        avg_agreement = st.mean(agreement_scores)
        print(f"\nAverage Engine Agreement: {avg_agreement:.2f}%")
