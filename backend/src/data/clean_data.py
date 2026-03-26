import pandas as pd


def drop_columns(df: pd.DataFrame) -> pd.DataFrame:
    DROP_COLUMNS = [
        "Deleted", "DeletedReason",
        "FastF1Generated", "IsAccurate",
        "LapStartDate",  # time leakage risk
    ]
    df = df.drop(columns=DROP_COLUMNS, errors="ignore")
    return df


def change_time_to_seconds(df: pd.DataFrame) -> pd.DataFrame:
    TIME_COLUMNS = [
        "LapTime", "Sector1Time", "Sector2Time",
        "Sector3Time", "PitInTime", "PitOutTime"
    ]

    for col in TIME_COLUMNS:
        if col in df.columns:
            # If loaded from CSV as strings, parse to timedelta first
            if df[col].dtype == object:
                df[col] = pd.to_timedelta(df[col])
            # Extract total seconds from timedelta
            if pd.api.types.is_timedelta64_dtype(df[col]):
                df[col] = df[col].dt.total_seconds()

    return df


def filter_invalid_laps(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove clearly invalid laps:
      - LapTime outside a plausible F1 race window (60–200 s)
      - Laps marked as Deleted (only if the column still exists pre-drop)
    """
    mask = (df["LapTime"] > 60) & (df["LapTime"] < 200)

    # 'Deleted' may already have been dropped by drop_columns; guard accordingly
    if "Deleted" in df.columns:
        mask = mask & (~df["Deleted"].fillna(False))

    return df[mask].reset_index(drop=True)


def handle_missing_numeric_values(df: pd.DataFrame) -> pd.DataFrame:
    NUMERIC_COLS = [
        "SpeedI1", "SpeedI2", "SpeedFL", "SpeedST",
        "AirTemp", "TrackTemp", "Humidity", "WindSpeed"
    ]
    present = [c for c in NUMERIC_COLS if c in df.columns]

    if "Track" in df.columns and present:
        df[present] = df.groupby("Track")[present].transform(
            lambda x: x.fillna(x.median())
        )
    elif present:
        df[present] = df[present].fillna(df[present].median())

    return df


def handle_missing_categorical_values(df: pd.DataFrame) -> pd.DataFrame:
    if "Compound" in df.columns:
        df["Compound"] = df["Compound"].fillna("UNKNOWN")
    if "Rainfall" in df.columns:
        df["Rainfall"] = df["Rainfall"].fillna(0)
    return df


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Full cleaning pipeline:
      1. Convert timedelta columns to seconds
      2. Filter invalid laps
      3. Drop metadata/leakage columns
      4. Impute missing numeric weather values
      5. Fill missing categoricals
    """
    df = change_time_to_seconds(df)
    df = filter_invalid_laps(df)
    df = drop_columns(df)
    df = handle_missing_numeric_values(df)
    df = handle_missing_categorical_values(df)
    return df