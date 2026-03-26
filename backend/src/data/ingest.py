"""
ingest.py — Single-script pipeline orchestrator for Phase 1 data ingestion.

Usage:
    python -m src.data.ingest

What it does:
    1. Loads raw lap + weather data for TARGET_YEARS (default: 2022, 2023, 2024)
       using the FastF1 API, with local caching to avoid redundant downloads.
    2. Cleans and normalises the combined DataFrame.
    3. Saves the processed result to:
          data/processed/laps_processed.parquet   (primary, column-typed)
          data/processed/laps_processed.csv        (human-readable backup)

Re-running is idempotent: existing data is overwritten with fresh results so
the folder is always reproducible from a single script run.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd

# Allow running as `python -m src.data.ingest` from the project root.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import (
    PROCESSED_DIR,
    PROCESSED_PARQUET,
    PROCESSED_CSV,
    RAW_DIR,
    TARGET_YEARS,
)
from src.data.clean_data import clean_data
from src.data.load_data import load_all_data


def _ensure_dirs() -> None:
    """Create output directories if they don't exist yet."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def run_ingestion(years: list[int] | None = None) -> pd.DataFrame:
    """
    Full ingestion pipeline.

    Parameters
    ----------
    years:
        List of seasons to ingest. Defaults to ``config.TARGET_YEARS``.

    Returns
    -------
    pd.DataFrame
        Cleaned, processed DataFrame ready for feature engineering.
    """
    if years is None:
        years = TARGET_YEARS

    _ensure_dirs()

    print(f"\n{'='*60}")
    print(f"  F1 Pitstop RL — Data Ingestion Pipeline")
    print(f"  Target years : {years}")
    print(f"  Output       : {PROCESSED_PARQUET}")
    print(f"{'='*60}\n")

    t0 = time.time()

    # ── 1. Load raw data ──────────────────────────────────────────────────────
    print("[1/3] Loading raw sessions from FastF1 API (uses local cache)…")
    raw_df = load_all_data(years)

    if raw_df.empty:
        print("  ⚠  No data returned — check your FastF1 cache or network.")
        return raw_df

    print(f"  ✓  Loaded {len(raw_df):,} raw lap rows across {raw_df['Year'].nunique()} season(s).")

    # ── 2. Clean ──────────────────────────────────────────────────────────────
    print("\n[2/3] Cleaning and normalising…")
    clean_df = clean_data(raw_df.copy())
    n_dropped = len(raw_df) - len(clean_df)
    print(f"  ✓  {len(clean_df):,} laps retained ({n_dropped:,} invalid laps removed).")

    # ── 3. Save ───────────────────────────────────────────────────────────────
    print(f"\n[3/3] Saving processed data…")
    clean_df.to_parquet(PROCESSED_PARQUET, index=False)
    clean_df.to_csv(PROCESSED_CSV, index=False)
    print(f"  ✓  Parquet → {PROCESSED_PARQUET}")
    print(f"  ✓  CSV    → {PROCESSED_CSV}")

    elapsed = time.time() - t0
    print(f"\n  Pipeline complete in {elapsed:.1f}s.\n")

    return clean_df


if __name__ == "__main__":
    run_ingestion()
