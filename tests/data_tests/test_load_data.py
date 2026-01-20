import unittest
from unittest.mock import patch, MagicMock
import pandas as pd

from src.data.load_data import load_event, load_session, load_lap_data

EVENT = "French Grand Prix"
YEAR = 2021


class TestLoadEvent(unittest.TestCase):

    @patch("src.data.load_data.fastf1.get_event")
    def test_load_event_regular(self, mock_get_event):
        mock_event = MagicMock()
        mock_event.EventName = EVENT
        mock_get_event.return_value = mock_event

        event = get_event_metadata(EVENT, YEAR)
        self.assertIs(event, mock_event)
        mock_get_event.assert_called_once_with(YEAR, EVENT)

    @patch("src.data.load_data.fastf1.get_event")
    def test_load_event_doesnt_exist(self, mock_get_event):
        mock_get_event.side_effect = Exception("Event not found")

        with self.assertRaises(ValueError):
            get_event_metadata("Fake GP", YEAR)

    def test_load_event_improper_type(self):
        with self.assertRaises(TypeError):
            get_event_metadata(123, YEAR)  # event_name must be str

    
class TestLoadSession(unittest.TestCase):

    @patch("src.data.load_data.fastf1.get_session")
    def test_load_session_regular(self, mock_get_session):
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        session = get_session(YEAR, 1, "R")

        self.assertIs(session, mock_session)
        mock_get_session.assert_called_once_with(YEAR, 1, "R")

    @patch("src.data.load_data.fastf1.get_session")
    def test_load_session_doesnt_exist(self, mock_get_session):
        mock_get_session.side_effect = Exception("Invalid session")

        with self.assertRaises(ValueError):
            get_session(YEAR, 99, "R")

    def test_load_session_improper_type(self):
        with self.assertRaises(TypeError):
            get_session("2021", "one", 5)


class TestLoadLapData(unittest.TestCase):

    def test_load_lap_data_regular(self):
        mock_session = MagicMock()
        mock_session.laps = pd.DataFrame({"LapTime": [1, 2, 3]})

        df = load_laps_from_session(mock_session)

        mock_session.load.assert_called_once()
        self.assertIsInstance(df, pd.DataFrame)
        self.assertFalse(df.empty)

    def test_load_lap_data_session_doesnt_exist(self):
        with self.assertRaises(AttributeError):
            load_laps_from_session(None)

    def test_load_lap_data_improper_type(self):
        with self.assertRaises(AttributeError):
            load_laps_from_session("not a session")
