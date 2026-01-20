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

def load_session(year: int = 2021, race_id: int = 1, *additional_info: str ):
    return

def load_lap_data(session: pd.DataFrame):
    return
