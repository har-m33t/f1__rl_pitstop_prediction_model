"""
dashboard.py — Phase 7: Streamlit Interactive Dashboard

A fully interactive race strategy explorer. Load any saved decision trace
and explore the agent's reasoning visually.

Launch:
    streamlit run visualizations/dashboard.py

    # Or with a specific trace pre-loaded:
    streamlit run visualizations/dashboard.py -- --trace outputs/decision_trace.csv
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
import numpy as np
import pandas as pd
import streamlit as st

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="F1 Pit Stop RL — Strategy Explorer",
    page_icon="🏎️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Styling ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main { background: #0f1117; color: #f0f0f0; }
    .block-container { padding-top: 1.5rem; }
    .metric-label { font-size: 0.8rem; color: #aaa; }
    .stMetric > div > div { color: #f0f0f0; }
    h1, h2, h3 { color: #e63946; }
    .stSidebar { background: #1a1d2e; }
</style>
""", unsafe_allow_html=True)


# ── Data loading ──────────────────────────────────────────────────────────────

def _synthetic_trace(n: int = 55, seed: int = 0) -> pd.DataFrame:
    """Generate a synthetic decision trace for demo mode."""
    rng = np.random.default_rng(seed)
    stint_len = n // 3
    tire_age = np.concatenate([
        np.arange(1, stint_len + 1),
        np.arange(1, stint_len + 1),
        np.arange(1, n - 2 * stint_len + 1),
    ])[:n]

    deg = np.clip(tire_age * 0.012 + rng.normal(0, 0.02, n), 0, 1)
    margin = rng.normal(0, 0.3, n)
    margin[stint_len - 1] += 0.8
    margin[2 * stint_len - 1] += 0.7

    actions = np.zeros(n, dtype=int)
    actions[stint_len - 1] = 1
    actions[2 * stint_len - 1] = 1

    return pd.DataFrame({
        "lap":              range(1, n + 1),
        "tire_age_norm":    tire_age / 50.0,
        "degradation_norm": deg,
        "track_temp_norm":  np.clip(0.5 + rng.normal(0, 0.04, n), 0, 1),
        "sc_flag":          (rng.random(n) < 0.06).astype(float),
        "action_taken":     actions,
        "pit_margin":       margin,
        "q_stay_out":       -90 - deg * 10 + rng.normal(0, 1, n),
        "q_pit":            -92 - (1 - deg) * 5 + rng.normal(0, 1, n),
    })


@st.cache_data
def load_trace(path: str) -> pd.DataFrame:
    return pd.read_csv(path)


# ── Plotting helpers (dashboard-adapted versions) ─────────────────────────────

def _fig_degradation(df: pd.DataFrame, show_sc: bool) -> plt.Figure:
    laps     = df["lap"].values
    deg      = df["degradation_norm"].values
    tire     = df["tire_age_norm"].values * 50
    sc       = df["sc_flag"].values
    pit_laps = df[df["action_taken"] == 1]["lap"].values

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 5), sharex=True,
                                    gridspec_kw={"height_ratios": [2, 1]})
    fig.patch.set_facecolor("#0f1117")
    for ax in (ax1, ax2):
        ax.set_facecolor("#1a1d2e")
        ax.tick_params(colors="#aaa")
        ax.yaxis.label.set_color("#aaa")
        ax.xaxis.label.set_color("#aaa")
        for sp in ax.spines.values():
            sp.set_color("#333")

    ax1.plot(laps, deg, color="#2a9d8f", linewidth=2, label="Degradation")
    ax1.fill_between(laps, deg, alpha=0.2, color="#2a9d8f")
    if show_sc:
        for lap, s in zip(laps, sc):
            if s >= 0.5:
                ax1.axvspan(lap - 0.5, lap + 0.5, color="#e9c46a", alpha=0.25)
    for pl in pit_laps:
        ax1.axvline(pl, color="#e63946", linestyle="--", linewidth=1.5, alpha=0.9)
        ax1.annotate("PIT", xy=(pl, max(deg) * 0.9), fontsize=8,
                     color="#e63946", ha="center", fontweight="bold")
    ax1.set_ylabel("Degradation (norm)", color="#aaa", fontsize=9)
    ax1.legend(fontsize=8, facecolor="#1a1d2e", labelcolor="#f0f0f0")

    ax2.bar(laps, tire, color="#f4a261", width=0.8, alpha=0.8)
    for pl in pit_laps:
        ax2.axvline(pl, color="#e63946", linestyle="--", linewidth=1.5, alpha=0.7)
    ax2.set_ylabel("Tire Age (laps)", color="#aaa", fontsize=9)
    ax2.set_xlabel("Lap Number", color="#aaa", fontsize=9)

    fig.tight_layout()
    return fig


