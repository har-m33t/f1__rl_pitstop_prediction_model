import unittest
import pandas as pd
import numpy as np


# ── Helpers ────────────────────────────────────────────────────────────────

def _make_df(**kwargs) -> pd.DataFrame:
    """Build a minimal lap DataFrame for testing."""
    defaults = {
        "LapTime": [90.0, 91.5, 89.0, 500.0, 50.0],  # 500 and 50 are invalid
        "Sector1Time": [30.0, 31.0, 29.0, 150.0, 20.0],
        "Compound": ["SOFT", "SOFT", "MEDIUM", None, "HARD"],
        "Track": ["Bahrain"] * 5,
        "Rainfall": [None, 0, 0, 0, 1],
        "SpeedI1": [290.0, None, 295.0, 280.0, 305.0],
        "TrackTemp": [35.0, None, 36.0, 34.0, 37.0],
        "AirTemp": [28.0, 29.0, 28.5, 29.0, 27.0],
    }
    defaults.update(kwargs)
    return pd.DataFrame(defaults)


# ── Import under test ──────────────────────────────────────────────────────

from src.data.clean_data import (
    change_time_to_seconds,
    drop_columns,
    filter_invalid_laps,
    handle_missing_categorical_values,
    handle_missing_numeric_values,
    clean_data,
)


class TestChangeTimeToSeconds(unittest.TestCase):

    def test_timedelta_converted_to_float(self):
        df = pd.DataFrame({
            "LapTime": pd.to_timedelta(["0:01:30.000", "0:01:31.500"]),
        })
        result = change_time_to_seconds(df)
        self.assertTrue(pd.api.types.is_float_dtype(result["LapTime"]))
        self.assertAlmostEqual(result["LapTime"].iloc[0], 90.0)

    def test_string_timedelta_converted(self):
        df = pd.DataFrame({"LapTime": ["0 days 00:01:30", "0 days 00:01:31.500"]})
        result = change_time_to_seconds(df)
        self.assertAlmostEqual(result["LapTime"].iloc[0], 90.0)

    def test_missing_column_is_ignored(self):
        df = pd.DataFrame({"Driver": ["HAM", "VER"]})
        result = change_time_to_seconds(df)
        self.assertListEqual(list(result.columns), ["Driver"])


class TestDropColumns(unittest.TestCase):

    def test_drops_targeted_columns(self):
        df = pd.DataFrame({
            "LapTime": [90.0],
            "Deleted": [False],
            "DeletedReason": [""],
            "FastF1Generated": [True],
            "IsAccurate": [True],
            "LapStartDate": ["2022-01-01"],
        })
        result = drop_columns(df)
        self.assertIn("LapTime", result.columns)
        for col in ["Deleted", "DeletedReason", "FastF1Generated", "IsAccurate", "LapStartDate"]:
            self.assertNotIn(col, result.columns)

    def test_missing_columns_ignored(self):
        df = pd.DataFrame({"LapTime": [90.0]})
        result = drop_columns(df)  # Should not raise
        self.assertIn("LapTime", result.columns)


class TestFilterInvalidLaps(unittest.TestCase):

    def test_removes_too_slow(self):
        df = pd.DataFrame({"LapTime": [90.0, 300.0]})
        result = filter_invalid_laps(df)
        self.assertEqual(len(result), 1)
        self.assertEqual(result["LapTime"].iloc[0], 90.0)

    def test_removes_too_fast(self):
        df = pd.DataFrame({"LapTime": [90.0, 30.0]})
        result = filter_invalid_laps(df)
        self.assertEqual(len(result), 1)

    def test_deleted_column_respected_when_present(self):
        df = pd.DataFrame({"LapTime": [90.0, 95.0], "Deleted": [False, True]})
        result = filter_invalid_laps(df)
        self.assertEqual(len(result), 1)
        self.assertEqual(result["LapTime"].iloc[0], 90.0)

    def test_works_without_deleted_column(self):
        """Must not raise when Deleted has already been dropped."""
        df = pd.DataFrame({"LapTime": [90.0, 95.0]})
        result = filter_invalid_laps(df)  # Should not raise
        self.assertEqual(len(result), 2)


class TestHandleMissingCategoricals(unittest.TestCase):

    def test_compound_fillna(self):
        df = pd.DataFrame({"Compound": [None, "SOFT"]})
        result = handle_missing_categorical_values(df)
        self.assertEqual(result["Compound"].iloc[0], "UNKNOWN")

    def test_rainfall_fillna(self):
        df = pd.DataFrame({"Rainfall": [None, 1]})
        result = handle_missing_categorical_values(df)
        self.assertEqual(result["Rainfall"].iloc[0], 0)


class TestCleanDataPipeline(unittest.TestCase):

    def test_pipeline_runs_end_to_end(self):
        df = pd.DataFrame({
            "LapTime": pd.to_timedelta(["0:01:30", "0:01:31", "0 days 00:08:00"]),
            "Compound": [None, "SOFT", "HARD"],
            "Rainfall": [None, 0, 0],
            "Track": ["Bahrain"] * 3,
            "Deleted": [False, False, False],
        })
        result = clean_data(df)
        # The 8-min lap is invalid and must be removed
        self.assertTrue(all(result["LapTime"] < 200))
        # Compound NaN filled
        self.assertNotIn(None, result["Compound"].tolist())
        # Deleted column dropped
        self.assertNotIn("Deleted", result.columns)


if __name__ == "__main__":
    unittest.main()
