# Adaptive Chess Engine (Minimal Viable Product)

Baseline: talk to Stockfish via UCI, play full games, export PGNs with eval comments.

## Quickstart (Windows / PowerShell)

```powershell
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
python .\scripts\play_self.py
```