def _fig_q_margin(df: pd.DataFrame) -> plt.Figure:
    laps   = df["lap"].values
    margin = df["pit_margin"].values
    pits   = df[df["action_taken"] == 1]["lap"].values
    sc     = df["sc_flag"].values

    fig, ax = plt.subplots(figsize=(10, 3.5))
    fig.patch.set_facecolor("#0f1117")
    ax.set_facecolor("#1a1d2e")
    for sp in ax.spines.values():
        sp.set_color("#333")
    ax.tick_params(colors="#aaa")

    ax.axhline(0, color="#555", linewidth=0.8, linestyle="--")
    ax.fill_between(laps, margin, 0, where=(margin > 0),
                    color="#e63946", alpha=0.3, label="Pit preferred")
    ax.fill_between(laps, margin, 0, where=(margin <= 0),
                    color="#457b9d", alpha=0.3, label="Stay preferred")
    ax.plot(laps, margin, color="#f0f0f0", linewidth=1.2)

    for pl in pits:
        ax.axvline(pl, color="#e63946", linestyle=":", linewidth=1.5, alpha=0.8,
                   label="Pit taken" if pl == pits[0] else "")
    sc_laps = laps[sc >= 0.5]
    if len(sc_laps):
        ax.scatter(sc_laps, margin[sc >= 0.5], color="#e9c46a",
                   s=60, zorder=5, marker="v", label="SC lap")

    ax.set_ylabel("Q(pit) − Q(stay)", color="#aaa", fontsize=9)
    ax.set_xlabel("Lap Number", color="#aaa", fontsize=9)
    ax.legend(fontsize=8, facecolor="#1a1d2e", labelcolor="#f0f0f0", ncol=3)
    fig.tight_layout()
    return fig


def _fig_counterfactual(df: pd.DataFrame, param: str, delta: float) -> plt.Figure:
    laps       = df["lap"].values
    orig_margin = df["pit_margin"].values
    param_vals  = df[param].values

    cf_margin = orig_margin + delta * (1 + param_vals)  # simplified approximation
    flipped   = np.sign(orig_margin) != np.sign(cf_margin)

    fig, ax = plt.subplots(figsize=(10, 3.5))
    fig.patch.set_facecolor("#0f1117")
    ax.set_facecolor("#1a1d2e")
    for sp in ax.spines.values():
        sp.set_color("#333")
    ax.tick_params(colors="#aaa")

    ax.axhline(0, color="#555", linewidth=0.8, linestyle="--")
    ax.plot(laps, orig_margin, color="#f0f0f0", linewidth=2, label="Original")
    ax.plot(laps, cf_margin,   color="#e63946", linewidth=2, linestyle="--",
            label=f"Counterfactual ({param} {'+' if delta >= 0 else ''}{delta:.0%})")

    flip_laps = laps[flipped]
    if len(flip_laps):
        ax.scatter(flip_laps, cf_margin[flipped], color="#e9c46a",
                   s=80, zorder=6, marker="*", label=f"Decision flipped ({len(flip_laps)} laps)")

    ax.set_ylabel("Q(pit) − Q(stay)", color="#aaa", fontsize=9)
    ax.set_xlabel("Lap Number", color="#aaa", fontsize=9)
    ax.legend(fontsize=8, facecolor="#1a1d2e", labelcolor="#f0f0f0")
    fig.tight_layout()
    return fig


# ── Dashboard layout ──────────────────────────────────────────────────────────

