import argparse
from src.ace.analysis import (
    load_game, extract_eval_curve, plot_eval_curve,
    plot_histogram_deltas, batch_selfplay, outcome_counts, plot_outcomes
)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("pgn_path", nargs="?", help="Path to PGN file (optional if --batch)")
    p.add_argument("--batch", type=int, help="Run N self-play games instead of analyzing one")
    p.add_argument("--depth", type=int, default=6)
    p.add_argument("--max-moves", type=int, default=80)
    args = p.parse_args()

    if args.batch:
        paths = batch_selfplay(n_games=args.batch, depth=args.depth, max_moves=args.max_moves)
        counts = outcome_counts(paths)
        plot_outcomes(counts, title=f"{args.batch} games at depth {args.depth}")
    else:
        if not args.pgn_path:
            print("Need PGN path unless using --batch")
            return
        game = load_game(args.pgn_path)
        evals = extract_eval_curve(game)
        plot_eval_curve(evals, title=f"Evaluation curve: {args.pgn_path}")
        plot_histogram_deltas(game, title=f"Eval histogram: {args.pgn_path}")

if __name__ == "__main__":
    main()
