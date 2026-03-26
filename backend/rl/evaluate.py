"""
evaluate.py — Phase 4 evaluation: RL agent vs heuristic vs ML baseline.

"Framed pit strategy as a sequential decision problem with delayed rewards."

Usage:
    # Full comparison on all 2024 episodes
    python rl/evaluate.py --model rl/models/dqn_f1_pit.zip

    # Restrict to a specific track for analysis
    python rl/evaluate.py --model rl/models/dqn_f1_pit.zip --track "Bahrain"

Output:
    - Console table: Avg Reward / Avg Race Time / Win-Rate per agent
    - outputs/evaluation_results.csv
    - outputs/evaluation_comparison.png (bar chart)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from stable_baselines3 import DQN

from envs.f1_pit_env import F1PitEnv, PIT_PENALTY_SECONDS
from src.config import PROCESSED_PARQUET

OUTPUTS_DIR = ROOT / "outputs"
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

# ── Agent type alias ──────────────────────────────────────────────────────────
# Any callable: obs (np.ndarray) -> action (int)
PolicyFn = Callable[[np.ndarray], int]


# ── Built-in heuristic agents ─────────────────────────────────────────────────

def heuristic_fixed_interval(obs: np.ndarray, interval: int = 20) -> int:
    """
    Pit every `interval` laps regardless of tyre state.

    Baseline: mirrors a naive fixed-interval strategy teams sometimes use
    as a fallback when telemetry is unavailable.

    obs[1] = normalised tire_age (0→1 mapped over 0–50 laps).
    We convert back to raw laps: tire_age_raw = obs[1] * 50.
    """
    tire_age_raw = obs[1] * 50.0
    return 1 if (tire_age_raw > 0 and tire_age_raw % interval < 1) else 0


def heuristic_degradation_threshold(obs: np.ndarray) -> int:
    """
    Pit when degradation_rate (obs[2]) exceeds 0.6 normalised (≈ 2.4 s/lap raw).

    Mirrors a simple telemetry-triggered strategy: pit once pace loss crosses
    a threshold. Also exploits safety car periods (obs[4] == 1).
    """
    deg_rate = obs[2]   # normalised [0,1]; 0.6 ≈ 2.4 s/lap raw
    sc_flag = obs[4]
    if sc_flag == 1.0:
        return 1         # always pit under safety car (free stop)
    return 1 if deg_rate > 0.60 else 0


# ── Rollout engine ────────────────────────────────────────────────────────────

def run_episode(env: F1PitEnv, policy: PolicyFn) -> dict:
    """
    Roll out one episode with the given policy.

    Returns
    -------
    dict with keys: total_reward, race_time, n_pits, episode_key
    """
    obs, info = env.reset()
    total_reward = 0.0
    terminated = False

    while not terminated:
        action = policy(obs)
        obs, reward, terminated, _, info = env.step(int(action))
        total_reward += reward

    return {
        "total_reward": total_reward,
        "race_time": info.get("race_time_so_far", float("nan")),
        "n_pits": info.get("n_pits_total", 0),
        "episode_key": str(env.current_episode_key),
    }


def evaluate_agent(
    name: str,
    policy: PolicyFn,
    env: F1PitEnv,
    n_episodes: int,
    seed_offset: int = 0,
) -> pd.DataFrame:
    """
    Run `n_episodes` episodes and return a DataFrame of per-episode results.
    """
    results = []
    for i in range(n_episodes):
        env._rng = np.random.default_rng(seed_offset + i)
        ep = run_episode(env, policy)
        ep["agent"] = name
        results.append(ep)
    return pd.DataFrame(results)


# ── Summary statistics ────────────────────────────────────────────────────────

def _summary(df: pd.DataFrame) -> dict:
    return {
        "avg_reward": df["total_reward"].mean(),
        "avg_race_time": df["race_time"].mean(),
        "std_reward": df["total_reward"].std(),
        "avg_n_pits": df["n_pits"].mean(),
    }


def compute_win_rate(
    all_results: dict[str, pd.DataFrame],
    n_episodes: int,
) -> dict[str, float]:
    """
    Win-rate: fraction of episodes where this agent had the highest reward.

    Requires all agents to have been evaluated on the same episode ordering
    (same seed sequence), so results can be compared episode-by-episode.
    """
    agents = list(all_results.keys())
    n = min(len(df) for df in all_results.values())
    rewards_matrix = np.stack(
        [all_results[a]["total_reward"].values[:n] for a in agents], axis=1
    )  # shape: (n_episodes, n_agents)

    winners = np.argmax(rewards_matrix, axis=1)  # index of best agent per episode
    win_counts = {a: int(np.sum(winners == i)) for i, a in enumerate(agents)}
    win_rates = {a: c / n for a, c in win_counts.items()}
    return win_rates


# ── Plot ──────────────────────────────────────────────────────────────────────

def _plot_comparison(
    summaries: dict[str, dict],
    win_rates: dict[str, float],
    out_path: Path = OUTPUTS_DIR / "evaluation_comparison.png",
) -> None:
    agents = list(summaries.keys())
    colors = ["#e63946", "#457b9d", "#2a9d8f", "#f4a261"][:len(agents)]

    fig, axes = plt.subplots(1, 3, figsize=(14, 5))
    fig.suptitle("F1 Pit Stop Strategy — Agent Comparison (2024 Holdout)",
                 fontsize=13, fontweight="bold")

    metrics = [
        ("avg_reward",    "Avg Episode Reward",    "Higher is better  ▲"),
        ("avg_race_time", "Avg Race Time (s)",      "Lower is better   ▼"),
    ]

    for ax, (metric, title, hint) in zip(axes[:2], metrics):
        vals = [summaries[a][metric] for a in agents]
        bars = ax.bar(agents, vals, color=colors, edgecolor="white", width=0.5)
        for bar, v in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() * 1.01,
                    f"{v:.1f}", ha="center", va="bottom", fontsize=9)
        ax.set_title(title, fontsize=10)
        ax.set_xlabel("")
        ax.text(0.98, 0.98, hint, transform=ax.transAxes,
                ha="right", va="top", fontsize=8, color="gray")
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(axis="x", labelrotation=15)

    # Win-rate axis
    ax = axes[2]
    wr_vals = [win_rates.get(a, 0.0) * 100 for a in agents]
    bars = ax.bar(agents, wr_vals, color=colors, edgecolor="white", width=0.5)
    for bar, v in zip(bars, wr_vals):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                f"{v:.1f}%", ha="center", va="bottom", fontsize=9)
    ax.set_title("Win-Rate (% of episodes)", fontsize=10)
    ax.set_ylim(0, 105)
    ax.text(0.98, 0.98, "Higher is better  ▲", transform=ax.transAxes,
            ha="right", va="top", fontsize=8, color="gray")
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(axis="x", labelrotation=15)

    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Chart saved → {out_path}")


# ── Main ──────────────────────────────────────────────────────────────────────

def evaluate(
    model_path: str,
    n_episodes: int = 50,
    track_filter: str | None = None,
    year_filter: int | None = None,
    data_path: Path | None = None,
    seed: int = 0,
) -> pd.DataFrame:
    """
    Compare the trained DQN against two heuristics and (optionally) the
    ML baseline on `n_episodes` episodes.

    Parameters
    ----------
    model_path : str
        Path to the saved DQN .zip file.
    n_episodes : int
        Episodes to evaluate per agent (same seed sequence for fair comparison).
    track_filter : str or None
        Restrict evaluation to circuits containing this substring.
    year_filter : int or None
        Restrict evaluation to episodes from this season.
    data_path : Path or None
        Override default processed parquet location.
    seed : int
        Global random seed for reproducibility.

    Returns
    -------
    pd.DataFrame
        Full per-episode results for all agents.
    """
    data_path = data_path or PROCESSED_PARQUET

    print(f"\n{'='*60}")
    print(f"  F1 Pitstop RL — Agent Evaluation (Phase 4)")
    print(f"  Model        : {model_path}")
    print(f"  Episodes     : {n_episodes}")
    print(f"  Track filter : {track_filter or 'all circuits'}")
    print(f"  Year filter  : {year_filter or '2024 holdout (default)'}")
    print(f"{'='*60}\n")

    # ── Build shared evaluation environment ───────────────────────────────────
    eval_year = year_filter or 2024
    env = F1PitEnv(data_path=data_path, seed=seed)

    # Filter to eval year/track
    filtered = {
        k: v for k, v in env._race_episodes.items()
        if k[0] == eval_year
        and (not track_filter or track_filter.lower() in k[1].lower())
    }
    if not filtered:
        print(f"  ⚠ No episodes found for year={eval_year} track={track_filter}.")
        print(f"    Falling back to all available episodes.")
        filtered = env._race_episodes

    env._race_episodes = filtered
    n_available = len(filtered)
    print(f"  Evaluating on {n_available} unique race-driver episodes\n")

    # ── Load DQN ──────────────────────────────────────────────────────────────
    model = DQN.load(model_path)

    def dqn_policy(obs: np.ndarray) -> int:
        action, _ = model.predict(obs, deterministic=True)
        return int(action)

    # ── Define all agents ─────────────────────────────────────────────────────
    agents: dict[str, PolicyFn] = {
        "DQN Agent":            dqn_policy,
        "Heuristic (Fixed)":    heuristic_fixed_interval,
        "Heuristic (Deg Thr)":  heuristic_degradation_threshold,
        "Random":               lambda _: int(np.random.default_rng(seed).integers(2)),
    }

    # ── Run rollouts ──────────────────────────────────────────────────────────
    all_dfs: dict[str, pd.DataFrame] = {}
    for name, policy in agents.items():
        print(f"  Evaluating: {name} …")
        df = evaluate_agent(name, policy, env, n_episodes=n_episodes, seed_offset=seed)
        all_dfs[name] = df

    # ── Compute summaries + win rates ─────────────────────────────────────────
    summaries = {name: _summary(df) for name, df in all_dfs.items()}
    win_rates = compute_win_rate(all_dfs, n_episodes)

    # ── Print results table ───────────────────────────────────────────────────
    print(f"\n{'─'*65}")
    print(f"  {'Agent':<25} {'Avg Reward':>10} {'Avg Race(s)':>12} {'Win%':>7} {'Avg Pits':>9}")
    print(f"{'─'*65}")
    for name in agents:
        s = summaries[name]
        wr = win_rates.get(name, 0.0)
        print(
            f"  {name:<25} {s['avg_reward']:>10.1f} "
            f"{s['avg_race_time']:>12.1f} "
            f"{wr*100:>6.1f}% "
            f"{s['avg_n_pits']:>8.2f}"
        )
    print(f"{'─'*65}\n")

    # ── Save outputs ──────────────────────────────────────────────────────────
    combined = pd.concat(all_dfs.values(), ignore_index=True)
    csv_path = OUTPUTS_DIR / "evaluation_results.csv"
    combined.to_csv(csv_path, index=False)
    print(f"  Results saved → {csv_path}")

    _plot_comparison(summaries, win_rates)

    return combined


# ── CLI ───────────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Evaluate DQN vs heuristics for F1 pit strategy")
    p.add_argument("--model", type=str, required=True,
                   help="Path to trained DQN .zip file")
    p.add_argument("--episodes", type=int, default=50,
                   help="Number of evaluation episodes per agent (default: 50)")
    p.add_argument("--track", type=str, default=None,
                   help="Restrict evaluation to circuits containing this string")
    p.add_argument("--year", type=int, default=2024,
                   help="Evaluation season year (default: 2024, the holdout year)")
    p.add_argument("--seed", type=int, default=0)
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    evaluate(
        model_path=args.model,
        n_episodes=args.episodes,
        track_filter=args.track,
        year_filter=args.year,
        seed=args.seed,
    )
