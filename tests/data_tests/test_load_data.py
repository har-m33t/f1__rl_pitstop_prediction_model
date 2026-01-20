import unittest
from unittest.mock import patch, MagicMock
import pandas as pd

from src.data.load_data import load_event, load_session, load_lap_data

EVENT = "French Grand Prix"
YEAR = 2021


class TestLoadEvent(unittest.TestCase):
    def test_load_event_regular(self):
        event = load_event(EVENT, YEAR)

        self.assertIsInstance(event, pd.DataFrame)
        self.assertEqual(event['EventName'], 'French Grand Prix')
    
    def test_load_event_doesnt_exist():
        return 
    
    def test_load_event_improper_type():
        return

    
class TestLoadSession(unittest.TestCase):
    def test_load_session_regular():
        return
    
    def test_load_session_doesnt_exist():
        return 
    
    def test_load_session_improper_type():
        return

class TestLoadLapData(unittest.TestCase):
    def test_load_lap_data_regular():
        return
    
    def test_load_lap_data_session_doesnt_exist():
        return 
    
    def test_load_session_improper_type():
        return
