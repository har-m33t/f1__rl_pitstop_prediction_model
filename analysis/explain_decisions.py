"""
explain_decisions.py — Phase 6: DQN Explainability & Counterfactual Analysis

"Why did the agent pit on lap 23?"

This module answers that question three ways:
  1. Q-value logging  — raw neural network confidence per action at each lap
  2. Action preference plot — visualise pit vs stay-out preference across a race
  3. Counterfactuals — "If degradation were 10% lower, would it still pit?"

Usage (standalone script):
    python analysis/explain_decisions.py --model rl/models/dqn_f1_pit.zip

Usage (import):
    from analysis.explain_decisions import explain_episode, counterfactual_analysis
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import argparse
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
import pandas as pd

from envs.f1_pit_env import F1PitEnv, OBS_DEG_SLOPE_MAX, OBS_DEG_SLOPE_MIN
from src.config import PROCESSED_PARQUET

OUTPUTS_DIR = ROOT / "outputs"
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

# State index constants (mirrors f1_pit_env.py observation order)
IDX_LAP     = 0
IDX_TIRE    = 1
IDX_DEG     = 2
IDX_TEMP    = 3
IDX_SC      = 4

STATE_NAMES = ["lap_number", "tire_age", "degradation_rate", "track_temp", "safety_car_flag"]


# ── Q-value extraction ────────────────────────────────────────────────────────

def get_q_values(model, obs: np.ndarray) -> np.ndarray:
    """
    Extract raw Q-values [Q(stay_out), Q(pit)] from a trained SB3 DQN.

    The Q-network lives at model.policy.q_net. We pass a single observation
    through it as a float32 tensor and return the output as a numpy array.

    Returns
    -------
    np.ndarray of shape (2,): [Q_stay_out, Q_pit]
    """
    import torch
    with torch.no_grad():
        obs_t = torch.tensor(obs[None], dtype=torch.float32,
                             device=model.policy.q_net.device if
                             hasattr(model.policy.q_net, 'device') else 'cpu')
        q_vals = model.policy.q_net(obs_t).cpu().numpy()[0]
    return q_vals  # shape (2,)


# ── Full episode rollout with logging ─────────────────────────────────────────

def explain_episode(
    model,
    env: F1PitEnv,
    episode_seed: int = 0,
) -> pd.DataFrame:
    """
    Roll out one episode with the DQN, logging the full decision trace.

    Returns
    -------
    pd.DataFrame with columns:
        lap, tire_age_norm, degradation_norm, track_temp_norm, sc_flag,
        q_stay_out, q_pit, preferred_action, action_taken, pit_margin,
        explanation
    """
    env._rng = np.random.default_rng(episode_seed)
    obs, info = env.reset()

    rows = []
    lap = 1
    terminated = False

    while not terminated:
        q_vals = get_q_values(model, obs)
        q_stay, q_pit = float(q_vals[0]), float(q_vals[1])

        preferred = 1 if q_pit > q_stay else 0
        action, _ = model.predict(obs, deterministic=True)
        action = int(action)

        # Human-readable explanation
        explanation = _explain_lap(obs, q_stay, q_pit)

        rows.append({
            "lap":              lap,
            "tire_age_norm":    float(obs[IDX_TIRE]),
            "degradation_norm": float(obs[IDX_DEG]),
            "track_temp_norm":  float(obs[IDX_TEMP]),
            "sc_flag":          float(obs[IDX_SC]),
            "q_stay_out":       q_stay,
            "q_pit":            q_pit,
            "preferred_action": preferred,
            "action_taken":     action,
            "pit_margin":       q_pit - q_stay,   # positive = pit favoured
        })

        obs, _, terminated, _, info = env.step(action)
        lap += 1

    df = pd.DataFrame(rows)
    df["explanation"] = df.apply(
        lambda r: _explain_lap(
            np.array([r["tire_age_norm"], r["degradation_norm"],
                      r["track_temp_norm"], r["sc_flag"]]),
            r["q_stay_out"], r["q_pit"]
        ), axis=1
    )
    return df


def _explain_lap(obs, q_stay: float, q_pit: float) -> str:
    """Generate a one-line English explanation of why the agent prefers pit or stay."""
    reasons = []

    tire_raw = obs[IDX_TIRE] * 50              # denormalise to laps
    deg_raw  = obs[IDX_DEG] * (OBS_DEG_SLOPE_MAX - OBS_DEG_SLOPE_MIN) + OBS_DEG_SLOPE_MIN
    sc_on    = obs[IDX_SC] >= 0.5

    if q_pit > q_stay:
        if sc_on:
            reasons.append("SC active (free stop opportunity)")
        if deg_raw > 1.5:
            reasons.append(f"high degradation ({deg_raw:.2f} s/lap)")
        if tire_raw > 25:
            reasons.append(f"aged tyres ({tire_raw:.0f} laps)")
        label = "PIT favoured"
    else:
        reasons.append("tyres still viable")
        if not sc_on and tire_raw < 15:
            reasons.append(f"only {tire_raw:.0f} laps on current set")
        label = "STAY OUT favoured"

    reason_str = "; ".join(reasons) if reasons else "margin close"
    return f"{label} — {reason_str}  [ΔQ={q_pit - q_stay:+.3f}]"


# ── Action preference plot ────────────────────────────────────────────────────

def plot_action_preference(
    trace_df: pd.DataFrame,
    out: Path = OUTPUTS_DIR / "action_preference.png",
    episode_key: str = "",
) -> None:
    """
    3-panel figure showing:
      Top    — Q(pit) − Q(stay) margin across laps (positive = pit preferred)
      Middle — Degradation rate and safety car events
      Bottom — Tire age
    Pit decisions are marked with vertical dashed lines.
    """
    laps       = trace_df["lap"].values
    margin     = trace_df["pit_margin"].values
    pit_laps   = trace_df[trace_df["action_taken"] == 1]["lap"].values
    deg        = trace_df["degradation_norm"].values
    sc         = trace_df["sc_flag"].values
    tire       = trace_df["tire_age_norm"].values * 50   # denorm

    fig = plt.figure(figsize=(13, 9))
    fig.suptitle(
        f"DQN Decision Trace{': ' + episode_key if episode_key else ''}\n"
        "How the agent weighted pit vs stay-out at each lap",
        fontsize=12, fontweight="bold"
    )
    gs = gridspec.GridSpec(3, 1, hspace=0.45)

    # ── Panel 1: Q margin ─────────────────────────────────────────────────────
    ax1 = fig.add_subplot(gs[0])
    ax1.axhline(0, color="gray", linewidth=0.8, linestyle="--")
    ax1.fill_between(laps, margin, 0,
                     where=(np.array(margin) > 0),
                     color="#e63946", alpha=0.35, label="Pit favoured")
    ax1.fill_between(laps, margin, 0,
                     where=(np.array(margin) <= 0),
                     color="#457b9d", alpha=0.35, label="Stay-out favoured")
    ax1.plot(laps, margin, color="#333", linewidth=1.2)
    for pl in pit_laps:
        ax1.axvline(pl, color="#e63946", linestyle=":", linewidth=1.5, alpha=0.8)
    ax1.set_ylabel("Q(pit) − Q(stay)", fontsize=9)
    ax1.set_title("Action Preference Margin", fontsize=10)
    ax1.legend(fontsize=8, loc="upper left")
    ax1.spines[["top", "right"]].set_visible(False)

    # ── Panel 2: Degradation + SC ─────────────────────────────────────────────
    ax2 = fig.add_subplot(gs[1])
    ax2.plot(laps, deg, color="#f4a261", linewidth=1.8, label="Degradation rate (norm)")
    sc_laps = laps[sc >= 0.5]
    if len(sc_laps):
        ax2.scatter(sc_laps, deg[sc >= 0.5], color="#e63946", s=60,
                    zorder=5, label="SC active", marker="v")
    for pl in pit_laps:
        ax2.axvline(pl, color="#e63946", linestyle=":", linewidth=1.5, alpha=0.8)
    ax2.set_ylabel("Degradation (norm)", fontsize=9)
    ax2.set_title("Tire Degradation Rate & Safety Car Events", fontsize=10)
    ax2.legend(fontsize=8, loc="upper left")
    ax2.spines[["top", "right"]].set_visible(False)

    # ── Panel 3: Tire age ─────────────────────────────────────────────────────
    ax3 = fig.add_subplot(gs[2])
    ax3.plot(laps, tire, color="#2a9d8f", linewidth=1.8, label="Tire age (laps)")
    for pl in pit_laps:
        ax3.axvline(pl, color="#e63946", linestyle=":", linewidth=1.5, alpha=0.8,
                    label="Pit stop" if pl == pit_laps[0] else "")
    ax3.set_ylabel("Tire Age (laps)", fontsize=9)
    ax3.set_xlabel("Lap Number", fontsize=9)
    ax3.set_title("Tire Age (resets at each pit stop)", fontsize=10)
    ax3.legend(fontsize=8, loc="upper left")
    ax3.spines[["top", "right"]].set_visible(False)

    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Action preference plot saved → {out}")


# ── Counterfactual analysis ───────────────────────────────────────────────────

def counterfactual_analysis(
    model,
    trace_df: pd.DataFrame,
    param: str = "degradation_norm",
    perturbation: float = -0.10,
    label: str | None = None,
) -> pd.DataFrame:
    """
    Counterfactual: "What if one state dimension were different?"

    For each lap in the trace, perturb `param` by `perturbation` (additive)
    and recompute Q-values to see whether the decision would flip.

    Parameters
    ----------
    param : str
        Column in trace_df to perturb (e.g. 'degradation_norm', 'tire_age_norm').
    perturbation : float
        Additive amount to change the parameter (e.g. -0.10 = 10% lower
        in normalised space).
    label : str or None
        Human-readable description shown in output (e.g. "degradation −10%").

    Returns
    -------
    pd.DataFrame with original and counterfactual decisions + delta Q.
    """
    import torch
    if label is None:
        sign = "+" if perturbation >= 0 else ""
        label = f"{param} {sign}{perturbation*100:.0f}%"

    state_cols = ["tire_age_norm", "degradation_norm", "track_temp_norm", "sc_flag"]
    param_to_idx = {
        "tire_age_norm":    IDX_TIRE,
        "degradation_norm": IDX_DEG,
        "track_temp_norm":  IDX_TEMP,
        "sc_flag":          IDX_SC,
    }

    rows = []
    for _, row in trace_df.iterrows():
        # Build original and counterfactual obs vectors
        obs = np.array([
            row["tire_age_norm"],
            row["degradation_norm"],
            row["track_temp_norm"],
            row["sc_flag"],
        ], dtype=np.float32)

        full_obs = np.zeros(5, dtype=np.float32)
        full_obs[IDX_LAP]  = row.get("lap", 0) / 70.0
        full_obs[IDX_TIRE]  = obs[0]
        full_obs[IDX_DEG]   = obs[1]
        full_obs[IDX_TEMP]  = obs[2]
        full_obs[IDX_SC]    = obs[3]

        # Counterfactual: perturb the target dimension
        cf_obs = full_obs.copy()
        cf_idx = param_to_idx.get(param, IDX_DEG)
        cf_obs[cf_idx] = float(np.clip(full_obs[cf_idx] + perturbation, 0.0, 1.0))

        q_orig = get_q_values(model, full_obs)
        q_cf   = get_q_values(model, cf_obs)

        orig_action = int(q_orig[1] > q_orig[0])
        cf_action   = int(q_cf[1]   > q_cf[0])
        flipped     = orig_action != cf_action

        rows.append({
            "lap":             int(row["lap"]),
            "original_action": orig_action,
            "cf_action":       cf_action,
            "decision_flipped":flipped,
            "q_pit_orig":      float(q_orig[1]),
            "q_pit_cf":        float(q_cf[1]),
            "delta_q_pit":     float(q_cf[1] - q_orig[1]),
            "perturbation":    label,
        })

    result = pd.DataFrame(rows)
    n_flip = result["decision_flipped"].sum()
    n_pit  = (result["original_action"] == 1).sum()
    print(f"\n  Counterfactual: {label}")
    print(f"  Original pit decisions : {n_pit}")
    print(f"  Decisions flipped      : {n_flip} "
          f"({n_flip/(len(result)+1e-9)*100:.1f}% of laps)")

    return result


def plot_counterfactuals(
    cf_results: dict[str, pd.DataFrame],
    trace_df: pd.DataFrame,
    out: Path = OUTPUTS_DIR / "counterfactual_analysis.png",
) -> None:
    """
    Overlay counterfactual Q(pit) traces on the original decision trace.
    Shows how robust (or sensitive) the agent's preference is to parameter changes.
    """
    laps = trace_df["lap"].values
    orig_margin = trace_df["pit_margin"].values

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(laps, orig_margin, "k-", linewidth=2, label="Original (no change)", zorder=5)
    ax.axhline(0, color="gray", linewidth=0.8, linestyle="--")

    palette = ["#e63946", "#457b9d", "#2a9d8f", "#f4a261"]
    for (label, cf_df), color in zip(cf_results.items(), palette):
        delta = cf_df["delta_q_pit"].values[:len(laps)]
        cf_margin = orig_margin[:len(delta)] + delta
        ax.plot(laps[:len(delta)], cf_margin, "--", color=color,
                linewidth=1.5, alpha=0.9, label=label)
        # Mark flipped decisions
        flips = cf_df[cf_df["decision_flipped"]]["lap"].values
        for fl in flips:
            ax.axvline(fl, color=color, alpha=0.3, linewidth=1)

    pit_laps = trace_df[trace_df["action_taken"] == 1]["lap"].values
    for pl in pit_laps:
        ax.axvline(pl, color="black", linestyle=":", linewidth=1.2,
                   alpha=0.5, label="Pit stop" if pl == pit_laps[0] else "")

    ax.fill_between(laps, orig_margin, 0, where=(orig_margin > 0),
                    alpha=0.08, color="#e63946")
    ax.set_xlabel("Lap Number", fontsize=10)
    ax.set_ylabel("Q(pit) − Q(stay) Margin", fontsize=10)
    ax.set_title("Counterfactual Analysis — How Sensitive Is the Agent?\n"
                 "(dashed = what-if scenarios; vertical highlights = decision flips)",
                 fontsize=11)
    ax.legend(fontsize=9, loc="upper left", ncol=2)
    ax.spines[["top", "right"]].set_visible(False)
    plt.tight_layout()
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Counterfactual plot saved → {out}")


# ── Lap-level explanation table ───────────────────────────────────────────────

def print_explanation_table(trace_df: pd.DataFrame, n: int = 10) -> None:
    """Print the most decisive laps (largest absolute Q margin)."""
    top = trace_df.nlargest(n, "pit_margin")[
        ["lap", "q_stay_out", "q_pit", "pit_margin", "action_taken"]
    ].copy()
    top["action"] = top["action_taken"].map({0: "Stay", 1: "PIT"})

    print("\n  Top pit-favoured laps:")
    print(f"  {'Lap':>4} {'Q_stay':>8} {'Q_pit':>8} {'ΔQ':>8} {'Action':>6}")
    print(f"  {'─'*40}")
    for _, r in top.iterrows():
        print(f"  {int(r.lap):>4} {r.q_stay_out:>8.3f} {r.q_pit:>8.3f}"
              f" {r.pit_margin:>+8.3f} {r.action:>6}")

    # Print explanation for the most decisive pit lap
    pit_rows = trace_df[trace_df["action_taken"] == 1]
    if not pit_rows.empty:
        best = pit_rows.nlargest(1, "pit_margin").iloc[0]
        print(f"\n  Most decisive pit (lap {int(best.lap)}):")
        print(f"  → {best.explanation}")


# ── Main ──────────────────────────────────────────────────────────────────────

def run(
    model_path: str,
    data_path: Path | None = None,
    episode_seed: int = 7,
) -> None:
    """
    Full explainability pipeline for one episode.
    """
    from stable_baselines3 import DQN

    data_path = data_path or PROCESSED_PARQUET

    print(f"\n{'='*60}")
    print(f"  F1 Pitstop RL — Explainability Analysis (Phase 6)")
    print(f"  Model : {model_path}")
    print(f"{'='*60}\n")

    model = DQN.load(model_path)
    env   = F1PitEnv(data_path=data_path, seed=episode_seed)

    # ── 1. Decision trace ─────────────────────────────────────────────────────
    print("[1/3] Rolling out episode and logging Q-values…")
    trace_df = explain_episode(model, env, episode_seed=episode_seed)

    trace_csv = OUTPUTS_DIR / "decision_trace.csv"
    trace_df.to_csv(trace_csv, index=False)
    print(f"  Decision trace saved → {trace_csv}")
    print_explanation_table(trace_df)

    # ── 2. Action preference plot ─────────────────────────────────────────────
    print("\n[2/3] Generating action preference plot…")
    plot_action_preference(
        trace_df,
        out=OUTPUTS_DIR / "action_preference.png",
        episode_key=str(env.current_episode_key),
    )

    # ── 3. Counterfactuals ────────────────────────────────────────────────────
    print("\n[3/3] Running counterfactual analysis…")
    counterfactuals_to_test = {
        "degradation −10%":  ("degradation_norm", -0.10),
        "degradation +10%":  ("degradation_norm", +0.10),
        "tire age −20%":     ("tire_age_norm",    -0.20),
        "SC removed":        ("sc_flag",          -1.00),
    }
    cf_results = {}
    for label, (param, pert) in counterfactuals_to_test.items():
        cf_df = counterfactual_analysis(model, trace_df, param, pert, label)
        cf_results[label] = cf_df

    plot_counterfactuals(
        cf_results, trace_df,
        out=OUTPUTS_DIR / "counterfactual_analysis.png",
    )
    print("\n  Phase 6 complete.\n")


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="F1 DQN explainability & counterfactuals")
    p.add_argument("--model", type=str, required=True,
                   help="Path to trained DQN .zip")
    p.add_argument("--seed", type=int, default=7,
                   help="Episode seed to trace (default: 7)")
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    run(model_path=args.model, episode_seed=args.seed)
