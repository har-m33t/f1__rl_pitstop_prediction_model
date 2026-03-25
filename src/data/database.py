import sqlite3
import pandas as pd
import os
from pathlib import Path

DB_PATH = Path("data/f1_predictions.db")

def init_db(db_path=DB_PATH):
    """
    Initializes the SQLite database and creates the necessary tables 
    for F1 lap features and RL model predictions.
    """
    os.makedirs(db_path.parent, exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA foreign_keys = ON;")

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS laps_features (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        Year INTEGER,
        Track TEXT,
        SessionType TEXT,
        Driver TEXT,
        DriverNumber INTEGER,
        LapNumber REAL,
        
        -- Base telemetry/timings (seconds)
        LapTime REAL,
        Sector1Time REAL,
        Sector2Time REAL,
        Sector3Time REAL,
        
`        -- Tires & Stints
`        Compound TEXT,
        TyreLife REAL,
        FreshTyre INTEGER,
        Stint INTEGER,
        
        -- Weather & Track proxy
        TrackStatus TEXT,
        AirTemp REAL,
        TrackTemp REAL,
        Humidity REAL,
        WindSpeed REAL,
        
        -- Engineered Features (RL State)
        PrevLapTime REAL,
        LapTimeDiff REAL,
        TireAge REAL,
        LapTimeDeltaFresh REAL,
        DegradationSlope REAL,
        IsSafetyCar INTEGER,
        
        -- Ground Truth
        PitStopObserved INTEGER,
        
        -- Ensure we don't insert the exact same lap twice
        UNIQUE(Year, Track, DriverNumber, LapNumber)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS pitstop_predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lap_feature_id INTEGER,
        
        -- Context (simplifies querying without always joining)
        Year INTEGER,
        Track TEXT,
        DriverNumber INTEGER,
        LapNumber REAL,
        
        -- RL Output
        ModelVersion TEXT,
        PredictedPitStop INTEGER,
        PredictionProbability REAL,
        Reward REAL,
        
        -- Metadata
        Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        
        -- Relation to the features table
        FOREIGN KEY(lap_feature_id) REFERENCES laps_features(id) ON DELETE CASCADE
    )
    ''')
    
    conn.commit()
    conn.close()
    print(f"Database schema initialized successfully at '{db_path}'")

def save_features_to_db(df: pd.DataFrame, db_path=DB_PATH):
    """
    Save a Pandas DataFrame of engineered features into the 'laps_features' table.
    Ignores rows that already exist (based on Year, Track, DriverNumber, LapNumber).
    """
    if df.empty:
        return
        
    conn = sqlite3.connect(db_path)
    
    cursor = conn.execute("PRAGMA table_info(laps_features)")
    db_columns = [col[1] for col in cursor.fetchall() if col[1] != 'id']
    
    cols_to_insert = [c for c in db_columns if c in df.columns]
    df_filtered = df[cols_to_insert].copy()
    
    df_filtered = df_filtered.where(pd.notnull(df_filtered), None)
    
    placeholders = ", ".join(["?"] * len(cols_to_insert))
    columns_str = ", ".join(cols_to_insert)
    
    sql = f"INSERT OR IGNORE INTO laps_features ({columns_str}) VALUES ({placeholders})"
    
    # Execute many
    try:
        conn.executemany(sql, df_filtered.values.tolist())
        conn.commit()
        print(f"Successfully processed {len(df_filtered)} records for the database.")
    except Exception as e:
        print(f"Error saving to database: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
    
    if os.path.exists("lap_features_engineered.csv"):
        print("Found 'lap_features_engineered.csv', bulk inserting into DB...")
        df_features = pd.read_csv("lap_features_engineered.csv")
        save_features_to_db(df_features)
