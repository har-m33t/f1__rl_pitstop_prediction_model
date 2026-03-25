# F1 Pit Stop — Simulation Environment

`envs/f1_pit_env.py` implements a standard **OpenAI Gymnasium** (`gym.Env`)
environment that wraps real FastF1 race data. Each episode is one driver's
race. The RL agent observes lap state every lap and decides whether to pit or
stay out.

---

## State → Action → Reward Flow

```
┌─────────────────────────────────────────────────────────┐
│                    ENVIRONMENT STATE                    │
│                                                         │
│  obs[0]  lap_number       Progress through the race     │
│  obs[1]  tire_age         Laps on current compound      │
│  obs[2]  degradation_rate Rolling slope of pace loss    │
│  obs[3]  track_temp       Track surface temp (°C)       │
│  obs[4]  safety_car_flag  SC/VSC active this lap        │
│                                                         │
│                All values normalised to [0, 1]          │
└───────────────────────┬─────────────────────────────────┘
                        │  obs_t
                        ▼
               ┌────────────────┐
               │   RL AGENT     │  (DQN / PPO / A2C …)
               └────────┬───────┘
                        │  action_t ∈ {0, 1}
                        ▼
        ┌───────────────────────────────┐
        │         ACTION SPACE           │
        │                               │
        │   0  →  Stay Out              │
        │         ↳ Lap time accrues    │
        │         ↳ Tire age +1         │
        │                               │
        │   1  →  Pit                   │
        │         ↳ Pit penalty −22 s   │
        │         ↳ Tire age resets → 0 │
        │         ↳ Stint counter +1    │
        └───────────────┬───────────────┘
                        │
                        ▼
        ┌───────────────────────────────────────┐
        │           REWARD FUNCTION              │
        │                                       │
        │  r(t) = − lap_time                    │ ← penalise slow laps
        │         − pit_penalty × a_t           │ ← one-off pit cost
        │         + end_position_bonus          │ ← terminal step only
        │                (at episode end)       │
        └───────────────────────────────────────┘
```

---

## Reward Function — Detailed

### `− lap_time`
Every lap the agent pays a cost equal to the actual lap time in seconds.
Degraded tyres produce slower laps → higher cost → the agent learns to pit
*before* pace deteriorates too much.

### `− pit_penalty × action`
Taking a pit stop (action = 1) subtracts a fixed penalty (default **22 s**),
approximating the real-world pit lane time loss. This prevents the agent from
pitting every lap to reset tyre age.

### `+ end_position_bonus`
At the final lap the agent receives a bonus proportional to how much faster its
cumulative race time is compared to the season median for that circuit:

```
delta_t  = median_race_time − agent_race_time   (positive = faster)
bonus    = max(0, delta_t / 20) × 5.0           (≈ 5 pts per place gained)
```

The divisor `20 s` approximates one track position gap in F1, and can be
tuned via `end_position_bonus_per_place`.

---

## State Space

| Index | Feature | Raw Range | Normalised |
|---|---|---|---|
| 0 | `lap_number` | 1 – 70 laps | 0 → 1 |
| 1 | `tire_age` | 0 – 50 laps | 0 → 1 |
| 2 | `degradation_rate` | −2 to +5 s/lap | 0 → 1 |
| 3 | `track_temp` | 15 – 65 °C | 0 → 1 |
| 4 | `safety_car_flag` | {0, 1} | {0, 1} |

All observations are `float32` and bounded to **[0, 1]** via `gymnasium.spaces.Box`.

---

## Action Space

| Action | Meaning | Side Effect |
|---|---|---|
| `0` | Stay out | Tyre age increments by 1 |
| `1` | Pit stop | Tyre age resets to 0, stint counter +1, `−pit_penalty` applied |

---

## Using the Environment

```python
from envs.f1_pit_env import F1PitEnv

env = F1PitEnv(seed=42)
obs, info = env.reset()

terminated = False
while not terminated:
    action = env.action_space.sample()       # replace with your agent
    obs, reward, terminated, truncated, info = env.step(action)
    env.render()

print(f"Total reward: {info['race_time_so_far']:.1f} s")
```

---

## Configuration

| Parameter | Default | Description |
|---|---|---|
| `data_path` | `data/processed/laps_processed.parquet` | Race episode data |
| `pit_penalty` | `22.0` s | Pit lane time loss |
| `end_position_bonus_per_place` | `5.0` | Bonus reward per place gained |
| `max_stints` | `4` | Maximum pit stops per race |
| `seed` | `None` | Random seed for episode sampling |

---

## DQN Baseline Threshold

The DQN must outperform the supervised baseline (Phase 2) on the 2024 holdout:

| Metric | Must Beat |
|---|---|
| F1-score | ≥ 0.35 |
| ROC-AUC | ≥ 0.80 |
| Recall | ≥ 0.60 |
