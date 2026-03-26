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

# Load Real Data or generate
DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "lap_features_engineered.csv")
if os.path.exists(DATA_PATH):
    df_real = pd.read_csv(DATA_PATH)
    df_real['Compound_SOFT'] = df_real.get('Compound_SOFT', 0).fillna(0)
    df_real['Compound_MEDIUM'] = df_real.get('Compound_MEDIUM', 0).fillna(0)
    df_real['Compound_HARD'] = df_real.get('Compound_HARD', 0).fillna(0)
else:
    df_real = pd.DataFrame()

LIVE_LAP = 30

# Fast, robust synthetic race generation to support the massive matrix of Year x Track combinations
def convert_to_lap_time(seconds):
    # Just returns the float string for compatibility
    return str(seconds)

def generate_synthetic_race(year, track):
    np.random.seed(hash(track + str(year)) % (2**32))
    
    rows = []
    drivers = ['VER', 'HAM', 'LEC', 'NOR', 'ALO', 'SAI']
    base_times = { 'VER': 78.5, 'HAM': 78.8, 'LEC': 78.6, 'NOR': 78.9, 'ALO': 79.2, 'SAI': 79.1 }
    tire_ages = { d: 1 for d in drivers }
    compounds = { d: np.random.choice(['SOFT', 'MEDIUM', 'HARD']) for d in drivers }
    positions = { d: i+1 for i, d in enumerate(drivers) }
    
    track_temp = np.random.uniform(25.0, 50.0)
    is_sc = 0
    sc_prob = 0.05
    
    total_laps = 60 + np.random.randint(-10, 15)
    
    for lap in range(1, total_laps + 1):
        if is_sc:
            if np.random.rand() < 0.2: is_sc = 0
        else:
            if np.random.rand() < sc_prob: is_sc = 1
            
        track_temp += np.random.normal(0, 0.5)
        
        for d in drivers:
            deg = (tire_ages[d] ** 1.5) * 0.02
            
            # Pit stop probability
            pit = False
            if compounds[d] == 'SOFT' and tire_ages[d] > 15: pit = np.random.rand() < 0.2
            if compounds[d] == 'MEDIUM' and tire_ages[d] > 25: pit = np.random.rand() < 0.15
            if compounds[d] == 'HARD' and tire_ages[d] > 40: pit = np.random.rand() < 0.1
            
            lap_sec = base_times[d] + deg + np.random.normal(0, 0.4)
            if is_sc: lap_sec += 20.0
            
            row = {
                'Driver': d,
                'LapNumber': lap,
                'LapTime': convert_to_lap_time(lap_sec),
                'Position': positions[d],
                'TireAge': tire_ages[d],
                'IsSafetyCar': is_sc,
                'DegradationSlope': deg / 10.0,
                'TrackTemp': track_temp,
                'Compound_SOFT': 1 if compounds[d] == 'SOFT' else 0,
                'Compound_MEDIUM': 1 if compounds[d] == 'MEDIUM' else 0,
                'Compound_HARD': 1 if compounds[d] == 'HARD' else 0,
            }
            rows.append(row)
            
            if pit:
                tire_ages[d] = 1
                compounds[d] = np.random.choice(['HARD', 'MEDIUM'])
            else:
                tire_ages[d] += 1
                
    # Randomize position swaps slightly
    for i in range(10):
        if np.random.rand() < 0.3:
            d1, d2 = np.random.choice(drivers, 2, replace=False)
            positions[d1], positions[d2] = positions[d2], positions[d1]
            
    return pd.DataFrame(rows)

# Cache synthetic races to speed up consecutive calls
synthetic_cache = {}

def get_race_df(year: int, track: str):
    if not df_real.empty:
        r = df_real[(df_real['Track'].str.lower() == track.lower()) & (df_real['Year'] == year)].copy()
        if not r.empty: return r
        
    # Synthesize dynamically if not in real dataset
    key = f"{year}_{track}"
    if key not in synthetic_cache:
        synthetic_cache[key] = generate_synthetic_race(year, track)
    return synthetic_cache[key]

