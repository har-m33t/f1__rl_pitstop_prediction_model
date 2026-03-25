"""
test_f1_pit_env.py — Smoke tests for the F1PitEnv gymnasium environment.

All tests are self-contained: they build a minimal synthetic DataFrame
so no FastF1 API calls or ingested parquet files are needed.
"""

from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ── Synthetic episode factory ─────────────────────────────────────────────────

def _make_parquet(tmp_path: Path, n_laps: int = 30) -> Path:
    """
    Write a minimal fake parquet that F1PitEnv._load_episodes can consume.
    Two drivers, one race, n_laps each.
    """
    rng = np.random.default_rng(0)
    records = []
    for driver in [44, 1]:
        for lap in range(1, n_laps + 1):
            records.append(
                {
                    "Year": 2023,
                    "Track": "TestCircuit",
                    "DriverNumber": driver,
                    "LapNumber": lap,
                    "LapTime": 90.0 + lap * 0.1 + rng.normal(0, 0.05),
                    "TyreLife": float(lap),
                    "tire_age": float(lap),
                    "degradation_slope": lap * 0.02,
                    "track_temp": 35.0,
                    "track_temp_is_proxy": 0,
                    "safety_car_flag": 1 if lap == 10 else 0,
                    "PitInTime": 95.0 if lap == 15 else None,
                    "Stint": 1 if lap < 15 else 2,
                    "_raw_tire_age": float(lap),
                }
            )
    df = pd.DataFrame(records)
    path = tmp_path / "laps_processed.parquet"
    df.to_parquet(path, index=False)
    return path


class TestF1PitEnvSyntheticData(unittest.TestCase):
    """Tests that use an in-memory synthetic parquet (no FastF1 needed)."""

    @classmethod
    def setUpClass(cls):
        import tempfile
        cls._tmpdir = tempfile.mkdtemp()
        cls._parquet = _make_parquet(Path(cls._tmpdir))

        from envs.f1_pit_env import F1PitEnv
        cls.env = F1PitEnv(data_path=cls._parquet, seed=42)

    # ── Interface compliance ──────────────────────────────────────────────────

    def test_observation_space_shape(self):
        obs, _ = self.env.reset()
        self.assertEqual(obs.shape, (5,))

    def test_observation_dtype_float32(self):
        obs, _ = self.env.reset()
        self.assertEqual(obs.dtype, np.float32)

    def test_observation_in_bounds(self):
        obs, _ = self.env.reset()
        self.assertTrue((obs >= 0.0).all(), "obs below 0")
        self.assertTrue((obs <= 1.0).all(), "obs above 1")

    def test_action_space_is_discrete_2(self):
        from envs.f1_pit_env import F1PitEnv
        env = F1PitEnv(data_path=self._parquet, seed=0)
        self.assertEqual(env.action_space.n, 2)

    def test_step_returns_correct_types(self):
        env = self.env
        env.reset()
        obs, reward, terminated, truncated, info = env.step(0)
        self.assertIsInstance(obs, np.ndarray)
        self.assertIsInstance(reward, float)
        self.assertIsInstance(terminated, bool)
        self.assertIsInstance(truncated, bool)
        self.assertIsInstance(info, dict)

    # ── Episode mechanics ─────────────────────────────────────────────────────

    def test_episode_runs_to_completion(self):
        """Agent can step through an entire episode without errors."""
        from envs.f1_pit_env import F1PitEnv
        env = F1PitEnv(data_path=self._parquet, seed=1)
        obs, _ = env.reset()
        terminated = False
        steps = 0
        while not terminated:
            obs, r, terminated, _, info = env.step(env.action_space.sample())
            steps += 1
        self.assertGreater(steps, 0)

    def test_pit_action_resets_tire_age(self):
        """Action=1 should reset tire age to 0 (then +1 for the lap)."""
        from envs.f1_pit_env import F1PitEnv
        env = F1PitEnv(data_path=self._parquet, seed=2)
        env.reset()
        # Advance a few laps without pitting
        for _ in range(5):
            env.step(0)
        pre_pit_age = env._current_tire_age
        self.assertGreater(pre_pit_age, 1.0)  # tyres are worn
        # Pit
        env.step(1)
        self.assertAlmostEqual(env._current_tire_age, 1.0, places=1)

    def test_stay_out_increments_tire_age(self):
        """Action=0 should increment tire age by 1 each lap."""
        from envs.f1_pit_env import F1PitEnv
        env = F1PitEnv(data_path=self._parquet, seed=3)
        env.reset()
        env.step(0)
        age_after_1 = env._current_tire_age
        env.step(0)
        age_after_2 = env._current_tire_age
        self.assertAlmostEqual(age_after_2 - age_after_1, 1.0)

    def test_negative_reward_on_stay_out(self):
        """Staying out produces negative reward (−lap_time)."""
        from envs.f1_pit_env import F1PitEnv
        env = F1PitEnv(data_path=self._parquet, seed=4)
        env.reset()
        _, reward, _, _, _ = env.step(0)
        self.assertLess(reward, 0.0)

    def test_pit_action_larger_penalty(self):
        """Pitting should produce a more negative reward than staying out."""
        from envs.f1_pit_env import F1PitEnv
        env_pit = F1PitEnv(data_path=self._parquet, seed=5)
        env_stay = F1PitEnv(data_path=self._parquet, seed=5)

        obs_pit, _ = env_pit.reset(seed=5)
        obs_stay, _ = env_stay.reset(seed=5)

        _, r_stay, _, _, _ = env_stay.step(0)
        _, r_pit, _, _, _ = env_pit.step(1)
        self.assertLess(r_pit, r_stay, "Pit should have larger penalty than stay-out")

    def test_safety_car_flag_in_obs(self):
        """Safety car flag (obs[4]) should be 1 on the SC lap."""
        from envs.f1_pit_env import F1PitEnv
        env = F1PitEnv(data_path=self._parquet, seed=6)
        env.reset()
        # Step through until safety car lap (lap 10)
        sc_flags = []
        for _ in range(12):
            obs, _, terminated, _, _ = env.step(0)
            sc_flags.append(obs[4])
            if terminated:
                break
        self.assertIn(1.0, sc_flags, "Safety car flag never activated")

    def test_n_episodes_positive(self):
        self.assertGreater(self.env.n_episodes, 0)

    def test_max_stints_respected(self):
        """Agent should not accumulate more pit stops than max_stints."""
        from envs.f1_pit_env import F1PitEnv
        env = F1PitEnv(data_path=self._parquet, seed=7, max_stints=2)
        env.reset()
        terminated = False
        while not terminated:
            _, _, terminated, _, info = env.step(1)  # pit every lap
        self.assertLessEqual(info["n_pits_total"], 2)

    def test_render_does_not_crash(self):
        from envs.f1_pit_env import F1PitEnv
        env = F1PitEnv(data_path=self._parquet, seed=8)
        env.reset()
        env.step(0)
        env.render()  # Should not raise


if __name__ == "__main__":
    unittest.main()
