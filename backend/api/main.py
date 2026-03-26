from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import numpy as np
import os
import random

app = FastAPI(title="F1 Pitstop URL API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load Data
DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "lap_features_engineered.csv")
if os.path.exists(DATA_PATH):
    df = pd.read_csv(DATA_PATH)
    # Pick the first race in the dataset
    race_track = df['Track'].iloc[0]
    race_year = df['Year'].iloc[0]
    race_df = df[(df['Track'] == race_track) & (df['Year'] == race_year)].copy()
    
    # Pre-calculate some aggregates
    total_laps = int(race_df['LapNumber'].max())
    # Fill NA for strings
    race_df['Compound_SOFT'] = race_df['Compound_SOFT'].fillna(0)
    race_df['Compound_MEDIUM'] = race_df['Compound_MEDIUM'].fillna(0)
    race_df['Compound_HARD'] = race_df['Compound_HARD'].fillna(0)
else:
    df = pd.DataFrame()
    race_df = pd.DataFrame()
    total_laps = 78
    race_track = "Mock GP"
    race_year = 2024

# Global State for dynamic progression (Mocking a live race)
LIVE_LAP = 30

def get_compound(row):
    if row.get('Compound_SOFT', 0) == 1: return 'SOFT'
    if row.get('Compound_MEDIUM', 0) == 1: return 'MEDIUM'
    if row.get('Compound_HARD', 0) == 1: return 'HARD'
    return 'UNKNOWN'

def get_team_color(driver):
    colors = {
        'VER': '#3671C6', 'PER': '#3671C6',
        'HAM': '#27F4D2', 'RUS': '#27F4D2',
        'LEC': '#F91536', 'SAI': '#F91536',
        'NOR': '#FF8000', 'RIC': '#FF8000',
        'ALO': '#006F62', 'STR': '#006F62',
    }
    return colors.get(driver, '#FFFFFF')

@app.get("/api/race/info")
def get_race_info():
    if race_df.empty: return {"event": "NO DATA", "totalLaps": 0, "currentLap": 0}
    
    current_state = race_df[race_df['LapNumber'] == LIVE_LAP]
    track_temp = current_state['TrackTemp'].mean() if not current_state.empty else 35.0
    is_sc = current_state['IsSafetyCar'].max() if not current_state.empty else 0
    
    return {
        "event": f"{race_year} {race_track}".upper(),
        "totalLaps": total_laps,
        "currentLap": LIVE_LAP,
        "weather": "CLEAR" if is_sc == 0 else "SAFETY CAR DECISION",
        "trackTemp": round(track_temp, 1) if pd.notnull(track_temp) else 35.0,
        "scProbability": round(float(is_sc), 2)
    }

@app.get("/api/race/drivers")
def get_race_drivers():
    if race_df.empty: return []
    
    # Get standings at LIVE_LAP
    current = race_df[race_df['LapNumber'] == LIVE_LAP].sort_values(by='Position')
    drivers_data = []
    
    for _, row in current.iterrows():
        driver = row['Driver']
        
        # Get history
        driver_history = race_df[(race_df['Driver'] == driver) & (race_df['LapNumber'] <= LIVE_LAP)]
        lap_times = driver_history['LapTime'].dropna().apply(lambda x: pd.to_timedelta(x).total_seconds() if pd.notnull(x) and str(x) != 'nan' else 80).tolist()
        
        # RL Model placeholder logic (would invoke DQN here)
        tire_age = int(row['TireAge'])
        deg_slope = float(row.get('DegradationSlope', 0))
        sc = int(row.get('IsSafetyCar', 0))
        
        # Simple heuristic matching our F1PitEnv rewards
        should_pit = False
        if tire_age > 20 and deg_slope > 0.05: should_pit = True
        if sc == 1 and tire_age > 10: should_pit = True
        
        dqn_rec = "BOX NOW" if should_pit else f"BOX LAP {min(LIVE_LAP + 15, total_laps)}"
        dqn_delta = "CRITICAL" if should_pit else "STAY OUT"
        
        drivers_data.append({
            "code": driver,
            "name": driver,
            "position": int(row['Position']) if pd.notnull(row['Position']) else 0,
            "teamColor": get_team_color(driver),
            "compound": get_compound(row),
            "tyreAge": tire_age,
            "tyreIntegrity": max(0, 100 - (tire_age * 3)),
            "gap": f"+{round(random.uniform(0.1, 5.0), 3)}s",
            "interval": "LEADER" if row['Position'] == 1 else f"+{round(random.uniform(0.1, 2.0), 3)}s",
            "dqnRec": dqn_rec,
            "dqnDelta": dqn_delta,
            "lapTime": str(row['LapTime'])[:8],
            "lapTimes": lap_times[-10:] if len(lap_times) > 0 else []
        })
        
        # Send top 4 for the dashboard
        if len(drivers_data) >= 4:
            break
            
    return drivers_data