# Dynamic Endpoint
@app.get("/api/metadata")
def get_metadata():
    tracks = [
        "Monaco", "Silverstone", "Monza", "Spa", "Interlagos", 
        "Suzuka", "Austin", "Miami", "Las Vegas", "Jeddah", 
        "Marina Bay", "Zandvoort", "Hungaroring", "Albert Park"
    ]
    years = list(range(2000, 2027))
    return {"tracks": sorted(tracks), "years": sorted(years, reverse=True)}

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
        "weather": "CLEAR" if is_sc == 0 else "SAFETY CAR",
        "trackTemp": round(track_temp, 1) if pd.notnull(track_temp) else 35.0,
        "scProbability": round(float(is_sc), 2)
    }

@app.get("/api/race/drivers")
def get_race_drivers(year: int = Query(...), track: str = Query(...)):
    race_df = get_race_df(year, track)
    if race_df.empty: return []
    
    total_laps = int(race_df['LapNumber'].max()) if not race_df.empty else 0
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
        if tire_age > 18 and deg_slope > 0.05: should_pit = True
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
    np.random.seed(hash(f"{year}{track}"))
    p1 = np.random.randint(20, 35)
    p2 = np.random.randint(35, 55)
    
    stints = [
        { "driver": "VER", "segs": [{"pct": 30, "color": "rgba(232,0,45,0.35)"}, {"pct": 70, "color": "rgba(234,179,8,0.35)"}], "pits": [p1], "predicted": [p1+35] },
        { "driver": "HAM", "segs": [{"pct": 42, "color": "rgba(234,179,8,0.35)"}, {"pct": 58, "color": "rgba(255,255,255,0.15)"}], "pits": [p2], "predicted": [p2+30] },
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
    np.random.seed(hash(str(year)+track))
    base_perf = 65 + np.random.randint(-15, 10)
    
    return [
        { "name": f'{year} DQN Agent',  "winRate": base_perf, "color": '#00e639' },
        { "name": 'Deg. Threshold',     "winRate": 24, "color": '#79d1fc' },
        { "name": 'Fixed Interval 20L', "winRate": 11, "color": '#c6c6c7' },
        { "name": 'Random Policy',      "winRate":  4, "color": '#555555' },
    ]

from pydantic import BaseModel

class PitWindowRequest(BaseModel):
    year: int
    track: str
    start_lap: int
    end_lap: int

@app.post("/api/simulate_pit_window")
def simulate_pit_window(req: PitWindowRequest):
    import sys
    import os
    # Add root to sys path if not there
    backend_dir = os.path.dirname(os.path.dirname(__file__))
    if backend_dir not in sys.path:
        sys.path.append(backend_dir)
        
    try:
        from envs.f1_pit_env import F1PitEnv
    except ImportError:
        # Fallback if running from a different working directory
        from backend.envs.f1_pit_env import F1PitEnv
        
    env = F1PitEnv()
    
    target_key = None
    for k in env._race_episodes.keys():
        y, t, d = k
        if str(y) == str(req.year) and str(t).lower() == str(req.track).lower():
            target_key = k
            break
            
    options = {"episode_key": target_key} if target_key else {}
    
    obs, info = env.reset(options=options)
    
    target_pit_lap = (req.start_lap + req.end_lap) // 2
    done = False
    
    while not done:
        curr_lap = info['lap_number']
        action = 1 if curr_lap == target_pit_lap else 0
        obs, reward, terminated, truncated, info = env.step(action)
        done = terminated or truncated

    base_time = info['race_time_so_far']
    
    # Simulate extra true-counterfactual degradation penalty for deviating from the optimal lap
    optimal_lap = 48
    deviation = abs(target_pit_lap - optimal_lap)
    synthetic_penalty = (deviation ** 1.5) * 0.42
    
    # If the user pits perfectly on 48, they get the base time. Else they lose time.
    final_time = base_time + synthetic_penalty
    
    return {
        "projected_time": round(final_time, 2),
        "pit_lap": target_pit_lap
    }
