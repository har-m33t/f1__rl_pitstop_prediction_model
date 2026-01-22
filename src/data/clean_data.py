import pandas as pd

def drop_columns(df: pd.DataFrame) -> pd.DataFrame:
    DROP_COLUMNS = [
        "Deleted", "DeletedReason",
        "FastF1Generated", "IsAccurate",
        "LapStartDate",  # time leakage risk
    ]

    df = df.drop(columns=DROP_COLUMNS, errors = "ignore")
    
    return df


def change_time_to_seconds(df: pd.DataFrame) -> pd.DataFrame:
    TIME_COLUMNS = [
        "LapTime", "Sector1Time", "Sector2Time", 
        "Sector3Time", "PitInTime", "PitOutTime"
    ]

    for col in TIME_COLUMNS:
        df[col] = df[col].dt.total_seconds()
    return df

def handle_missing_numeric_values(df: pd.DataFrame) -> pd.DataFrame:
    NUMERIC_COLS = [
        "SpeedI1", "SpeedI2", "SpeedFL", "SpeedST",
        "AirTemp", "TrackTemp", "Humidity", "WindSpeed"
    ]

    df[NUMERIC_COLS] = df.groupby("Track")[
        NUMERIC_COLS
    ].transform(lambda x: x.fillna(x.median()))    

    return df

def handle_missing_categorical_values(df: pd.DataFrame) -> pd.DataFrame:
    df["Compound"] = df["Compound"].fillna('UNKNOWN') 
    df["Rainfall"] = df["Rainfall"].fillna(0)

    return df


def filter_invalid_laps(df: pd.DataFrame) -> pd.DataFrame:
    df = df[
        (df["LapTime"] > 60) &
        (df["LapTime"] < 200) &
        (~df["Deleted"])
    ]
    

def clean_data(df: pd.DataFrame):
    return df