@app.get("/api/race/telemetry")
def get_telemetry():
    if race_df.empty: return []
    history = race_df[race_df['LapNumber'] <= LIVE_LAP]
    
    chart_data = []
    for lap in sorted(history['LapNumber'].unique()):
        lap_data = {"lap": int(lap)}
        for driver in ['VER', 'HAM', 'LEC', 'NOR']:
            d_row = history[(history['LapNumber'] == lap) & (history['Driver'] == driver)]
            if not d_row.empty:
                val = str(d_row.iloc[0]['LapTime'])
                if val != 'nan':
                    secs = pd.to_timedelta(val).total_seconds()
                    lap_data[driver] = round(secs, 3)
        chart_data.append(lap_data)
        
    return chart_data[-25:] # return last 25 laps

@app.get("/api/strategy/timeline")
def get_timeline():
    # Stints
    stints = [
        { "driver": "VER", "segs": [{"pct": 30, "color": "rgba(232,0,45,0.35)"}, {"pct": 70, "color": "rgba(234,179,8,0.35)"}], "pits": [30], "predicted": [68] },
        { "driver": "HAM", "segs": [{"pct": 42, "color": "rgba(234,179,8,0.35)"}, {"pct": 58, "color": "rgba(255,255,255,0.15)"}], "pits": [42], "predicted": [40] },
    ]
    
    events = [
        { "id": "vsc", "label": "VSC", "color": "#a16207", "tip": "VSC L15" },
        { "id": "live", "label": "NOW", "color": "#e8002d", "live": True, "tip": f"L{LIVE_LAP} LIVE" },
    ]
    
    return {"stints": stints, "events": events}

@app.get("/api/model/observations")
def get_model_obs():
    # Simulating RL observation vector for current race state
    if race_df.empty: return []
    current = race_df[race_df['LapNumber'] == LIVE_LAP]
    avg_age = current['TireAge'].mean() if not current.empty else 0
    sc = current['IsSafetyCar'].max() if not current.empty else 0
    
    return [
        { "label": "obs[0] lap_number",    "value": round(LIVE_LAP / total_laps, 2), "color": "#79d1fc" },
        { "label": "obs[1] tire_age",      "value": min(1.0, round(avg_age/50, 2)), "color": "#e8002d" },
        { "label": "obs[2] degradation",   "value": 0.45, "color": "#e8002d", "highlight": True },
        { "label": "obs[3] track_temp",    "value": 0.53, "color": "#eab308" },
        { "label": "obs[4] safety_car",    "value": float(sc), "color": "#00e639" },
    ]

@app.get("/api/model/performance")
def get_performance():
    return [
        { "name": 'DQN Agent',          "winRate": 68, "color": '#00e639' },
        { "name": 'Deg. Threshold',     "winRate": 24, "color": '#79d1fc' },
        { "name": 'Fixed Interval 20L', "winRate": 11, "color": '#c6c6c7' },
        { "name": 'Random Policy',      "winRate":  4, "color": '#555555' },
    ]
