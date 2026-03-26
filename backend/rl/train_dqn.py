"""
train_dqn.py — Phase 4 DQN training using Stable-Baselines3.

"Framed pit strategy as a sequential decision problem with delayed rewards."

Usage:
    # Multi-track (default — train on all episodes across 2022-2024)
    python rl/train_dqn.py

    # Per-track mode (train a separate agent for one circuit)
    python rl/train_dqn.py --track "Bahrain Grand Prix" --year 2023

    # Resume training from a saved model
    python rl/train_dqn.py --resume rl/models/dqn_f1_pit.zip

TensorBoard logs:
    tensorboard --logdir outputs/tensorboard/
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
from stable_baselines3 import DQN
from stable_baselines3.common.callbacks import (
    BaseCallback,
    CheckpointCallback,
    EvalCallback,
)
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import DummyVecEnv

from envs.f1_pit_env import F1PitEnv
from src.config import PROCESSED_PARQUET

# ── Output paths ──────────────────────────────────────────────────────────────
MODELS_DIR = ROOT / "rl" / "models"
TB_LOG_DIR = ROOT / "outputs" / "tensorboard"
MODELS_DIR.mkdir(parents=True, exist_ok=True)
TB_LOG_DIR.mkdir(parents=True, exist_ok=True)

# ── Training hyperparameters ──────────────────────────────────────────────────
# Tuned conservatively for the small F1 state space (5D obs, 2 actions).
HYPERPARAMS = {
    "learning_rate": 1e-4,
    "buffer_size": 50_000,
    "learning_starts": 1_000,
    "batch_size": 256,
    "tau": 1.0,                # hard target network update
    "gamma": 0.99,             # high discount — race outcomes are highly delayed
    "train_freq": 4,
    "gradient_steps": 1,
    "target_update_interval": 500,
    "exploration_fraction": 0.3,
    "exploration_initial_eps": 1.0,
    "exploration_final_eps": 0.05,
    "policy_kwargs": {
        "net_arch": [128, 128],  # two hidden layers; sufficient for 5D input
    },
    "verbose": 1,
}


# ── Custom logging callback ───────────────────────────────────────────────────

class PitStrategyCallback(BaseCallback):
    """
    Logs per-episode strategy consistency and reward to TensorBoard.

    Metrics logged every `log_freq` episodes:
      - train/ep_reward_mean      — average episode cumulative reward
      - train/pit_stop_rate       — fraction of laps where agent chose to pit
      - train/strategy_consistent — ratio of episodes where agent pitted 1-3×
                                    (realistic F1 strategies)
    """

    def __init__(self, log_freq: int = 100, verbose: int = 0) -> None:
        super().__init__(verbose)
        self.log_freq = log_freq
        self._episode_rewards: list[float] = []
        self._episode_pit_counts: list[int] = []
        self._episode_lengths: list[int] = []
        self._n_episodes = 0
        self._n_pits_this_ep = 0

    def _on_step(self) -> bool:
        # Accumulate info from each environment step
        for info in self.locals.get("infos", []):
            if info.get("pit_stop_taken"):
                self._n_pits_this_ep += 1

        # Detect episode boundaries via the done flag
        dones = self.locals.get("dones", [])
        rewards = self.locals.get("rewards", [])
        for done, reward in zip(dones, rewards):
            if done:
                self._episode_pit_counts.append(self._n_pits_this_ep)
                self._n_pits_this_ep = 0
                self._n_episodes += 1

        if self._n_episodes > 0 and self._n_episodes % self.log_freq == 0:
            self._flush_logs()

        return True

    def _flush_logs(self) -> None:
        if not self._episode_pit_counts:
            return

        # Episode reward comes from SB3 Monitor wrapper
        monitor_data = self.training_env.get_attr("get_episode_rewards")
        try:
            ep_rewards = self.training_env.get_attr("get_episode_rewards")[0]()
        except Exception:
            ep_rewards = []

        # Strategy consistency: % of episodes with 1-3 pit stops (realistic F1)
        counts = np.array(self._episode_pit_counts[-self.log_freq:])
        consistent = float(np.mean((counts >= 1) & (counts <= 3)))
        pit_rate = float(np.mean(counts))

        self.logger.record("train/pit_stop_rate", pit_rate)
        self.logger.record("train/strategy_consistent_pct", consistent * 100)
        self.logger.record("train/n_episodes", self._n_episodes)
        self.logger.dump(self.num_timesteps)

        if self.verbose:
            print(
                f"  [ep {self._n_episodes:>5}] "
                f"pit_rate={pit_rate:.2f}  "
                f"consistent={consistent:.1%}"
            )


# ── Environment factory ───────────────────────────────────────────────────────

def _make_env(
    data_path: Path,
    track_filter: str | None = None,
    year_filter: int | None = None,
    seed: int = 0,
) -> F1PitEnv:
    """
    Create a monitored F1PitEnv, optionally filtered to a single track/year.

    For per-track training the environment only samples episodes from the
    specified Grand Prix, giving the agent more focused experience.
    """
    env = F1PitEnv(data_path=data_path, seed=seed)

    # Per-track filtering: remove episodes that don't match the filter
    if track_filter or year_filter:
        filtered = {}
        for key, ep in env._race_episodes.items():
            year, track, driver = key
            if track_filter and track_filter.lower() not in track.lower():
                continue
            if year_filter and year != year_filter:
                continue
            filtered[key] = ep

        if not filtered:
            raise ValueError(
                f"No episodes found for track='{track_filter}' year={year_filter}. "
                f"Available tracks: {sorted({k[1] for k in env._race_episodes})}"
            )
        env._race_episodes = filtered
        print(f"  Per-track mode: {len(filtered)} episodes "
              f"({track_filter or 'all'}, {year_filter or 'all years'})")

    return Monitor(env)


# ── Main training routine ─────────────────────────────────────────────────────

def train(
    total_timesteps: int = 300_000,
    track_filter: str | None = None,
    year_filter: int | None = None,
    resume_path: str | None = None,
    data_path: Path | None = None,
    seed: int = 42,
) -> DQN:
    """
    Train a DQN agent on the F1PitEnv.

    Parameters
    ----------
    total_timesteps : int
        Total environment interactions. 300k is fast (~2-3 min on CPU) and
        sufficient to learn a reasonable pit strategy baseline.
    track_filter : str or None
        If given, restrict training episodes to circuits whose name contains
        this substring (case-insensitive).
    year_filter : int or None
        If given, restrict training to a single championship year.
    resume_path : str or None
        Path to a .zip model to resume training from.
    seed : int
        Global random seed.
    data_path : Path or None
        Override the default processed parquet path.
    """
    data_path = data_path or PROCESSED_PARQUET
    model_tag = f"dqn_f1_pit{'_' + track_filter.replace(' ', '_') if track_filter else ''}"
    save_path = MODELS_DIR / model_tag

    print(f"\n{'='*60}")
    print(f"  F1 Pitstop RL — DQN Training (Phase 4)")
    print(f"  Timesteps    : {total_timesteps:,}")
    print(f"  Track filter : {track_filter or 'multi-track (all circuits)'}")
    print(f"  Year filter  : {year_filter or 'all years (2022–2024)'}")
    print(f"  Model output : {save_path}.zip")
    print(f"  TensorBoard  : tensorboard --logdir {TB_LOG_DIR}")
    print(f"{'='*60}\n")

    # ── Build vectorised training + eval environments ─────────────────────────
    train_env = DummyVecEnv([
        lambda: _make_env(data_path, track_filter, year_filter, seed=seed + i)
        for i in range(1)  # single env — DQN is off-policy, parallelism has little benefit
    ])

    eval_env = _make_env(data_path, track_filter, year_filter, seed=seed + 99)

    # ── Callbacks ─────────────────────────────────────────────────────────────
    checkpoint_cb = CheckpointCallback(
        save_freq=50_000,
        save_path=str(MODELS_DIR),
        name_prefix=model_tag,
        verbose=1,
    )

    eval_cb = EvalCallback(
        eval_env,
        best_model_save_path=str(MODELS_DIR),
        log_path=str(MODELS_DIR),
        eval_freq=25_000,
        n_eval_episodes=10,
        deterministic=True,
        verbose=1,
    )

    strategy_cb = PitStrategyCallback(log_freq=50, verbose=1)

    # ── Model init or resume ──────────────────────────────────────────────────
    if resume_path:
        print(f"Resuming from: {resume_path}")
        model = DQN.load(
            resume_path,
            env=train_env,
            tensorboard_log=str(TB_LOG_DIR),
        )
    else:
        model = DQN(
            policy="MlpPolicy",
            env=train_env,
            tensorboard_log=str(TB_LOG_DIR),
            seed=seed,
            **HYPERPARAMS,
        )

    # ── Train ─────────────────────────────────────────────────────────────────
    t0 = time.time()
    model.learn(
        total_timesteps=total_timesteps,
        callback=[checkpoint_cb, eval_cb, strategy_cb],
        tb_log_name=model_tag,
        reset_num_timesteps=resume_path is None,
        progress_bar=True,
    )
    elapsed = time.time() - t0

    model.save(str(save_path))
    print(f"\n  Training complete in {elapsed:.1f}s")
    print(f"  Model saved → {save_path}.zip\n")
    return model


# ── CLI ───────────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Train DQN for F1 pit stop strategy")
    p.add_argument("--timesteps", type=int, default=300_000,
                   help="Total training timesteps (default: 300,000)")
    p.add_argument("--track", type=str, default=None,
                   help="Filter to a specific circuit, e.g. 'Bahrain'")
    p.add_argument("--year", type=int, default=None,
                   help="Filter to a specific season year, e.g. 2023")
    p.add_argument("--resume", type=str, default=None,
                   help="Path to a .zip model to resume training from")
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    train(
        total_timesteps=args.timesteps,
        track_filter=args.track,
        year_filter=args.year,
        resume_path=args.resume,
        seed=args.seed,
    )
