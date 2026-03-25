"""
config.py — Centralized configuration for the F1 RL Pitstop Prediction project.

All file paths and session parameters live here. Override any value by setting
the corresponding environment variable (or adding it to a .env file in the
project root). This avoids hardcoded strings scattered across modules.
"""

from __future__ import annotations

import os
from pathlib import Path

# ── Optional .env support ────────────────────────────────────────────────────
# If python-dotenv is installed, load a .env file from the project root.
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
except ImportError:
    pass  # dotenv is optional; defaults below are always used as fallback.

# ── Project root ─────────────────────────────────────────────────────────────
ROOT_DIR: Path = Path(__file__).resolve().parents[1]

# ── Data directories ─────────────────────────────────────────────────────────
DATA_DIR: Path = Path(os.getenv("F1_DATA_DIR", str(ROOT_DIR / "data")))
RAW_DIR: Path = Path(os.getenv("F1_RAW_DIR", str(DATA_DIR / "raw")))
PROCESSED_DIR: Path = Path(os.getenv("F1_PROCESSED_DIR", str(DATA_DIR / "processed")))
CACHE_DIR: Path = Path(os.getenv("F1_CACHE_DIR", str(RAW_DIR)))  # FastF1 cache

# ── Database ─────────────────────────────────────────────────────────────────
DB_PATH: Path = Path(os.getenv("F1_DB_PATH", str(DATA_DIR / "f1_predictions.db")))

# ── Session / ingestion settings ─────────────────────────────────────────────
# Years to ingest. Override via F1_TARGET_YEARS="2022,2023,2024"
_years_env = os.getenv("F1_TARGET_YEARS", "2022,2023,2024")
TARGET_YEARS: list[int] = [int(y.strip()) for y in _years_env.split(",")]

# Session type to ingest (R = Race).
SESSION_TYPE: str = os.getenv("F1_SESSION_TYPE", "R")

# ── Feature-engineering settings ─────────────────────────────────────────────
# Rolling window (laps) for computing degradation slope.
DEGRADATION_WINDOW: int = int(os.getenv("F1_DEGRADATION_WINDOW", "5"))

# ── Processed output filenames ────────────────────────────────────────────────
PROCESSED_PARQUET: Path = PROCESSED_DIR / "laps_processed.parquet"
PROCESSED_CSV: Path = PROCESSED_DIR / "laps_processed.csv"
