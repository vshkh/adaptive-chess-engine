import argparse
import json
from src.ace.analysis import (
    load_game,
    extract_eval_curve,
    plot_eval_curve,
    plot_histogram_deltas,
    check_game,
    summarize_game,
    analyze_move_agreement,
)

def main():
    parser = argparse.ArgumentParser(description="A tool for analyzing PGN files from ACE.")
    subparsers = parser.add_subparsers(dest="command", required=True, help="Available commands")

    # 'plot' command
    parser_plot = subparsers.add_parser("plot", help="Plot evaluation curve and histograms for a PGN file.")
    parser_plot.add_argument("pgn_path", help="Path to the PGN file.")

    # 'check' command
    parser_check = subparsers.add_parser("check", help="Check a PGN file for data integrity.")
    parser_check.add_argument("pgn_path", help="Path to the PGN file.")

    # 'summary' command
    parser_summary = subparsers.add_parser("summary", help="Generate a JSON summary of a PGN file.")
    parser_summary.add_argument("pgn_path", help="Path to the PGN file.")
    
    # 'agreement' command
    parser_agreement = subparsers.add_parser("agreement", help="Analyze move agreement in a PGN file.")
    parser_agreement.add_argument("pgn_path", help="Path to the PGN file.")

    args = parser.parse_args()

    game = load_game(args.pgn_path)

    if args.command == "plot":
        evals = extract_eval_curve(game)
        plot_eval_curve(evals, title=f"Evaluation Curve: {args.pgn_path}")
        plot_histogram_deltas(game, title=f"Eval Histogram: {args.pgn_path}")
    elif args.command == "check":
        errors, plies = check_game(game)
        result = {
            "plies": plies,
            "result": game.headers.get("Result"),
            "errors": errors,
        }
        print(json.dumps(result, indent=2))
        if errors:
            exit(1)
    elif args.command == "summary":
        summary = summarize_game(game)
        print(json.dumps(summary, indent=2))
    elif args.command == "agreement":
        analyze_move_agreement(game)

if __name__ == "__main__":
    main()
