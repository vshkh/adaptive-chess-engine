from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class EngineConfig:
    # Update this path if your Stockfish binary moves
    stockfish_path: Path = Path(
        r"C:\Users\visha\OneDrive\Documents\stockfish\stockfish-windows-x86-64-avx2.exe"
    )
    skill_level: int = 20               # 0..20
    hash_mb: int = 256
    threads: int = 8
    default_depth: int = 12
    movetime_ms: int | None = None      # set to e.g. 1000 to use time instead of depth

@dataclass(frozen=True)
class Paths:
    root: Path = Path(__file__).resolve().parents[2]
    logs: Path = root / "logs"
    data: Path = root / "data"
    personas: Path = root / "src" / "personas"

CFG = EngineConfig()
PATHS = Paths()

# Ensure directories exist
PATHS.logs.mkdir(parents=True, exist_ok=True)
PATHS.data.mkdir(parents=True, exist_ok=True)
