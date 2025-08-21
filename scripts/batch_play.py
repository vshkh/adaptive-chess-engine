import argparse
from src.ace.analysis import batch_selfplay, analyze_batch
from src.ace.logging_setup import setup_logging

def main():
    setup_logging()
    parser = argparse.ArgumentParser(description="Run a batch of self-play games and analyze the results.")
    parser.add_argument("n_games", type=int, help="Number of games to play.")
    parser.add_argument("--depth", type=int, default=6)
    parser.add_argument("--max-moves", type=int, default=80)
    parser.add_argument("--style-white", type=str, default="aggressive")
    parser.add_argument("--style-black", type=str, default="defensive")
    args = parser.parse_args()

    pgn_paths = batch_selfplay(
        n_games=args.n_games,
        depth=args.depth,
        max_moves=args.max_moves,
        style_white=args.style_white,
        style_black=args.style_black,
    )
    
    if pgn_paths:
        analyze_batch(pgn_paths)

if __name__ == "__main__":
    main()
