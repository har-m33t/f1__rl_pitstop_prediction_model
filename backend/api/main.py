from fastapi import FastAPI, Query, HTTPException
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

# Load Data Once Globally
DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "lap_features_engineered.csv")
if os.path.exists(DATA_PATH):
    df = pd.read_csv(DATA_PATH)
    df['Compound_SOFT'] = df['Compound_SOFT'].fillna(0)
    df['Compound_MEDIUM'] = df['Compound_MEDIUM'].fillna(0)
    df['Compound_HARD'] = df['Compound_HARD'].fillna(0)
else:
    df = pd.DataFrame()

# Global State for dynamic progression (Mocking a live race)
LIVE_LAP = 30

def get_race_df(year: int, track: str):
    if df.empty: return pd.DataFrame()
    return df[(df['Track'] == track) & (df['Year'] == year)].copy()

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

@app.get("/api/race/list")
def get_race_list():
    if df.empty: return []
    # Get unique (year, track) combos
    unique_races = df[['Year', 'Track']].drop_duplicates().sort_values(by=['Year', 'Track'], ascending=[False, True])
    races = []
    for _, row in unique_races.iterrows():
        races.append({
            "year": int(row['Year']),
            "track": str(row['Track'])
        })
    return races

@app.get("/api/race/info")
def get_race_info(year: int = Query(...), track: str = Query(...)):
    race_df = get_race_df(year, track)
    if race_df.empty: raise HTTPException(status_code=404, detail="Race not found")
    
    total_laps = int(race_df['LapNumber'].max()) if not race_df.empty else 0
    current_state = race_df[race_df['LapNumber'] == LIVE_LAP]
    track_temp = current_state['TrackTemp'].mean() if not current_state.empty else 35.0
    is_sc = current_state['IsSafetyCar'].max() if not current_state.empty else 0
    
    return {
        "event": f"{year} {track}".upper(),
        "totalLaps": total_laps,
        "currentLap": LIVE_LAP,
        "weather": "CLEAR" if is_sc == 0 else "SAFETY CAR DECISION",
        "trackTemp": round(track_temp, 1) if pd.notnull(track_temp) else 35.0,
        "scProbability": round(float(is_sc), 2)
    }

@app.get("/api/race/drivers")
def get_race_drivers(year: int = Query(...), track: str = Query(...)):
    race_df = get_race_df(year, track)
    if race_df.empty: return []
    
    total_laps = int(race_df['LapNumber'].max()) if not race_df.empty else 0
    
    # Get standings at LIVE_LAP
    current = race_df[race_df['LapNumber'] == LIVE_LAP].sort_values(by='Position')
    drivers_data = []
    
    for _, row in current.iterrows():
        driver = row['Driver']
        driver_history = race_df[(race_df['Driver'] == driver) & (race_df['LapNumber'] <= LIVE_LAP)]
        lap_times = driver_history['LapTime'].dropna().apply(lambda x: float(str(x).strip()) if pd.notnull(x) and str(x) != 'nan' else 80.0).tolist()
        
        tire_age = int(row['TireAge'])
        deg_slope = float(row.get('DegradationSlope', 0))
        sc = int(row.get('IsSafetyCar', 0))
        
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
        if len(drivers_data) >= 4:
            break
            
    return drivers_data

@app.get("/api/race/telemetry")
def get_telemetry(year: int = Query(...), track: str = Query(...)):
    race_df = get_race_df(year, track)
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
                    try:
                        secs = float(val)
                        lap_data[driver] = round(secs, 3)
                    except ValueError:
                        pass
        chart_data.append(lap_data)
        
    return chart_data[-25:]

@app.get("/api/strategy/timeline")
def get_timeline(year: int = Query(...), track: str = Query(...)):
    # Mocking stints logic for the specific query to demonstrate connectivity
    stints = [
        { "driver": "VER", "segs": [{"pct": 30, "color": "rgba(232,0,45,0.35)"}, {"pct": 70, "color": "rgba(234,179,8,0.35)"}], "pits": [30], "predicted": [68] },
        { "driver": "HAM", "segs": [{"pct": 42, "color": "rgba(234,179,8,0.35)"}, {"pct": 58, "color": "rgba(255,255,255,0.15)"}], "pits": [42], "predicted": [40] },
    ]
    events = [
        { "id": "vsc", "label": "VSC", "color": "#a16207", "tip": f"VSC {year} L15" },
        { "id": "live", "label": "NOW", "color": "#e8002d", "live": True, "tip": f"L{LIVE_LAP} LIVE - {track}" },
    ]
    return {"stints": stints, "events": events}

@app.get("/api/model/observations")
def get_model_obs(year: int = Query(...), track: str = Query(...)):
    race_df = get_race_df(year, track)
    if race_df.empty: return []
    
    total_laps = int(race_df['LapNumber'].max()) if not race_df.empty else 0
    current = race_df[race_df['LapNumber'] == LIVE_LAP]
    avg_age = current['TireAge'].mean() if not current.empty else 0
    sc = current['IsSafetyCar'].max() if not current.empty else 0
    
    return [
        { "label": "obs[0] lap_number",    "value": round(LIVE_LAP / (total_laps or 1), 2), "color": "#79d1fc" },
        { "label": "obs[1] tire_age",      "value": min(1.0, round(avg_age/50, 2)), "color": "#e8002d" },
        { "label": "obs[2] degradation",   "value": round(random.uniform(0.3, 0.7), 2), "color": "#e8002d", "highlight": True },
        { "label": "obs[3] track_temp",    "value": 0.53, "color": "#eab308" },
        { "label": "obs[4] safety_car",    "value": float(sc), "color": "#00e639" },
    ]

@app.get("/api/model/performance")
def get_performance(year: int = Query(...), track: str = Query(...)):
    # Performance is generally global over the model, not necessarily single race, 
    # but we will return it statically.
    return [
        { "name": f'{year} DQN Agent',          "winRate": 68 + random.randint(-5, 5), "color": '#00e639' },
        { "name": 'Deg. Threshold',     "winRate": 24, "color": '#79d1fc' },
        { "name": 'Fixed Interval 20L', "winRate": 11, "color": '#c6c6c7' },
        { "name": 'Random Policy',      "winRate":  4, "color": '#555555' },
    ]
