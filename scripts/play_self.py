import argparse
import json
from src.ace.game import play_self
from src.ace.logging_setup import setup_logging
from src.ace.analysis import (
    load_game,
    summarize_game,
    extract_eval_curve,
    plot_eval_curve,
)

def main():
    setup_logging()
    p = argparse.ArgumentParser()
    p.add_argument("--dw", type=int, default=12)
    p.add_argument("--db", type=int, default=12)
    p.add_argument("--max-moves", type=int, default=300)
    p.add_argument("--style-white", type=str, default="aggressive")
    p.add_argument("--style-black", type=str, default="defensive")
    p.add_argument("--no-analysis", action="store_true", help="Disable analysis after the game.")
    args = p.parse_args()

    pgn_path = play_self(
        depth_white=args.dw,
        depth_black=args.db,
        max_moves=args.max_moves,
        style_white=args.style_white,
        style_black=args.style_black,
    )
    print(f"PGN saved to: {pgn_path}")

    if not args.no_analysis:
        print("\n--- Game Analysis ---")
        game = load_game(pgn_path)
        
        # Print summary
        summary = summarize_game(game)
        print(json.dumps(summary, indent=2))
        
        # Plot evaluation curve
        print("\nGenerating evaluation plot...")
        evals = extract_eval_curve(game)
        plot_eval_curve(evals, title=f"Evaluation Curve: {pgn_path}")
        print("Plot window opened. Close it to exit.")

if __name__ == "__main__":
    main()
