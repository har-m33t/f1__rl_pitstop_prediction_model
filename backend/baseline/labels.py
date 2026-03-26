"""
labels.py — Label construction and train/validation splitting for the F1 pit
stop baseline classifier.

Class imbalance note
--------------------
Pit stop laps are rare events. Typical ratios observed across 2022–2024:
  - 2022: ~1 pit lap per 18 regular laps  (~5.3 % positive rate)
  - 2023: ~1 pit lap per 17 regular laps  (~5.7 % positive rate)
  - 2024: ~1 pit lap per 18 regular laps  (~5.3 % positive rate)

Two strategies are supported, toggled via config:
  IMBALANCE_STRATEGY = "smote"          → SMOTE oversampling on training data
  IMBALANCE_STRATEGY = "class_weight"   → class_weight='balanced' passed to clf

Season split (no data leakage)
-------------------------------
  Train  : 2022 + 2023
  Validate: 2024
Data is NEVER shuffled across seasons to prevent temporal leakage.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import PROCESSED_PARQUET

logger = logging.getLogger(__name__)

# ── Config flags (override via env vars) ──────────────────────────────────────
# "smote" or "class_weight"
IMBALANCE_STRATEGY: str = os.getenv("F1_IMBALANCE_STRATEGY", "class_weight")

# Season splits — hard-coded to enforce train-before-validate temporal ordering.
TRAIN_YEARS: list[int] = [2022, 2023]
VAL_YEARS: list[int] = [2024]

# ── Feature columns used by the baseline model ────────────────────────────────
# These are produced by src.data.features.build_feature_matrix plus the
# feature_engineering pipeline. We also include base lap info as context.
FEATURE_COLS: list[str] = [
    # Phase 1 RL features
    "tire_age",
    "lap_time_delta",
    "degradation_slope",
    "track_temp",
    "track_temp_is_proxy",
    "safety_car_flag",
    # Additional engineered signals
    "LapNumber",
    "TyreLife",
    "AirTemp",
    "TrackTemp",
    "Humidity",
    "WindSpeed",
    "SpeedI1",
    "SpeedI2",
    "SpeedFL",
    "SpeedST",
]

LABEL_COL: str = "pit_label"


# ── Label construction ────────────────────────────────────────────────────────

def build_pit_label(df: pd.DataFrame) -> pd.DataFrame:
    """
    Construct the binary ``pit_label`` column.

    ``pit_label = 1``  if the driver pitted at the end of this lap
                       (i.e. PitInTime is not null after time conversion).
    ``pit_label = 0``  otherwise (driver stayed out).

    Parameters
    ----------
    df:
        Cleaned lap-level DataFrame that includes a ``PitInTime`` column
        (already converted to seconds by clean_data; non-null means a pit stop).

    Returns
    -------
    pd.DataFrame
        Input DataFrame with a new ``pit_label`` column appended.
    """
    if "PitInTime" in df.columns:
        df[LABEL_COL] = df["PitInTime"].notna().astype(int)
    elif "PitStopObserved" in df.columns:
        # Fallback: use the column produced by feature_engineering.py
        df[LABEL_COL] = df["PitStopObserved"].fillna(0).astype(int)
    else:
        raise ValueError(
            "DataFrame must contain 'PitInTime' or 'PitStopObserved' to construct pit_label."
        )

    # Log class distribution per available season
    if "Year" in df.columns:
        for year, grp in df.groupby("Year"):
            ratio = grp[LABEL_COL].mean()
            n_pits = grp[LABEL_COL].sum()
            logger.info(
                "Year %s — %d pit laps / %d total (%.1f%% positive rate)",
                year, n_pits, len(grp), ratio * 100,
            )

    return df


# ── Season-based split ────────────────────────────────────────────────────────

def season_split(
    df: pd.DataFrame,
    train_years: list[int] | None = None,
    val_years: list[int] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Split a labelled DataFrame chronologically by season year.

    Data is NOT shuffled to prevent temporal / data leakage. The training
    set contains all laps from ``train_years``; the validation set contains
    all laps from ``val_years``.

    Parameters
    ----------
    df:
        Labelled DataFrame with a ``Year`` column.
    train_years:
        Seasons to include in train split (default: [2022, 2023]).
    val_years:
        Seasons to include in validation split (default: [2024]).

    Returns
    -------
    (train_df, val_df): tuple of DataFrames, sorted by Year + LapNumber.
    """
    if train_years is None:
        train_years = TRAIN_YEARS
    if val_years is None:
        val_years = VAL_YEARS

    if "Year" not in df.columns:
        raise ValueError("DataFrame must contain a 'Year' column for season split.")

    sort_cols = [c for c in ["Year", "Track", "DriverNumber", "LapNumber"] if c in df.columns]

    train_df = (
        df[df["Year"].isin(train_years)]
        .sort_values(sort_cols)
        .reset_index(drop=True)
    )
    val_df = (
        df[df["Year"].isin(val_years)]
        .sort_values(sort_cols)
        .reset_index(drop=True)
    )

    logger.info(
        "Season split — train: %d laps (%s) | val: %d laps (%s)",
        len(train_df), train_years,
        len(val_df), val_years,
    )

    return train_df, val_df


