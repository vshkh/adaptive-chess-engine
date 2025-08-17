# Adaptive Chess Engine (Minimal Viable Product)

Baseline: talk to Stockfish via UCI, play full games, export PGNs with eval comments.

Update on 8/17:

- Created the repo and setup the skeleton of the engine to interact with Stockfish. As of now, its possible to simulate games and store them using .pgn (Portable Game Notation).
- Next goal is to start creating a function to stray away from maximizing the score, now add bias representing a personality.

## Quickstart (Windows / PowerShell)

```powershell
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
python .\scripts\play_self.py
```
