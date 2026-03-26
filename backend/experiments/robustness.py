"""
robustness.py — Phase 5: Uncertainty & What-If Analysis

Mirrors real production ML validation: a deterministic model trained on
clean data must still perform when the world adds noise.

Three noise sources are injected into the F1PitEnv:
  1. sc_prob       — random safety car periods (probability per lap)
  2. temp_drift    — temperature drifts ±N degrees across a race
  3. tire_variance — random lap-to-lap tire wear variation

Usage:
    # Run full stress test (requires a trained model)
    python experiments/robustness.py --model rl/models/dqn_f1_pit.zip

    # Sweep a single noise parameter
    python experiments/robustness.py --model rl/models/dqn_f1_pit.zip --sweep sc_prob

Outputs:
    outputs/robustness_results.csv
    outputs/robustness_stress_test.png
    outputs/robustness_sweep_<param>.png
"""

from __future__ import annotations

import argparse
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from envs.f1_pit_env import F1PitEnv
from src.config import PROCESSED_PARQUET

OUTPUTS_DIR = ROOT / "outputs"
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

# ── Noise configuration defaults ──────────────────────────────────────────────
DEFAULT_NOISE = {
    "sc_prob": 0.0,        # probability of spontaneous SC per lap
    "temp_drift": 0.0,     # std dev of temperature random walk per lap (°C)
    "tire_variance": 0.0,  # std dev of additive tire-age noise per lap (laps)
}

NOISE_SWEEP_VALUES = {
    "sc_prob":       [0.0, 0.02, 0.05, 0.10, 0.15, 0.20],
    "temp_drift":    [0.0, 0.5,  1.0,  2.0,  4.0,  6.0],
    "tire_variance": [0.0, 0.25, 0.5,  1.0,  2.0,  3.0],
}

NOISE_LABELS = {
    "sc_prob":       "SC Probability per Lap",
    "temp_drift":    "Temp Drift Std Dev (°C/lap)",
    "tire_variance": "Tire Wear Std Dev (laps)",
}


# ── Stochastic environment wrapper ────────────────────────────────────────────