# ── Feature/label extraction ──────────────────────────────────────────────────

def get_feature_matrix(
    df: pd.DataFrame,
    feature_cols: list[str] | None = None,
) -> tuple[pd.DataFrame, pd.Series]:
    """
    Extract X (features) and y (labels) from a labelled DataFrame.

    Only columns present in the DataFrame are used; missing columns are
    silently dropped with a warning so the pipeline is robust to partial data.

    Returns
    -------
    (X, y)
    """
    if feature_cols is None:
        feature_cols = FEATURE_COLS

    available = [c for c in feature_cols if c in df.columns]
    missing = set(feature_cols) - set(available)
    if missing:
        logger.warning("Feature columns not found and will be skipped: %s", sorted(missing))

    if LABEL_COL not in df.columns:
        raise ValueError(f"'{LABEL_COL}' column not found — run build_pit_label first.")

    X = df[available].copy()
    y = df[LABEL_COL].copy()

    # Final safety: drop rows where X has any NaN
    mask = X.notna().all(axis=1)
    n_dropped = (~mask).sum()
    if n_dropped:
        logger.warning("Dropping %d rows with NaN features before modelling.", n_dropped)
    X, y = X[mask], y[mask]

    return X, y


# ── SMOTE helper ──────────────────────────────────────────────────────────────

def apply_smote(
    X: pd.DataFrame,
    y: pd.Series,
    random_state: int = 42,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Apply SMOTE oversampling to the training set.

    Only called when IMBALANCE_STRATEGY == 'smote'. Requires the
    ``imbalanced-learn`` package (``pip install imbalanced-learn``).

    Returns
    -------
    (X_resampled, y_resampled) as numpy arrays.
    """
    try:
        from imblearn.over_sampling import SMOTE
    except ImportError as exc:
        raise ImportError(
            "SMOTE requires imbalanced-learn: pip install imbalanced-learn"
        ) from exc

    sm = SMOTE(random_state=random_state)
    X_res, y_res = sm.fit_resample(X, y)
    logger.info(
        "SMOTE applied — resampled train size: %d (was %d)", len(X_res), len(X)
    )
    return X_res, y_res


# ── Convenience: load processed data and build labels ────────────────────────

def load_labelled_data(path: Path | None = None) -> pd.DataFrame:
    """
    Load the processed parquet, compute RL features, and attach pit_label.

    Parameters
    ----------
    path:
        Path to parquet file. Defaults to ``config.PROCESSED_PARQUET``.

    Returns
    -------
    Fully labelled, feature-enriched DataFrame ready for ``season_split``.
    """
    if path is None:
        path = PROCESSED_PARQUET

    if not Path(path).exists():
        raise FileNotFoundError(
            f"Processed data not found at '{path}'.\n"
            "Run `python -m src.data.ingest` first to generate it."
        )

    df = pd.read_parquet(path)

    # Attach Phase 1 RL features
    from src.data.features import build_feature_matrix
    df = build_feature_matrix(df)

    # Construct pit labels
    df = build_pit_label(df)

    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
    df = load_labelled_data()
    train_df, val_df = season_split(df)
    X_train, y_train = get_feature_matrix(train_df)
    X_val, y_val = get_feature_matrix(val_df)
    print(f"Train: {X_train.shape}, positives={y_train.sum()} ({y_train.mean():.1%})")
    print(f"Val  : {X_val.shape}, positives={y_val.sum()} ({y_val.mean():.1%})")
