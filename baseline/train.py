"""
train.py — Phase 2 baseline classifier training for F1 pit stop prediction.

Usage:
    python baseline/train.py
    # or from project root:
    python -m baseline.train

What it does:
    1. Loads processed data and builds feature matrix + pit_label
    2. Season split: train=2022-2023, val=2024 (no temporal leakage)
    3. Trains two baseline classifiers:
         - Logistic Regression  (linear, interpretable)
         - Random Forest        (non-linear, feature importance)
    4. Evaluates both on the 2024 holdout: Precision, Recall, F1, ROC-AUC
       (Recall is the primary metric — missing a pit window costs more than
        a false alarm in race strategy)
    5. Saves trained models to baseline/models/
    6. Generates feature importance chart -> outputs/feature_importance.png
    7. Warns if any Phase 1 feature ranks in the bottom 20%
"""

from __future__ import annotations

import logging
import os
import sys
import warnings
from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")  # non-interactive backend for saving figures
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    classification_report,
    precision_recall_fscore_support,
    roc_auc_score,
)
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from baseline.labels import (
    IMBALANCE_STRATEGY,
    apply_smote,
    get_feature_matrix,
    load_labelled_data,
    season_split,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)
warnings.filterwarnings("ignore", category=UserWarning)

# ── Output directories ────────────────────────────────────────────────────────
MODELS_DIR = ROOT / "baseline" / "models"
OUTPUTS_DIR = ROOT / "outputs"
MODELS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

# Phase 1 RL features — flagged for the bottom-20% warning
PHASE1_FEATURES = {
    "tire_age",
    "lap_time_delta",
    "degradation_slope",
    "track_temp",
    "track_temp_is_proxy",
    "safety_car_flag",
}

RANDOM_STATE = 42


# ── Metrics helper ────────────────────────────────────────────────────────────

def evaluate(name: str, model, X_val: pd.DataFrame, y_val: pd.Series) -> dict:
    """
    Evaluate a trained model on the validation set.

    Primary metric is Recall (missing a pit window costs more than a false
    alarm in race strategy). Also reports Precision, F1, and ROC-AUC.
    """
    y_pred = model.predict(X_val)
    y_proba = (
        model.predict_proba(X_val)[:, 1]
        if hasattr(model, "predict_proba")
        else None
    )

    precision, recall, f1, _ = precision_recall_fscore_support(
        y_val, y_pred, average="binary", zero_division=0
    )
    roc_auc = roc_auc_score(y_val, y_proba) if y_proba is not None else float("nan")

    print(f"\n{'─'*55}")
    print(f"  {name} — 2024 holdout results")
    print(f"{'─'*55}")
    print(classification_report(y_val, y_pred, target_names=["Stay Out", "Pit Stop"]))
    print(f"  ROC-AUC : {roc_auc:.4f}")
    print(f"  Recall  : {recall:.4f}  ← PRIMARY METRIC")
    print(f"{'─'*55}\n")

    return {
        "name": name,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "roc_auc": roc_auc,
    }


# ── Feature importance chart (Step 2.3) ──────────────────────────────────────

def plot_feature_importance(
    rf_model,
    feature_names: list[str],
    out_path: Path = OUTPUTS_DIR / "feature_importance.png",
) -> None:
    """
    Generate a horizontal bar chart of Random Forest feature importances and
    warn if any Phase 1 RL feature ranks in the bottom 20%.
    """
    # Extract from pipeline if wrapped
    clf = rf_model.named_steps["clf"] if hasattr(rf_model, "named_steps") else rf_model

    importances = clf.feature_importances_
    indices = np.argsort(importances)  # ascending for horizontal bar

    sorted_names = [feature_names[i] for i in indices]
    sorted_vals = importances[indices]

    # ── Bottom 20% warning ────────────────────────────────────────────────────
    threshold_idx = int(len(importances) * 0.20)
    bottom_20_names = set(sorted_names[:threshold_idx])
    phase1_in_bottom = PHASE1_FEATURES & bottom_20_names
    if phase1_in_bottom:
        for feat in sorted(phase1_in_bottom):
            logger.warning(
                "⚠  Phase 1 feature '%s' ranks in the bottom 20%% of importances. "
                "Consider reviewing it before passing to the RL environment.",
                feat,
            )

    # ── Ranked stdout list ────────────────────────────────────────────────────
    print("\nRandom Forest — Feature Importance Ranking (highest → lowest):")
    for rank, (nm, val) in enumerate(
        zip(reversed(sorted_names), reversed(sorted_vals)), start=1
    ):
        marker = "  ⚠ Phase1" if nm in PHASE1_FEATURES else ""
        print(f"  {rank:>2}. {nm:<30} {val:.4f}{marker}")

    # ── Chart ─────────────────────────────────────────────────────────────────
    colors = [
        "#e63946" if nm in PHASE1_FEATURES else "#457b9d"
        for nm in sorted_names
    ]

    fig, ax = plt.subplots(figsize=(10, max(6, len(sorted_names) * 0.38)))
    bars = ax.barh(sorted_names, sorted_vals, color=colors, edgecolor="white", height=0.7)

    # Label each bar
    for bar, val in zip(bars, sorted_vals):
        ax.text(
            bar.get_width() + 0.001, bar.get_y() + bar.get_height() / 2,
            f"{val:.3f}", va="center", ha="left", fontsize=8, color="#333"
        )

    # Legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor="#e63946", label="Phase 1 RL feature"),
        Patch(facecolor="#457b9d", label="Other feature"),
    ]
    ax.legend(handles=legend_elements, loc="lower right", fontsize=9)

    ax.set_xlabel("Mean Decrease in Impurity", fontsize=10)
    ax.set_title("Random Forest — Feature Importances\n(F1 Pit Stop Prediction Baseline)", fontsize=12)
    ax.axvline(
        np.percentile(importances, 20), color="gray", linestyle="--",
        linewidth=1, label="Bottom 20% threshold"
    )
    ax.spines[["top", "right"]].set_visible(False)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info("Feature importance chart saved → %s", out_path)


