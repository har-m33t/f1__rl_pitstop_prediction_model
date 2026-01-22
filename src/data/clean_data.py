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
    return 

def handle_missing_values():
    return 

def filter_invalid_laps():
    return

def clean_data(df: pd.DataFrame):
    return df