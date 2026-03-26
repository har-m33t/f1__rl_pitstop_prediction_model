"""
plots.py — Phase 7: Race visualization library

Three publication-quality plots:
  1. lap_vs_degradation()  — tire degradation curve across a race
  2. pit_decisions_over_time() — RL agent's pit choices annotated on lap timeline
  3. rl_vs_actual_strategy() — compare RL decisions to the real historical strategy

Usage:
    from visualizations.plots import lap_vs_degradation, pit_decisions_over_time, rl_vs_actual_strategy

    # Or run standalone to generate sample plots from a trace CSV:
    python visualizations/plots.py --trace outputs/decision_trace.csv
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd

OUTPUTS_DIR = ROOT / "outputs" / "visualizations"
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

# ── Shared style ──────────────────────────────────────────────────────────────
PALETTE = {
    "rl":       "#e63946",
    "actual":   "#457b9d",
    "tire":     "#f4a261",
    "deg":      "#2a9d8f",
    "sc":       "#e9c46a",
    "neutral":  "#6c757d",
}
plt.rcParams.update({
    "font.family":  "DejaVu Sans",
    "axes.spines.top":   False,
    "axes.spines.right": False,
    "figure.dpi": 100,
})


# ── Plot 1: Lap vs Degradation ────────────────────────────────────────────────

def lap_vs_degradation(
    trace_df: pd.DataFrame,
    driver_label: str = "Driver",
    out: Path | None = None,
    ax=None,
) -> plt.Axes:
    """
    Plot tire degradation rate (and raw tire age) across all laps in a race.

    Pit stops are marked with vertical bands. Safety car periods are shaded.

    Parameters
    ----------
    trace_df : pd.DataFrame
        Output of analysis.explain_decisions.explain_episode (or any DataFrame
        with columns: lap, degradation_norm, tire_age_norm, sc_flag, action_taken).
    """
    standalone = ax is None
    if standalone:
        fig, (ax, ax2) = plt.subplots(2, 1, figsize=(12, 6), sharex=True,
                                       gridspec_kw={"height_ratios": [2, 1]},)
        fig.suptitle(f"Tire Degradation — {driver_label}", fontsize=12, fontweight="bold")
    else:
        ax2 = None

    laps         = trace_df["lap"].values
    deg_norm     = trace_df["degradation_norm"].values
    tire_norm    = trace_df["tire_age_norm"].values * 50
    sc_flag      = trace_df["sc_flag"].values
    pit_laps     = trace_df[trace_df["action_taken"] == 1]["lap"].values

    # Degradation curve
    ax.plot(laps, deg_norm, color=PALETTE["deg"], linewidth=2, label="Degradation rate (norm)")
    ax.fill_between(laps, deg_norm, alpha=0.15, color=PALETTE["deg"])

    # Safety car shading
    for i, (lap, sc) in enumerate(zip(laps, sc_flag)):
        if sc >= 0.5:
            ax.axvspan(lap - 0.5, lap + 0.5, color=PALETTE["sc"], alpha=0.30, linewidth=0)

    # Pit stop markers
    for pl in pit_laps:
        ax.axvline(pl, color=PALETTE["rl"], linestyle="--", linewidth=1.8, alpha=0.9)
        ax.annotate("PIT", xy=(pl, ax.get_ylim()[1] * 0.9 if ax.get_ylim()[1] else 0.9),
                    fontsize=8, color=PALETTE["rl"], ha="center", fontweight="bold")

    ax.set_ylabel("Degradation Rate (norm)", fontsize=9)
    ax.legend(fontsize=8)

    # Tire age sub-panel
    if ax2 is not None:
        ax2.bar(laps, tire_norm, color=PALETTE["tire"], width=0.8, alpha=0.8, label="Tire age (laps)")
        for pl in pit_laps:
            ax2.axvline(pl, color=PALETTE["rl"], linestyle="--", linewidth=1.5, alpha=0.9)
        ax2.set_ylabel("Tire Age (laps)", fontsize=9)
        ax2.set_xlabel("Lap Number", fontsize=9)
        ax2.legend(fontsize=8)

    if standalone:
        out = out or OUTPUTS_DIR / "lap_vs_degradation.png"
        plt.tight_layout()
        plt.savefig(out, dpi=150, bbox_inches="tight")
        plt.close()
        print(f"  → {out}")
    return ax


# ── Plot 2: Pit Decisions Over Time ──────────────────────────────────────────

def pit_decisions_over_time(
    trace_df: pd.DataFrame,
    driver_label: str = "Driver",
    out: Path | None = None,
) -> None:
    """
    Horizontal racetrack timeline showing when the agent pits vs stays out.
    Each lap is a coloured segment: green (stay) / red (pit).
    """
    laps         = trace_df["lap"].values
    actions      = trace_df["action_taken"].values   # 0 = stay, 1 = pit
    margins      = trace_df["pit_margin"].values      # Q(pit) − Q(stay)
    sc_flag      = trace_df["sc_flag"].values

    fig, (ax_action, ax_margin) = plt.subplots(
        2, 1, figsize=(14, 5),
        gridspec_kw={"height_ratios": [1, 3]},
        sharex=True,
    )
    fig.suptitle(f"Pit Decisions Over Time — {driver_label}",
                 fontsize=12, fontweight="bold")

    # -- Top strip: action per lap
    for lap, action, sc in zip(laps, actions, sc_flag):
        color = PALETTE["rl"] if action == 1 else ("#e9c46a" if sc >= 0.5 else "#2a9d8f")
        ax_action.barh(0, 1, left=lap - 1, color=color, edgecolor="white", height=1)
    ax_action.set_yticks([])
    ax_action.set_xlim(laps[0] - 1, laps[-1])
    legend_patches = [
        mpatches.Patch(color=PALETTE["rl"],  label="Pit stop"),
        mpatches.Patch(color="#2a9d8f",      label="Stay out"),
        mpatches.Patch(color=PALETTE["sc"],  label="Safety car lap"),
    ]
    ax_action.legend(handles=legend_patches, loc="upper right", fontsize=8, ncol=3)
    ax_action.set_title("Action per Lap", fontsize=10, loc="left")

    # -- Bottom: Q-preference margin
    ax_margin.axhline(0, color="gray", linewidth=0.8, linestyle="--")
    ax_margin.fill_between(laps, margins, 0,
                            where=(margins > 0), color=PALETTE["rl"], alpha=0.3, label="Pit preferred")
    ax_margin.fill_between(laps, margins, 0,
                            where=(margins <= 0), color="#2a9d8f", alpha=0.3, label="Stay preferred")
    ax_margin.plot(laps, margins, color="#333", linewidth=1.2)
    ax_margin.set_ylabel("Q(pit) − Q(stay)", fontsize=9)
    ax_margin.set_xlabel("Lap Number", fontsize=9)
    ax_margin.legend(fontsize=8, loc="upper left")

    plt.tight_layout()
    out = out or OUTPUTS_DIR / "pit_decisions_over_time.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  → {out}")


# ── Plot 3: RL vs Actual Strategy ────────────────────────────────────────────

def rl_vs_actual_strategy(
    trace_df: pd.DataFrame,
    actual_pit_laps: list[int],
    driver_label: str = "Driver",
    out: Path | None = None,
) -> None:
    """
    Overlay the RL agent's pit stops vs the actual historical strategy.

    Parameters
    ----------
    actual_pit_laps : list[int]
        Lap numbers when the real driver pitted (from FastF1 PitInTime data).
    """
    laps      = trace_df["lap"].values
    margin    = trace_df["pit_margin"].values
    rl_pits   = trace_df[trace_df["action_taken"] == 1]["lap"].values
    n_laps    = len(laps)

    # Build stint arrays for both strategies
    def _stints(pit_laps, total):
        stints = []
        start = 1
        for pl in sorted(pit_laps):
            stints.append((start, pl))
            start = pl + 1
        stints.append((start, total))
        return stints

    rl_stints  = _stints(rl_pits,        n_laps)
    act_stints = _stints(actual_pit_laps, n_laps)

    fig, axes = plt.subplots(3, 1, figsize=(13, 8), sharex=True,
                              gridspec_kw={"height_ratios": [1, 1, 2]})
    fig.suptitle(f"RL vs Actual Strategy — {driver_label}",
                 fontsize=12, fontweight="bold")

    # -- Plot 1: RL stint map
    ax = axes[0]
    for i, (s, e) in enumerate(rl_stints):
        ax.barh(0, e - s + 1, left=s - 1, color=PALETTE["rl"], alpha=0.7,
                edgecolor="white", height=0.6)
        ax.text((s + e) / 2 - 1, 0, f"Stint {i+1}", va="center", ha="center",
                fontsize=8, color="white", fontweight="bold")
    ax.set_yticks([])
    ax.set_title("RL Agent Strategy", fontsize=10, loc="left", color=PALETTE["rl"])

    # -- Plot 2: Actual stint map
    ax = axes[1]
    for i, (s, e) in enumerate(act_stints):
        ax.barh(0, e - s + 1, left=s - 1, color=PALETTE["actual"], alpha=0.7,
                edgecolor="white", height=0.6)
        ax.text((s + e) / 2 - 1, 0, f"Stint {i+1}", va="center", ha="center",
                fontsize=8, color="white", fontweight="bold")
    ax.set_yticks([])
    ax.set_title("Actual Historical Strategy", fontsize=10, loc="left", color=PALETTE["actual"])

    # -- Plot 3: Q-margin context
    ax = axes[2]
    ax.plot(laps, margin, color="#333", linewidth=1.2, label="Q margin")
    ax.axhline(0, color="gray", linewidth=0.8, linestyle="--")
    ax.fill_between(laps, margin, 0, where=(margin > 0),
                    color=PALETTE["rl"], alpha=0.15)
    for pl in rl_pits:
        ax.axvline(pl, color=PALETTE["rl"], linewidth=1.5, linestyle="--",
                   label="RL pit" if pl == rl_pits[0] else "")
    for pl in actual_pit_laps:
        ax.axvline(pl, color=PALETTE["actual"], linewidth=1.5, linestyle=":",
                   label="Actual pit" if pl == actual_pit_laps[0] else "")
    ax.set_xlabel("Lap Number", fontsize=9)
    ax.set_ylabel("Q(pit) − Q(stay)", fontsize=9)
    ax.legend(fontsize=8, loc="upper left", ncol=2)

    plt.tight_layout()
    out = out or OUTPUTS_DIR / "rl_vs_actual_strategy.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  → {out}")


# ── Combined summary figure ───────────────────────────────────────────────────

def generate_all_plots(trace_df: pd.DataFrame, driver_label: str = "Race Episode") -> None:
    """Generate all three plots from a decision trace DataFrame."""
    print(f"\n  Generating all Phase 7 visualization plots for: {driver_label}")
    lap_vs_degradation(trace_df, driver_label)
    pit_decisions_over_time(trace_df, driver_label)

    # For rl_vs_actual, infer actual pit laps from the PitInTime column if available
    # (this comes through in the trace if the env episode retained it)
    actual_pits = []
    if "actual_pit_lap" in trace_df.columns:
        actual_pits = trace_df[trace_df["actual_pit_lap"] == 1]["lap"].tolist()
    if not actual_pits:
        # Synthetic fallback: show mid-race pit as representative "actual" strategy
        total = int(trace_df["lap"].max())
        actual_pits = [total // 3] if total > 10 else [5]

    rl_vs_actual_strategy(trace_df, actual_pits, driver_label)
    print(f"\n  All plots saved to {OUTPUTS_DIR}/")


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Generate Phase 7 race visualization plots")
    p.add_argument("--trace", type=str, default=None,
                   help="Path to decision_trace.csv from explain_decisions.py")
    args = p.parse_args()

    if args.trace:
        df = pd.read_csv(args.trace)
        generate_all_plots(df)
    else:
        # Generate synthetic demo plots even without real data
        print("No trace supplied — generating demo plots with synthetic data…")
        n = 55
        rng = np.random.default_rng(0)
        demo_df = pd.DataFrame({
            "lap":              range(1, n + 1),
            "degradation_norm": np.clip(np.cumsum(rng.normal(0.008, 0.004, n)), 0, 1),
            "tire_age_norm":    np.tile(np.linspace(0, 0.6, 20), 3)[:n],
            "track_temp_norm":  np.clip(0.5 + rng.normal(0, 0.05, n), 0, 1),
            "sc_flag":          (rng.random(n) < 0.05).astype(float),
            "action_taken":     ((np.arange(n) % 20 == 19)).astype(int),
            "pit_margin":       rng.normal(0, 0.4, n),
            "q_stay_out":       rng.normal(-90, 5, n),
            "q_pit":            rng.normal(-92, 5, n),
        })
        # Fix pit_margin to match pit decisions
        demo_df.loc[demo_df["action_taken"] == 1, "pit_margin"] = np.abs(
            rng.normal(0.5, 0.2, demo_df["action_taken"].sum())
        )
        generate_all_plots(demo_df, driver_label="Demo Race (Synthetic)")
