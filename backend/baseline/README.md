# F1 Pit Stop Prediction — Baseline Classifier Report

> **Populate this file:** Run `python baseline/train.py` to train on 2022–2024 data  
> and replace the placeholder values below with your actual results.

---

## Experimental Setup

| Setting | Value |
|---|---|
| **Train seasons** | 2022, 2023 |
| **Validation season** | 2024 (holdout — never seen during training) |
| **Split strategy** | Chronological (no shuffling across seasons) |
| **Class imbalance** | `class_weight='balanced'` (default) or SMOTE via `F1_IMBALANCE_STRATEGY=smote` |
| **Primary metric** | **Recall** — missing a pit window costs more than a false alarm in race strategy |

---

## Model Performance — 2024 Holdout

> Replace these values with the output of `python baseline/train.py`.

### Logistic Regression (linear baseline)

| Metric | Score |
|---|---|
| Precision | _run train.py_ |
| **Recall** ← primary | _run train.py_ |
| F1-score | _run train.py_ |
| ROC-AUC | _run train.py_ |

### Random Forest (non-linear baseline)

| Metric | Score |
|---|---|
| Precision | _run train.py_ |
| **Recall** ← primary | _run train.py_ |
| F1-score | _run train.py_ |
| ROC-AUC | _run train.py_ |

---

## Model Comparison

_Fill in after running train.py._

> **Expected winner: Random Forest** — tree-based models handle the non-linear
> interaction between tire age, lap time delta, and safety car periods better
> than a linear model. Logistic Regression is useful as a sanity check and for
> inspecting coefficient signs (feature direction validation).

---

## Top Predictive Features

_Generated from `outputs/feature_importance.png` after training._

| Rank | Feature | Strategic Interpretation |
|---|---|---|
| 1 | _run train.py_ | — |
| 2 | _run train.py_ | — |
| 3 | _run train.py_ | — |

**Expected top features based on domain knowledge:**

1. **`tire_age`** — direct proxy for compound wear; the strongest trigger for a pit window.
2. **`lap_time_delta`** / **`degradation_slope`** — quantify how much pace has been lost, confirming the tire is at end-of-life.
3. **`safety_car_flag`** — free stops under SC are the most strategically exploitable events in F1.

---

## ⚠️ Baseline Threshold

> The DQN must **exceed both thresholds** to be considered an improvement over the supervised baseline.

| Metric | Baseline Threshold |
|---|---|
| **F1-score** | **≥ 0.35** |
| **ROC-AUC** | **≥ 0.80** |
| **Recall** | **≥ 0.60** |

_Thresholds are set conservatively below expected Random Forest performance. Update after running `train.py`._

**Rationale:**  
F1 of 0.35 is meaningful given the severe class imbalance (~5% positive rate). Random chance would yield F1 ≈ 0.09. ROC-AUC of 0.80 demonstrates the model is strongly discriminating between pit and non-pit laps across all probability thresholds.

---

## Reproducing Results

```bash
# Step 1 — Generate processed data (if not already done)
python -m src.data.ingest

# Step 2 — Train both models and generate all outputs
python baseline/train.py
```

**Outputs:**
- `baseline/models/logistic_regression.joblib`
- `baseline/models/random_forest.joblib`
- `outputs/feature_importance.png`
