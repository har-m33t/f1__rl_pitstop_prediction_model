import fastf1
from fastf1.core import Session
from fastf1.events import Event
import pandas as pd

def get_event_metadata(event_name: str, year: int = 2021) -> Event:
    """
    Docstring for get_event_metadata
    
    :param event_name: Event Name
        example: "French Grand Prix" 
    :type event_name: str
    :param year: Year of Event
    :type year: int
    :return: event
    :rtype: DataFrame

    Load event data for a given race track and year using the FastF1 API. 
    """
    try:
        event = fastf1.get_event(year, event_name)
    except Exception as e: 
        raise ValueError(f"Invalid Event: {event_name} ({year})") from e
    return event

def get_session(year: int = 2021, race_id: int = 1, type: str = 'R' ) -> Session:
    """
    Docstring for get_session
    
    :param year: Year of Event
    :type year: int
    :param race_id: Race Number in Race Season
    :type race_id: int
    :param type: Q-> Qualifiying, R-> Race, etc. 
    :type type: str
    """
    try: 
        session = fastf1.get_session(year, race_id, type)
    except Exception as e: 
        raise ValueError(
            f"Failed to load session: year = {year}, race_id = {race_id}, type = {type}"
            ) from e
    return session

def load_laps_from_session(session: pd.DataFrame):
    """
    Docstring for load_lap_data
    
    :param session: Session object
    :type session: pd.DataFrame
    """

    session.load() # load session data
    lap_data = session.laps
    return lap_data

#TODO As more data is required, use this module to fetch more data from the FastF1 API
