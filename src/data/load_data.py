import fastf1
from fastf1.core import Session
from fastf1.events import Event
import pandas as pd

fastf1.Cache.enable_cache("data/raw") # store data locally for performance


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

    if not isinstance(event_name, str):
        raise TypeError(f"event_name must be str, got {type(event_name).__name__}")
    
    if not isinstance(year, int):
        raise TypeError(f"year must be int, got {type(year).__name__}")

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

    if not isinstance(year, int):
        raise TypeError(f"year must be int, got {type(year).__name__}")
    if not isinstance(race_id, int):
        raise TypeError(f"race_id must be int, got {type(race_id).__name__}")
    if not isinstance(type, str):
        raise TypeError(f"session_type must be str, got {type(type).__name__}")

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
    laps = session.laps
    if laps.empty:
        raise ValueError("Loaded session contains no lap data")
    return laps.copy()

#TODO As more data is required, use this module to fetch more data from the FastF1 API

if __name__ == "__main__":
    sesh = get_session(2021, 8)
    laps = load_laps_from_session(sesh)

    weather_data = laps.get_weather_data()
    laps = laps.reset_index(drop = True)
    weather_data = weather_data.reset_index(drop = True)

    joined = pd.concat([laps, weather_data.loc[:, ~(weather_data.columns == 'Time')]], axis =1)
    print(joined)
    joined.to_csv('lap_data.csv')