def main() -> None:
    # ── Header ───────────────────────────────────────────────────────────────
    st.title("🏎️ F1 Pit Stop RL — Strategy Explorer")
    st.markdown(
        "_Framed pit strategy as a sequential decision problem with delayed rewards._"
    )
    st.divider()

    # ── Sidebar controls ──────────────────────────────────────────────────────
    with st.sidebar:
        st.header("📂 Data Source")
        data_mode = st.radio("Mode", ["Demo (synthetic)", "Load trace CSV"])

        trace_path = None
        if data_mode == "Load trace CSV":
            trace_path = st.text_input(
                "Trace CSV path",
                value="outputs/decision_trace.csv",
            )

        st.divider()
        st.header("⚙️ Display Options")
        show_sc = st.checkbox("Highlight safety car laps", value=True)
        lap_range = st.slider("Lap range to display", 1, 80, (1, 70))

        st.divider()
        st.header("🔮 Counterfactual")
        cf_param = st.selectbox(
            "Perturb parameter",
            ["degradation_norm", "tire_age_norm", "track_temp_norm", "sc_flag"],
        )
        cf_delta = st.slider(
            "Perturbation (normalised units)",
            min_value=-0.30, max_value=0.30, value=-0.10, step=0.01,
        )

    # ── Load data ─────────────────────────────────────────────────────────────
    if data_mode == "Demo (synthetic)":
        df = _synthetic_trace()
        episode_label = "Demo Race — Synthetic Data"
    else:
        try:
            df = load_trace(trace_path)
            episode_label = trace_path
        except Exception as e:
            st.error(f"Could not load trace: {e}")
            st.info("Run `python analysis/explain_decisions.py --model rl/models/dqn_f1_pit.zip` first.")
            return

    # Apply lap range filter
    df = df[(df["lap"] >= lap_range[0]) & (df["lap"] <= lap_range[1])].copy()

    # ── KPI metrics ───────────────────────────────────────────────────────────
    total_pits  = int((df["action_taken"] == 1).sum())
    pit_laps    = df[df["action_taken"] == 1]["lap"].tolist()
    avg_deg     = float(df["degradation_norm"].mean())
    sc_count    = int((df["sc_flag"] >= 0.5).sum())
    decisive    = df["pit_margin"].abs().mean()

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Laps", len(df))
    col2.metric("Pit Stops", total_pits)
    col3.metric("SC Laps", sc_count)
    col4.metric("Avg Degradation", f"{avg_deg:.3f}")
    col5.metric("Avg |ΔQ|", f"{decisive:.3f}")

    st.divider()

    # ── Tab layout ────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs([
        "📉 Degradation",
        "🎯 Action Preference",
        "🔄 Counterfactuals",
        "📋 Decision Log",
    ])

    with tab1:
        st.subheader("Lap vs Tire Degradation")
        st.markdown(
            "The upper panel shows tire degradation rate across the race. "
            "Pit stops (red dashed) reset tire age. "
            "Safety car laps (yellow shading) often trigger opportunistic pits."
        )
        st.pyplot(_fig_degradation(df, show_sc=show_sc))

    with tab2:
        st.subheader("Q-Value Action Preference")
        st.markdown(
            "**Q(pit) − Q(stay)** at each lap. Positive values mean the agent "
            "prefers to pit. Red dashed markers show actual pit decisions taken."
        )
        st.pyplot(_fig_q_margin(df))

        if pit_laps:
            decisive_row = df[df["action_taken"] == 1].nlargest(1, "pit_margin").iloc[0]
            st.info(
                f"**Most decisive pit:** Lap {int(decisive_row.lap)} — "
                f"ΔQ = {decisive_row.pit_margin:+.3f}  "
                f"(degradation={decisive_row.degradation_norm:.3f}, "
                f"tire_age={decisive_row.tire_age_norm * 50:.1f} laps)"
            )

    with tab3:
        st.subheader("Counterfactual Analysis")
        st.markdown(
            f"What if **`{cf_param}`** were "
            f"{'higher' if cf_delta > 0 else 'lower'} by "
            f"**{abs(cf_delta):.0%}** (normalised)? "
            "Stars mark laps where the decision would flip."
        )
        st.pyplot(_fig_counterfactual(df, cf_param, cf_delta))

    with tab4:
        st.subheader("Per-Lap Decision Log")
        cols = [c for c in ["lap", "action_taken", "pit_margin", "q_stay_out",
                             "q_pit", "degradation_norm", "tire_age_norm", "sc_flag"]
                if c in df.columns]
        display = df[cols].copy()
        display["action"] = display["action_taken"].map({0: "Stay", 1: "🔴 PIT"})
        display["pit_margin"] = display["pit_margin"].round(4)
        st.dataframe(
            display.drop(columns=["action_taken"]),
            use_container_width=True,
            height=420,
        )

    # ── Footer ────────────────────────────────────────────────────────────────
    st.divider()
    st.caption(
        "F1 Pit Stop RL — Phase 7 Visualization Dashboard | "
        "Data: FastF1 2022–2024 | Model: DQN (Stable-Baselines3)"
    )


if __name__ == "__main__":
    main()
