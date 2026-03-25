# F1 Pit Stop RL Prediction Model

Reinforcement learning model that predicts optimal F1 pit stop windows using
historical race lap data from the [FastF1](https://docs.fastf1.dev/) API.

---

## Quickstart

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the full data ingestion pipeline (2022–2024)
python -m src.data.ingest

# 3. Run the test suite
python -m pytest tests/ -v
```

All paths and session parameters are configurable via environment variables
or a `.env` file in the project root — see `src/config.py` for the full list.

---

## Project Structure

```
src/
  config.py               # Centralized path & session config
  data/
    load_data.py          # FastF1 API helpers (session, laps, weather)
    clean_data.py         # Lap cleaning & normalisation
    ingest.py             # Pipeline orchestrator — run this for data
    features.py           # Phase 1 RL feature engineering (build_feature_matrix)
    feature_engineering.py# Extended feature set (target var, lag, encoding)
    database.py           # SQLite persistence layer
data/
  raw/                    # FastF1 cache (gitignored)
  processed/              # Output of ingest.py (gitignored)
    laps_processed.parquet
    laps_processed.csv
tests/
  data_tests/
    test_load_data.py
    test_clean_data.py
    test_features.py      # Smoke test for build_feature_matrix
```

---

## Data Schema

Output of `python -m src.data.ingest` → `data/processed/laps_processed.parquet`

All time columns are in **seconds** (converted from FastF1 timedeltas).

### Identification

| Column | dtype | Units | Description |
|---|---|---|---|
| `Year` | int | — | Championship season year |
| `Track` | str | — | Grand Prix event name (e.g. "Bahrain Grand Prix") |
| `Driver` | str | — | Three-letter driver code (e.g. "HAM") |
| `DriverNumber` | int | — | Official FIA driver number |
| `LapNumber` | float | lap | Lap index within the race session |

### Lap Timings

| Column | dtype | Units | Description |
|---|---|---|---|
| `LapTime` | float | seconds | Total lap time |
| `Sector1Time` | float | seconds | Time to complete sector 1 |
| `Sector2Time` | float | seconds | Time to complete sector 2 |
| `Sector3Time` | float | seconds | Time to complete sector 3 |
| `PitInTime` | float | seconds | Session time when the car entered the pit lane (null if no stop) |
| `PitOutTime` | float | seconds | Session time when the car exited the pit lane (null if no stop) |

### Tire & Stints

| Column | dtype | Units | Description |
|---|---|---|---|
| `Compound` | str | — | Tire compound: SOFT / MEDIUM / HARD / INTER / WET / UNKNOWN |
| `TyreLife` | float | laps | Laps completed on the current set at start of this lap |
| `FreshTyre` | int (0/1) | — | 1 if the tire is new (zero previous use) |
| `Stint` | int | — | Stint number within the race (increments after each pit stop) |

### Track & Weather

| Column | dtype | Units | Description |
|---|---|---|---|
| `TrackStatus` | str | — | FastF1 track status code(s): "1"=clear, "4"=SC, "6"=VSC |
| `AirTemp` | float | °C | Ambient air temperature |
| `TrackTemp` | float | °C | Track surface temperature |
| `Humidity` | float | % | Relative humidity |
| `WindSpeed` | float | m/s | Wind speed at circuit |
| `Rainfall` | int (0/1) | — | 1 if it was raining during the lap |

### Speed Traps

| Column | dtype | Units | Description |
|---|---|---|---|
| `SpeedI1` | float | km/h | Speed at first intermediate timing point |
| `SpeedI2` | float | km/h | Speed at second intermediate timing point |
| `SpeedFL` | float | km/h | Speed at the finish line |
| `SpeedST` | float | km/h | Speed at the speed trap (longest straight) |

---

## Phase 1 RL Feature Columns

Computed by `src.data.features.build_feature_matrix(session_df)`.

| Column | dtype | Units | Description |
|---|---|---|---|
| `tire_age` | float | laps | Laps on the current compound; primary degradation signal |
| `lap_time_delta` | float | seconds | Gap to the driver's best lap on fresh tires this stint |
| `degradation_slope` | float | s/lap | Rolling OLS slope of `lap_time_delta` over last 5 laps |
| `track_temp` | float | °C | Track temperature; AirTemp used as fallback |
| `track_temp_is_proxy` | int (0/1) | — | 1 when AirTemp was substituted for missing TrackTemp |
| `safety_car_flag` | int (0/1) | — | 1 if Safety Car or Virtual Safety Car was active this lap |

---

## Configuration

Override defaults via environment variables or `.env` file:

| Variable | Default | Description |
|---|---|---|
| `F1_DATA_DIR` | `./data` | Root data directory |
| `F1_RAW_DIR` | `./data/raw` | FastF1 cache & raw downloads |
| `F1_PROCESSED_DIR` | `./data/processed` | Cleaned parquet/CSV output |
| `F1_TARGET_YEARS` | `2022,2023,2024` | Comma-separated seasons to ingest |
| `F1_DEGRADATION_WINDOW` | `5` | Lap window for rolling degradation slope |
| `F1_DB_PATH` | `./data/f1_predictions.db` | SQLite database path |
