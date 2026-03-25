"""
test_features.py — Smoke test for features.build_feature_matrix.

Uses a fully synthetic, minimal DataFrame so no FastF1 API calls or external
data files are needed. All 5 required output columns are verified.
"""

import unittest
import pandas as pd
import numpy as np

from src.data.features import build_feature_matrix


def _make_synthetic_session(n_laps: int = 12) -> pd.DataFrame:
    """
    Build a small synthetic lap DataFrame that mimics FastF1 output after
    cleaning. Two drivers, one stint each.
    """
    records = []
    rng = np.random.default_rng(42)

    for driver_num in [44, 1]:
        base_time = 90.0 + rng.uniform(-1, 1)
        for lap in range(1, n_laps + 1):
            records.append({
                "Year": 2023,
                "Track": "Bahrain",
                "DriverNumber": driver_num,
                "Stint": 1,
                "LapNumber": lap,
                "LapTime": base_time + lap * 0.12 + rng.normal(0, 0.05),
                "TyreLife": lap,
                "Compound": "SOFT",
                "TrackTemp": 35.0 if lap % 4 != 0 else None,  # some NaN
                "AirTemp": 28.0,
                "TrackStatus": "1" if lap != 5 else "4",  # SC on lap 5
            })

    return pd.DataFrame(records)


class TestBuildFeatureMatrix(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Run once — compute the feature matrix for all test methods."""
        session_df = _make_synthetic_session()
        cls.result = build_feature_matrix(session_df)

    # ── Column presence ─────────────────────────────────────────────────────

    def test_tire_age_column_present(self):
        self.assertIn("tire_age", self.result.columns)

    def test_lap_time_delta_column_present(self):
        self.assertIn("lap_time_delta", self.result.columns)

    def test_degradation_slope_column_present(self):
        self.assertIn("degradation_slope", self.result.columns)

    def test_track_temp_column_present(self):
        self.assertIn("track_temp", self.result.columns)

    def test_track_temp_is_proxy_column_present(self):
        self.assertIn("track_temp_is_proxy", self.result.columns)

    def test_safety_car_flag_column_present(self):
        self.assertIn("safety_car_flag", self.result.columns)

    # ── Value semantics ─────────────────────────────────────────────────────

    def test_tire_age_non_negative(self):
        self.assertTrue((self.result["tire_age"] >= 0).all())

    def test_lap_time_delta_non_negative(self):
        self.assertTrue((self.result["lap_time_delta"] >= 0).all())

    def test_safety_car_flag_is_binary(self):
        vals = self.result["safety_car_flag"].unique()
        self.assertTrue(set(vals).issubset({0, 1}))

    def test_safety_car_triggered_on_lap_5(self):
        """SC is active on lap 5 for both drivers."""
        sc_laps = self.result[self.result["safety_car_flag"] == 1]["LapNumber"].unique()
        self.assertIn(5, sc_laps)

    def test_track_temp_no_nan(self):
        """NaN TrackTemp rows should be filled with AirTemp."""
        self.assertFalse(self.result["track_temp"].isna().any())

    def test_track_temp_proxy_flag_set_for_nan_rows(self):
        """Rows where TrackTemp was NaN should have is_proxy == 1."""
        proxy_rows = self.result[self.result["track_temp_is_proxy"] == 1]
        self.assertGreater(len(proxy_rows), 0)

    def test_degradation_slope_finite(self):
        """No infinities or NaN in degradation slope."""
        self.assertFalse(self.result["degradation_slope"].isna().any())
        self.assertTrue(np.isfinite(self.result["degradation_slope"]).all())

    def test_row_count_unchanged(self):
        """build_feature_matrix must not add or drop rows."""
        session_df = _make_synthetic_session()
        result = build_feature_matrix(session_df)
        self.assertEqual(len(result), len(session_df))

    def test_original_columns_preserved(self):
        """All input columns must still be present in the output."""
        session_df = _make_synthetic_session()
        result = build_feature_matrix(session_df)
        for col in session_df.columns:
            self.assertIn(col, result.columns)


if __name__ == "__main__":
    unittest.main()
