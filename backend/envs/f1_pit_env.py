"""
f1_pit_env.py — OpenAI Gym environment for F1 pit stop decision making.

This is the core Phase 3 deliverable. The environment wraps real historical
lap data from the Phase 1 pipeline and exposes a standard gym.Env interface
for training any RL algorithm (DQN, PPO, A2C, etc.).

State Space (5-dimensional, continuous Box)
-------------------------------------------
  [0] lap_number        – current lap in the race (normalised 0-1)
  [1] tire_age          – laps on current compound (normalised 0-1)
  [2] degradation_rate  – rolling slope of lap_time_delta (s/lap, normalised)
  [3] track_temp        – track surface temperature in °C (normalised 0-1)
  [4] safety_car_flag   – 1 if SC/VSC active, 0 otherwise

Action Space (Discrete 2)
--------------------------
  0  →  Stay out   (continue racing on current tyres)
  1  →  Pit        (take a pit stop; incurs pit_penalty, resets tire state)

Reward Function
---------------
  r(t) = - lap_time          # penalise slow laps (degraded tyres = slower)
         - pit_penalty * a   # one-off penalty when pitting (time lost in lane)
         + end_position_bonus (at episode end only)

See _compute_reward() for implementation details.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

# ── Gym import with graceful fallback message ─────────────────────────────────
try:
    import gymnasium as gym
    from gymnasium import spaces
    _GYM_BACKEND = "gymnasium"
except ImportError:
    try:
        import gym
        from gym import spaces
        _GYM_BACKEND = "gym"
    except ImportError:
        raise ImportError(
            "A gym backend is required. Install one:\n"
            "  pip install gymnasium\n"
            "  # or: pip install gym"
        )

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import PROCESSED_PARQUET

# ── Environment constants ─────────────────────────────────────────────────────
# Pit lane time loss penalty in seconds.
# Typical F1 pit stop = ~25 s stationary + ~5–7 s pit lane delta ≈ 20-23 s net.
PIT_PENALTY_SECONDS: float = 22.0

# Bonus applied at race end, proportional to final estimated track position.
# Position 1 → full bonus, Position 20 → zero. Scaled to race lap-time order.
END_POSITION_BONUS_PER_PLACE: float = 5.0

# Observation normalisation bounds
OBS_LAP_MAX: float = 70.0          # very long races (Monaco ~80 laps, but 70 covers most)
OBS_TIRE_AGE_MAX: float = 50.0     # max realistic laps on one compound
OBS_DEG_SLOPE_MIN: float = -2.0    # s per lap (improving)
OBS_DEG_SLOPE_MAX: float = 5.0     # s per lap (heavy degradation)
OBS_TEMP_MIN: float = 15.0         # °C cold track
OBS_TEMP_MAX: float = 65.0         # °C very hot track


class F1PitEnv(gym.Env):
    """
    F1 Pit Stop Decision Environment.

    Each *episode* is one driver's race — a sequence of laps drawn from real
    historical FastF1 data. The agent observes the current lap state and decides
    each lap whether to stay out or pit.

    Parameters
    ----------
    data_path:
        Path to the processed parquet produced by ``src.data.ingest``.
        Defaults to ``config.PROCESSED_PARQUET``.
    pit_penalty:
        Seconds added to lap time when the agent chooses to pit (action=1).
        Default: 22.0 s (realistic F1 pit lane loss).
    end_position_bonus_per_place:
        Reward bonus per estimated track position gained at race end.
    max_stints:
        Maximum number of pit stops allowed per episode (hard limit).
        Default: 4 (ultra-soft to hard strategy is typically 2; 4 is generous).
    seed:
        Random seed for episode sampling.
    """

    metadata = {"render_modes": ["human"], "render_mode": None}

    def __init__(
        self,
        data_path: Optional[Path] = None,
        pit_penalty: float = PIT_PENALTY_SECONDS,
        end_position_bonus_per_place: float = END_POSITION_BONUS_PER_PLACE,
        max_stints: int = 4,
        seed: Optional[int] = None,
    ) -> None:
        super().__init__()

        self.pit_penalty = pit_penalty
        self.end_position_bonus_per_place = end_position_bonus_per_place
        self.max_stints = max_stints
        self._rng = np.random.default_rng(seed)

        # ── Load and validate data ────────────────────────────────────────────
        path = Path(data_path or PROCESSED_PARQUET)
        self._race_episodes = self._load_episodes(path)

        # ── Spaces ────────────────────────────────────────────────────────────
        # Observation: 5D continuous vector, all values normalised to [0, 1]
        # except safety_car_flag which is already binary.
        #
        # Index  Feature             Raw range           Normalised
        # ─────  ──────────────────  ──────────────────  ────────────
        #   0    lap_number          [1, ~70]            [0, 1]
        #   1    tire_age            [0, ~50]            [0, 1]
        #   2    degradation_rate    [-2, +5] s/lap      [0, 1]
        #   3    track_temp          [15, 65] °C         [0, 1]
        #   4    safety_car_flag     {0, 1}              {0, 1}
        self.observation_space = spaces.Box(
            low=np.zeros(5, dtype=np.float32),
            high=np.ones(5, dtype=np.float32),
            dtype=np.float32,
        )

        # Action: 0 = stay out, 1 = pit
        self.action_space = spaces.Discrete(2)

        # ── Episode state (initialised in reset) ──────────────────────────────
        self._laps: pd.DataFrame = pd.DataFrame()
        self._current_step: int = 0
        self._current_tire_age: float = 0.0
        self._current_stint: int = 1
        self._total_race_time: float = 0.0
        self._n_pits: int = 0
        self._episode_key: tuple = ("", 0)  # (track, driver)

    # ── Public API ────────────────────────────────────────────────────────────

    def reset(
        self,
        *,
        seed: Optional[int] = None,
        options: Optional[dict] = None,
    ) -> tuple[np.ndarray, dict]:
        """
        Start a new episode by sampling one driver's race at random.

        Returns
        -------
        (obs, info)
        """
        super().reset(seed=seed)
        if seed is not None:
            self._rng = np.random.default_rng(seed)

        # Pick a random (race, driver) episode by default
        keys = list(self._race_episodes.keys())
        key = keys[self._rng.integers(len(keys))]
        
        # Override with requested key if provided
        if options and "episode_key" in options:
            req_key = options["episode_key"]
            if req_key in self._race_episodes:
                key = req_key

        self._laps = self._race_episodes[key].reset_index(drop=True)
        self._episode_key = key

        # Reset episode state
        self._current_step = 0
        self._current_tire_age = float(self._laps.at[0, "_raw_tire_age"])
        self._current_stint = 1
        self._total_race_time = 0.0
        self._n_pits = 0

        obs = self._get_obs()
        info = {"episode_key": str(key), "total_laps": len(self._laps)}
        return obs, info

    def step(
        self, action: int
    ) -> tuple[np.ndarray, float, bool, bool, dict]:
        """
        Advance the environment by one lap.

        Parameters
        ----------
        action:
            0 = stay out, 1 = pit this lap end.

        Returns
        -------
        obs, reward, terminated, truncated, info
        """
        assert self.action_space.contains(action), f"Invalid action: {action}"

        row = self._laps.iloc[self._current_step]
        lap_time = float(row["LapTime"])

        # ── Pit stop logic ────────────────────────────────────────────────────
        pitted = False
        if action == 1 and self._n_pits < self.max_stints:
            pitted = True
            self._n_pits += 1
            self._current_tire_age = 0.0      # fresh set
            self._current_stint += 1

        # ── Tire state update ─────────────────────────────────────────────────
        self._current_tire_age += 1.0

        # ── Reward ────────────────────────────────────────────────────────────
        reward = self._compute_reward(lap_time, pitted, is_final=False)
        self._total_race_time += lap_time + (self.pit_penalty if pitted else 0.0)

        # ── Step counter ──────────────────────────────────────────────────────
        self._current_step += 1
        terminated = self._current_step >= len(self._laps)

        if terminated:
            reward += self._end_position_bonus()

        obs = self._get_obs() if not terminated else np.zeros(5, dtype=np.float32)

        info = {
            "lap_number": int(row.get("LapNumber", self._current_step)),
            "tire_age": self._current_tire_age,
            "pit_stop_taken": pitted,
            "n_pits_total": self._n_pits,
            "race_time_so_far": self._total_race_time,
        }

        return obs, float(reward), terminated, False, info

    def render(self) -> None:
        """Print a simple text summary of the current lap state."""
        if self._current_step == 0:
            print("Episode not started — call reset() first.")
            return
        row = self._laps.iloc[self._current_step - 1]
        print(
            f"Lap {int(row.get('LapNumber', self._current_step)):>3} | "
            f"TireAge={self._current_tire_age:>5.1f} | "
            f"Stint={self._current_stint} | "
            f"Pits={self._n_pits} | "
            f"RaceTime={self._total_race_time:>8.2f}s"
        )

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _get_obs(self) -> np.ndarray:
        """
        Build the 5D normalised observation vector from the current lap row.

        Returns float32 array with all values in [0, 1].
        """
        if self._current_step >= len(self._laps):
            return np.zeros(5, dtype=np.float32)

        row = self._laps.iloc[self._current_step]

        # lap_number — normalised to [0, 1]
        lap_num = float(row.get("LapNumber", self._current_step + 1))
        total = float(len(self._laps))
        obs_lap = np.clip(lap_num / OBS_LAP_MAX, 0.0, 1.0)

        # tire_age — use our tracked value (agent may have pitted)
        obs_tire = np.clip(self._current_tire_age / OBS_TIRE_AGE_MAX, 0.0, 1.0)

        # degradation_rate — from precomputed degradation_slope column
        raw_deg = float(row.get("degradation_slope", 0.0))
        obs_deg = np.clip(
            (raw_deg - OBS_DEG_SLOPE_MIN) / (OBS_DEG_SLOPE_MAX - OBS_DEG_SLOPE_MIN),
            0.0, 1.0,
        )

        # track_temp
        raw_temp = float(row.get("track_temp", 35.0))
        obs_temp = np.clip(
            (raw_temp - OBS_TEMP_MIN) / (OBS_TEMP_MAX - OBS_TEMP_MIN),
            0.0, 1.0,
        )

        # safety_car_flag — already binary
        obs_sc = float(row.get("safety_car_flag", 0.0))

        return np.array(
            [obs_lap, obs_tire, obs_deg, obs_temp, obs_sc],
            dtype=np.float32,
        )

    def _compute_reward(
        self, lap_time: float, pitted: bool, is_final: bool
    ) -> float:
        """
        Compute per-step reward.

        Reward = - lap_time
                 - pit_penalty  (only when pitted)
                 + end_position_bonus  (only at terminal step, via caller)

        Design rationale:
          * Penalising lap_time directly links tyre degradation to reward —
            worn tyres = slower laps = lower cumulative reward. The agent
            learns to pit before degradation becomes too costly.
          * pit_penalty makes early/excessive pitting costly, replicating the
            real trade-off between track position and tyre life.
          * end_position_bonus anchors the episode reward to race outcome,
            preventing the agent from maximising intermediate rewards at the
            expense of finishing position.
        """
        r = -lap_time
        if pitted:
            r -= self.pit_penalty
        return r

    def _end_position_bonus(self) -> float:
        """
        Estimate race finishing position from cumulative race time and award
        a proportional bonus.

        Without a full multi-agent race simulation, we approximate position by
        comparing this driver's total race time against the season median race
        time for the same circuit. Faster than median → better position.

        Bonus = max(0, places_gained) * end_position_bonus_per_place
        """
        # Use the precomputed reference time stored on the episode
        ref_time = float(self._laps.attrs.get("season_median_race_time", self._total_race_time))
        delta = ref_time - self._total_race_time  # positive = faster than median

        # Convert seconds delta to estimated place gain (rough: ~1 place per 20 s)
        SECONDS_PER_PLACE = 20.0
        places_gained = delta / SECONDS_PER_PLACE
        bonus = max(0.0, places_gained) * self.end_position_bonus_per_place
        return bonus

    # ── Data loading ──────────────────────────────────────────────────────────

    @staticmethod
    def _load_episodes(path: Path) -> dict[tuple, pd.DataFrame]:
        """
        Load the processed parquet and split it into per-(track, driver)
        episodes. Returns a dict keyed by (Year, Track, DriverNumber).

        Each episode DataFrame has Phase 1 RL features pre-computed and
        stores the season median race time in DataFrame.attrs for use as the
        end-position reference.

        Raises FileNotFoundError if the parquet is missing.
        """
        if not path.exists():
            raise FileNotFoundError(
                f"Processed data not found at '{path}'.\n"
                "Run: python -m src.data.ingest"
            )

        df = pd.read_parquet(path)

        # Attach Phase 1 RL features if not already present
        if "degradation_slope" not in df.columns:
            from src.data.features import build_feature_matrix
            df = build_feature_matrix(df)

        # Store raw tire age in a helper column for reset()
        df["_raw_tire_age"] = df["tire_age"] if "tire_age" in df.columns else 0.0

        # Group key
        group_cols = ["Year", "Track", "DriverNumber"]
        available = [c for c in group_cols if c in df.columns]

        # Compute season-median race time per (Year, Track) for end-position bonus
        if "LapTime" in df.columns and "Year" in df.columns and "Track" in df.columns:
            race_totals = (
                df.groupby(["Year", "Track", "DriverNumber"])["LapTime"]
                .sum()
                .reset_index(name="total_time")
            )
            medians = (
                race_totals.groupby(["Year", "Track"])["total_time"]
                .median()
                .to_dict()
            )
        else:
            medians = {}

        episodes = {}
        for key, grp in df.groupby(available):
            grp_sorted = grp.sort_values("LapNumber").reset_index(drop=True)
            if len(grp_sorted) < 5:
                continue  # skip extremely short stints (DNFs with < 5 laps)
            # Store reference time in DataFrame.attrs
            year_track = key[:2] if len(key) >= 2 else key
            grp_sorted.attrs["season_median_race_time"] = medians.get(
                year_track, grp_sorted["LapTime"].sum() if "LapTime" in grp_sorted else 5400.0
            )
            episodes[key] = grp_sorted

        if not episodes:
            raise ValueError(
                "No valid driver episodes found in the processed data. "
                "Ensure the parquet contains Year, Track, DriverNumber, and LapNumber columns."
            )

        return episodes

    @property
    def n_episodes(self) -> int:
        """Number of unique (race, driver) episodes available."""
        return len(self._race_episodes)

    @property
    def current_episode_key(self) -> tuple:
        """Identity of the current episode: (Year, Track, DriverNumber)."""
        return self._episode_key