class StochasticF1PitEnv(F1PitEnv):
    """
    Extends F1PitEnv with configurable noise injection.

    Each noise channel independently perturbs the observation vector at
    every step, simulating real-world uncertainty in sensor readings and
    race conditions.

    Parameters
    ----------
    sc_prob : float
        Probability [0,1] that a safety car appears on any given lap,
        overriding the historical TrackStatus from the data.
    temp_drift : float
        Standard deviation (°C per lap) of a Gaussian random walk applied
        to track_temp. Simulates changing weather conditions.
    tire_variance : float
        Standard deviation (laps) of zero-mean Gaussian noise added to
        tire_age before normalisation. Simulates sensor imprecision.
    """

    def __init__(
        self,
        *args,
        sc_prob: float = 0.0,
        temp_drift: float = 0.0,
        tire_variance: float = 0.0,
        noise_seed: int = 0,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.sc_prob = sc_prob
        self.temp_drift = temp_drift
        self.tire_variance = tire_variance
        self._noise_rng = np.random.default_rng(noise_seed)
        self._temp_offset: float = 0.0   # running temperature drift

    def reset(self, **kwargs):
        obs, info = super().reset(**kwargs)
        self._temp_offset = 0.0
        return self._add_noise(obs), info

    def step(self, action: int):
        obs, reward, terminated, truncated, info = super().step(action)
        return self._add_noise(obs), reward, terminated, truncated, info

    def _add_noise(self, obs: np.ndarray) -> np.ndarray:
        obs = obs.copy()

        # 1. Random safety car injection (obs[4])
        if self.sc_prob > 0 and self._noise_rng.random() < self.sc_prob:
            obs[4] = 1.0   # force SC flag on

        # 2. Temperature drift (obs[3])
        if self.temp_drift > 0:
            self._temp_offset += float(
                self._noise_rng.normal(0, self.temp_drift)
            )
            # Normalised drift in the [15, 65] °C window (range = 50 °C)
            obs[3] = float(np.clip(obs[3] + self._temp_offset / 50.0, 0.0, 1.0))

        # 3. Tire wear variance (obs[1])
        if self.tire_variance > 0:
            noise_norm = float(self._noise_rng.normal(0, self.tire_variance)) / 50.0
            obs[1] = float(np.clip(obs[1] + noise_norm, 0.0, 1.0))

        return obs.astype(np.float32)


# ── Rollout helpers ───────────────────────────────────────────────────────────

def _rollout(env: F1PitEnv, policy, n_episodes: int, seed_offset: int = 0) -> list[dict]:
    results = []
    for i in range(n_episodes):
        env._rng = np.random.default_rng(seed_offset + i)
        obs, info = env.reset()
        total_reward = 0.0
        terminated = False
        n_pits = 0
        while not terminated:
            action = policy(obs)
            obs, reward, terminated, _, info = env.step(int(action))
            total_reward += reward
            if info.get("pit_stop_taken"):
                n_pits += 1
        results.append({
            "total_reward": total_reward,
            "race_time": info.get("race_time_so_far", float("nan")),
            "n_pits": n_pits,
        })
    return results


def _summarise(results: list[dict]) -> dict:
    rewards = np.array([r["total_reward"] for r in results])
    times   = np.array([r["race_time"]    for r in results])
    return {
        "mean_reward": float(np.mean(rewards)),
        "std_reward":  float(np.std(rewards)),
        "mean_time":   float(np.mean(times)),
        "mean_pits":   float(np.mean([r["n_pits"] for r in results])),
    }


# ── Stress test: deterministic vs all noise ───────────────────────────────────

def stress_test(
    dqn_policy,
    data_path: Path,
    n_episodes: int = 40,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Compare the DQN on clean vs maximally noisy environments.

    Conditions tested:
      - Deterministic (no noise)
      - High SC probability  (sc_prob=0.10)
      - Heavy temp drift     (temp_drift=3.0 °C/lap)
      - High tire variance   (tire_variance=2.0 laps)
      - All noise combined

    Returns a DataFrame with mean_reward / std_reward / mean_time per condition.
    """
    conditions = {
        "Deterministic":       dict(sc_prob=0.00, temp_drift=0.0, tire_variance=0.0),
        "+ SC noise":          dict(sc_prob=0.10, temp_drift=0.0, tire_variance=0.0),
        "+ Temp drift":        dict(sc_prob=0.00, temp_drift=3.0, tire_variance=0.0),
        "+ Tire variance":     dict(sc_prob=0.00, temp_drift=0.0, tire_variance=2.0),
        "All noise combined":  dict(sc_prob=0.10, temp_drift=3.0, tire_variance=2.0),
    }

    rows = []
    for cond_name, noise_kwargs in conditions.items():
        env = StochasticF1PitEnv(
            data_path=data_path,
            seed=seed,
            noise_seed=seed + 1,
            **noise_kwargs,
        )
        results = _rollout(env, dqn_policy, n_episodes, seed_offset=seed)
        s = _summarise(results)
        s["condition"] = cond_name
        rows.append(s)
        print(
            f"  {cond_name:<22} reward={s['mean_reward']:>8.1f}±{s['std_reward']:.1f}"
            f"  time={s['mean_time']:>8.1f}s  pits={s['mean_pits']:.2f}"
        )

    return pd.DataFrame(rows)


# ── Parameter sweep ───────────────────────────────────────────────────────────

def noise_sweep(
    param: str,
    dqn_policy,
    data_path: Path,
    n_episodes: int = 30,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Sweep one noise parameter across its full range and measure reward degradation.

    Returns a DataFrame indexed by the swept parameter value.
    """
    assert param in NOISE_SWEEP_VALUES, f"Unknown parameter: {param}"
    values = NOISE_SWEEP_VALUES[param]

    rows = []
    for v in values:
        kwargs = {**DEFAULT_NOISE, param: v}
        env = StochasticF1PitEnv(
            data_path=data_path, seed=seed, noise_seed=seed + 2, **kwargs
        )
        results = _rollout(env, dqn_policy, n_episodes, seed_offset=seed)
        s = _summarise(results)
        s[param] = v
        rows.append(s)
        print(f"  {param}={v:.3f}  reward={s['mean_reward']:>8.1f}±{s['std_reward']:.1f}")

    return pd.DataFrame(rows)


# ── Plotting ──────────────────────────────────────────────────────────────────

def _plot_stress_test(df: pd.DataFrame, out: Path) -> None:
    conditions = df["condition"].tolist()
    rewards    = df["mean_reward"].tolist()
    errors     = df["std_reward"].tolist()

    colors = ["#2a9d8f"] + ["#e76f51"] * (len(conditions) - 2) + ["#e63946"]

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.barh(conditions, rewards, xerr=errors, color=colors,
                   edgecolor="white", height=0.6,
                   error_kw=dict(elinewidth=1.2, capsize=4, ecolor="#555"))

    ax.axvline(rewards[0], color="#2a9d8f", linestyle="--", linewidth=1.2,
               label="Deterministic baseline")

    for bar, v in zip(bars, rewards):
        ax.text(v - 5, bar.get_y() + bar.get_height() / 2,
                f"{v:.0f}", va="center", ha="right", fontsize=9, color="white",
                fontweight="bold")

    ax.set_xlabel("Mean Episode Reward", fontsize=10)
    ax.set_title("Robustness Stress Test — DQN Under Noise\n"
                 "(lower reward = more degradation from noise)", fontsize=11)
    ax.legend(fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    plt.tight_layout()
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  → {out}")


def _plot_sweep(df: pd.DataFrame, param: str, out: Path) -> None:
    x   = df[param].tolist()
    y   = df["mean_reward"].tolist()
    err = df["std_reward"].tolist()

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(x, y, "o-", color="#457b9d", linewidth=2, markersize=6)
    ax.fill_between(
        x,
        [yi - ei for yi, ei in zip(y, err)],
        [yi + ei for yi, ei in zip(y, err)],
        alpha=0.2, color="#457b9d",
    )
    ax.axhline(y[0], color="#2a9d8f", linestyle="--", linewidth=1,
               label=f"No noise baseline (reward={y[0]:.0f})")

    ax.set_xlabel(NOISE_LABELS[param], fontsize=10)
    ax.set_ylabel("Mean Reward (±1 std)", fontsize=10)
    ax.set_title(f"Reward vs {NOISE_LABELS[param]}\n(DQN policy, deterministic inference)",
                 fontsize=11)
    ax.legend(fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    plt.tight_layout()
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  → {out}")


# ── Main ──────────────────────────────────────────────────────────────────────

def run(
    model_path: str | None,
    sweep_param: str | None = None,
    n_episodes: int = 40,
    data_path: Path | None = None,
    seed: int = 42,
) -> None:
    """
    Full robustness analysis pipeline.

    If no model_path is given, a random policy is used so the script can be
    run without a trained model (useful for testing the noise infrastructure).
    """
    data_path = data_path or PROCESSED_PARQUET

    print(f"\n{'='*60}")
    print(f"  F1 Pitstop RL — Robustness & Stress Test (Phase 5)")
    print(f"  Model     : {model_path or 'RANDOM POLICY (no model given)'}")
    print(f"  Episodes  : {n_episodes}")
    print(f"{'='*60}\n")

    # ── Build policy ──────────────────────────────────────────────────────────
    if model_path and Path(model_path).exists():
        from stable_baselines3 import DQN
        model = DQN.load(model_path)
        def policy(obs):
            action, _ = model.predict(obs, deterministic=True)
            return int(action)
    else:
        print("  ⚠  No model supplied — using random policy.\n")
        _rng = np.random.default_rng(seed)
        def policy(obs):
            return int(_rng.integers(2))

    # ── Stress test ───────────────────────────────────────────────────────────
    print("[1/2] Running stress test across noise conditions…")
    stress_df = stress_test(policy, data_path, n_episodes=n_episodes, seed=seed)

    stress_csv = OUTPUTS_DIR / "robustness_results.csv"
    stress_df.to_csv(stress_csv, index=False)
    print(f"\n  Results saved → {stress_csv}")

    _plot_stress_test(stress_df, OUTPUTS_DIR / "robustness_stress_test.png")

    # ── Noise sweep ───────────────────────────────────────────────────────────
    params_to_sweep = [sweep_param] if sweep_param else list(NOISE_SWEEP_VALUES)
    print(f"\n[2/2] Noise parameter sweeps: {params_to_sweep} …")

    for param in params_to_sweep:
        print(f"\n  Sweeping {param}…")
        sweep_df = noise_sweep(param, policy, data_path,
                               n_episodes=max(n_episodes // 2, 10), seed=seed)
        out_img = OUTPUTS_DIR / f"robustness_sweep_{param}.png"
        _plot_sweep(sweep_df, param, out_img)

    print("\n  Phase 5 complete.\n")


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="F1 RL robustness & noise stress test")
    p.add_argument("--model", type=str, default=None,
                   help="Path to DQN .zip (optional; uses random policy if omitted)")
    p.add_argument("--sweep", type=str, default=None,
                   choices=list(NOISE_SWEEP_VALUES),
                   help="Sweep a single noise parameter instead of all three")
    p.add_argument("--episodes", type=int, default=40)
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    run(
        model_path=args.model,
        sweep_param=args.sweep,
        n_episodes=args.episodes,
        seed=args.seed,
    )