# ── Main training routine ─────────────────────────────────────────────────────

def train(data_path: Path | None = None) -> dict:
    """
    Full Phase 2 training pipeline.

    Returns
    -------
    dict with keys 'lr_results' and 'rf_results', each containing
    precision/recall/f1/roc_auc dicts for both models.
    """
    print(f"\n{'='*55}")
    print(f"  F1 Pitstop RL — Baseline Classifier Training")
    print(f"  Imbalance strategy : {IMBALANCE_STRATEGY}")
    print(f"{'='*55}\n")

    # ── 1. Load data ──────────────────────────────────────────────────────────
    logger.info("[1/5] Loading and labelling data…")
    df = load_labelled_data(data_path)

    # ── 2. Season split ───────────────────────────────────────────────────────
    logger.info("[2/5] Splitting by season (train=2022-23, val=2024)…")
    train_df, val_df = season_split(df)

    X_train, y_train = get_feature_matrix(train_df)
    X_val, y_val = get_feature_matrix(val_df)
    feature_names = list(X_train.columns)

    print(f"  Train : {X_train.shape[0]:,} laps, {y_train.sum()} pit stops ({y_train.mean():.1%})")
    print(f"  Val   : {X_val.shape[0]:,} laps, {y_val.sum()} pit stops ({y_val.mean():.1%})\n")

    # ── 3. Handle class imbalance ─────────────────────────────────────────────
    logger.info("[3/5] Handling class imbalance (strategy=%s)…", IMBALANCE_STRATEGY)

    if IMBALANCE_STRATEGY == "smote":
        X_train_fit, y_train_fit = apply_smote(X_train, y_train, random_state=RANDOM_STATE)
        class_weight_param = None
    else:
        X_train_fit, y_train_fit = X_train.values, y_train.values
        class_weight_param = "balanced"

    # ── 4. Train models ───────────────────────────────────────────────────────
    logger.info("[4/5] Training Logistic Regression and Random Forest…")

    lr_pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(
            class_weight=class_weight_param,
            max_iter=1000,
            random_state=RANDOM_STATE,
            solver="lbfgs",
        )),
    ])

    rf_pipeline = Pipeline([
        ("clf", RandomForestClassifier(
            n_estimators=300,
            max_depth=12,
            min_samples_leaf=10,
            class_weight=class_weight_param,
            random_state=RANDOM_STATE,
            n_jobs=-1,
        )),
    ])

    lr_pipeline.fit(X_train_fit, y_train_fit)
    rf_pipeline.fit(X_train_fit, y_train_fit)

    # ── 5. Evaluate ───────────────────────────────────────────────────────────
    logger.info("[5/5] Evaluating on 2024 holdout…")

    lr_results = evaluate("Logistic Regression", lr_pipeline, X_val, y_val)
    rf_results = evaluate("Random Forest     ", rf_pipeline, X_val, y_val)

    # ── Save models ───────────────────────────────────────────────────────────
    joblib.dump(lr_pipeline, MODELS_DIR / "logistic_regression.joblib")
    joblib.dump(rf_pipeline, MODELS_DIR / "random_forest.joblib")
    logger.info("Models saved → %s", MODELS_DIR)

    # ── Feature importance chart (Step 2.3) ───────────────────────────────────
    plot_feature_importance(rf_pipeline, feature_names)

    # ── Summary ───────────────────────────────────────────────────────────────
    best = max([lr_results, rf_results], key=lambda r: r["recall"])
    print(f"\n{'='*55}")
    print(f"  Best model by Recall : {best['name'].strip()}")
    print(f"  Precision : {best['precision']:.4f}")
    print(f"  Recall    : {best['recall']:.4f}  ← PRIMARY")
    print(f"  F1        : {best['f1']:.4f}")
    print(f"  ROC-AUC   : {best['roc_auc']:.4f}")
    print(f"{'='*55}\n")

    return {"lr_results": lr_results, "rf_results": rf_results}


if __name__ == "__main__":
    results = train()
