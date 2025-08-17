import logging
from logging.handlers import RotatingFileHandler
from .config import PATHS

def setup_logging(name: str = "ace", level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(level)

    fmt = logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s")

    fh = RotatingFileHandler(PATHS.logs / "ace.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8")
    fh.setFormatter(fmt)
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger
