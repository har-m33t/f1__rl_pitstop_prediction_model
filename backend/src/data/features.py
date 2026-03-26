"""
features.py — Phase 1 feature engineering module.

Exposes a single public entry point:

    build_feature_matrix(session_df) -> pd.DataFrame

This takes a cleaned race DataFrame (output of clean_data.clean_data) and
appends the five RL state features required by the Phase 1 spec. All column
names use the exact snake_case names defined in the spec.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.config import DEGRADATION_WINDOW


# ── Internal helpers ──────────────────────────────────────────────────────────

def _group_cols(df: pd.DataFrame) -> list[str]:
    """Return the grouping key that uniquely identifies a driver within a race."""
    base = ["DriverNumber"]
    if "Year" in df.columns:
        base = ["Year"] + base
    if "Track" in df.columns:
        base = ["Track"] + base
    return base


def _stint_cols(df: pd.DataFrame) -> list[str]:
    """Extend the group key with Stint for within-stint calculations."""
    gc = _group_cols(df)
    return gc + (["Stint"] if "Stint" in df.columns else [])


# ── Feature computers ─────────────────────────────────────────────────────────

def _tire_age(df: pd.DataFrame) -> pd.Series:
    """
    tire_age: laps completed on the current tire compound/stint.

    Signal: higher values correlate with greater degradation; the RL agent
    uses this as a proxy for how 'worn' the current set of tyres is.
    """
    if "TyreLife" in df.columns:
        # FastF1 provides TyreLife directly — prefer it for accuracy.
        return df["TyreLife"].ffill().fillna(0)
    else:
        # Fallback: cumulative lap count within each stint.
        return (
            df.groupby(_stint_cols(df)).cumcount() + 1
        ).astype(float)


def _lap_time_delta(df: pd.DataFrame) -> pd.Series:
    """
    lap_time_delta: seconds behind the driver's best lap on the same compound / stint.

    Signal: captures pace degradation relative to the driver's freshest-tyre
    performance; rising values are a strong pit-stop trigger for the RL agent.
    """
    if "LapTime" not in df.columns:
        return pd.Series(np.nan, index=df.index)

    sc = _stint_cols(df)
    best = df.groupby(sc)["LapTime"].transform("min")
    return (df["LapTime"] - best).clip(lower=0)


def _degradation_slope(df: pd.DataFrame, lap_time_delta: pd.Series) -> pd.Series:
    """
    degradation_slope: rolling linear regression slope of lap_time_delta over
    DEGRADATION_WINDOW laps (default 5).

    Signal: a positive and growing slope means the car is losing time more
    quickly each lap — a strong indicator that a pit stop is overdue.
    """
    sc = _stint_cols(df)

    def _slope(series: pd.Series) -> pd.Series:
        """Compute slope via a rolling OLS over a fixed window."""
        result = pd.Series(np.nan, index=series.index)
        arr = series.values
        win = DEGRADATION_WINDOW
        # Use vectorised polyfit for speed.
        for i in range(len(arr)):
            start = max(0, i - win + 1)
            window_vals = arr[start : i + 1]
            if len(window_vals) < 2 or np.isnan(window_vals).any():
                result.iloc[i] = 0.0
            else:
                x = np.arange(len(window_vals), dtype=float)
                result.iloc[i] = float(np.polyfit(x, window_vals, 1)[0])
        return result

    tmp = df.copy()
    tmp["_ltd"] = lap_time_delta.values

    slopes = tmp.groupby(sc)["_ltd"].transform(_slope)
    return slopes.fillna(0.0)


def _track_temp(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """
    track_temp: track temperature in °C.
    track_temp_is_proxy: True when AirTemp was used instead of TrackTemp.

    Signal: higher track temperature softens compounds faster, lowering the
    optimal strategy window; the proxy flag lets the model discount uncertain
    temperature inputs.
    """
    if "TrackTemp" in df.columns:
        is_proxy = df["TrackTemp"].isna()
        temp = df["TrackTemp"].copy()
        if "AirTemp" in df.columns:
            temp = temp.where(~is_proxy, df["AirTemp"])
        else:
            temp = temp.fillna(temp.median())
        return temp, is_proxy.astype(int)
    elif "AirTemp" in df.columns:
        return df["AirTemp"].copy(), pd.Series(1, index=df.index)
    else:
        return pd.Series(np.nan, index=df.index), pd.Series(1, index=df.index)


def _safety_car_flag(df: pd.DataFrame) -> pd.Series:
    """
    safety_car_flag: 1 if a Safety Car (SC) or Virtual Safety Car (VSC) was
    active during this lap, otherwise 0.

    Signal: the RL agent should avoid pitting under green-flag conditions when
    SC is imminent; conversely, it should exploit free stops during SC periods.
    FastF1 TrackStatus: '1'=clear, '4'=SC, '6'=VSC; compound strings like '14'.
    """
    if "TrackStatus" not in df.columns:
        return pd.Series(0, index=df.index)
    return df["TrackStatus"].astype(str).str.contains(r"4|6", regex=True).astype(int)


# ── Public entry point ────────────────────────────────────────────────────────

def build_feature_matrix(session_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute all Phase 1 RL state features for a cleaned race DataFrame.

    Parameters
    ----------
    session_df:
        Cleaned lap-level DataFrame (output of ``clean_data.clean_data``).
        Must contain at minimum ``LapNumber`` and ``DriverNumber``.

    Returns
    -------
    pd.DataFrame
        Original DataFrame with five new columns appended:
        ``tire_age``, ``lap_time_delta``, ``degradation_slope``,
        ``track_temp``, ``track_temp_is_proxy``, ``safety_car_flag``.
    """
    gc = _group_cols(session_df)
    df = (
        session_df
        .sort_values(gc + ["LapNumber"])
        .reset_index(drop=True)
        .copy()
    )

    # 1. Tire age
    df["tire_age"] = _tire_age(df)

    # 2. Lap time delta
    df["lap_time_delta"] = _lap_time_delta(df)

    # 3. Degradation slope  (depends on lap_time_delta)
    df["degradation_slope"] = _degradation_slope(df, df["lap_time_delta"])

    # 4. Track temperature + proxy flag
    df["track_temp"], df["track_temp_is_proxy"] = _track_temp(df)

    # 5. Safety car flag
    df["safety_car_flag"] = _safety_car_flag(df)

    return df
