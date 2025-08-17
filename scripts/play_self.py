import argparse
from src.ace.game import play_self
from src.ace.logging_setup import setup_logging

def main():
    setup_logging()
    p = argparse.ArgumentParser(description="Stockfish vs Stockfish self-play")
    p.add_argument("--dw", type=int, default=12, help="White depth")
    p.add_argument("--db", type=int, default=12, help="Black depth")
    p.add_argument("--max-moves", type=int, default=300, help="Max ply (half-moves)")
    args = p.parse_args()
    pgn_path = play_self(depth_white=args.dw, depth_black=args.db, max_moves=args.max_moves)
    print("PGN saved to:", pgn_path)

if __name__ == "__main__":
    main()
