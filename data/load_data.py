import fastf1
import pandas as pd

def load_event(event_name: str, year: int = 2021) -> pd.DataFrame:
    """
    Docstring for load_event
    
    :param event_name: Event Name
        example: "French Grand Prix" 
    :type event_name: str
    :param year: Year of Event
    :type year: int
    :return: event
    :rtype: DataFrame

    Load event data for a given race track and year using the FastF1 API. 
    """
    event = fastf1.get_event(year, event_name)
    return event

def load_session(year: int = 2021, race_id: int = 1, type: str = 'R' ):
    """
    Docstring for load_session
    
    :param year: Year of Event
    :type year: int
    :param race_id: Race Number in Race Season
    :type race_id: int
    :param type: Q-> Qualifiying, R-> Race, etc. 
    :type type: str
    """
    session = fastf1.get_session(year, race_id, type)
    return session

def load_lap_data(session: pd.DataFrame):
    """
    Docstring for load_lap_data
    
    :param session: Session object
    :type session: pd.DataFrame
    """

    session.load() # load session data
    lap_data = session.laps
    return lap_data
