import argparse
from src.ace.analysis import run_tournament, generate_crosstable
from src.ace.logging_setup import setup_logging

PERSONAS = ["aggressive", "defensive", "calculative", "nervous", "spontaneous", "random"]

def main():
    setup_logging()
    parser = argparse.ArgumentParser(description="Run a round-robin tournament between chess personas.")
    parser.add_argument("-n", "--n_games", type=int, default=2, help="Number of games per matchup (one as white, one as black).")
    parser.add_argument("--depth", type=int, default=8, help="Engine search depth.")
    parser.add_argument("--max-moves", type=int, default=100, help="Maximum moves per game.")
    args = parser.parse_args()

    # The number of games per matchup will be n_games / 2, since they play each other once as white and once as black.
    games_per_matchup = max(1, args.n_games // 2)

    pgn_paths = run_tournament(
        personas=PERSONAS,
        games_per_matchup=games_per_matchup,
        depth=args.depth,
        max_moves=args.max_moves,
    )
    
    if pgn_paths:
        generate_crosstable(pgn_paths, PERSONAS)

if __name__ == "__main__":
    main()
