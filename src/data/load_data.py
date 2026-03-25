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

def get_session(year: int = 2021, race_id: int = 1, session_type: str = 'R' ) -> Session:
    """
    Docstring for get_session
    
    :param year: Year of Event
    :type year: int
    :param race_id: Race Number in Race Season
    :type race_id: int
    :param session_type: Q-> Qualifiying, R-> Race, etc. 
    :type session_type: str
    """

    try:
        year = int(year)
    except (TypeError, ValueError):
        raise TypeError(f"year must be int, got {type(year).__name__}")
        
    try:
        race_id = int(race_id)
    except (TypeError, ValueError):
        raise TypeError(f"race_id must be int, got {type(race_id).__name__}")
        
    if not isinstance(session_type, str):
        raise TypeError(f"session_type must be str, got {type(session_type).__name__}")

    try: 
        session = fastf1.get_session(year, race_id, session_type)
    except Exception as e: 
        raise ValueError(
            f"Failed to load session: year = {year}, race_id = {race_id}, type = {session_type}"
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

def load_all_data(years: list) -> pd.DataFrame:
    """
    Load lap and weather data for all races in the given years.
    
    :param years: List of years to load data for (e.g., [2021, 2022])
    :type years: list
    :return: DataFrame containing lap and weather data
    :rtype: pd.DataFrame
    """
    all_laps = []
    
    for year in years:
        schedule = fastf1.get_event_schedule(year)
        
        for race_id in schedule['RoundNumber']:
            if race_id == 0:
                continue
            
            try:
                print(f"Loading data for Year: {year}, Race ID: {race_id}")
                sesh = get_session(year, race_id, 'R')
                laps = load_laps_from_session(sesh)
                
                weather_data = laps.get_weather_data()
                laps = laps.reset_index(drop=True)
                weather_data = weather_data.reset_index(drop=True)
                
                joined = pd.concat([laps, weather_data.loc[:, ~(weather_data.columns == 'Time')]], axis=1)
                
                joined['Year'] = year
                event_name = schedule.loc[schedule['RoundNumber'] == race_id, 'EventName'].values[0]
                joined['Track'] = event_name
                
                all_laps.append(joined)
            except Exception as e:
                print(f"Error loading {year} race {race_id}: {e}")
                
    if all_laps:
        return pd.concat(all_laps, ignore_index=True)
    return pd.DataFrame()

if __name__ == "__main__":
    # Test loading data for a specific year's races (e.g., first 3 races of 2021)
    # For full dataset, use `load_all_data([2021, 2022, 2023])`
    schedule = fastf1.get_event_schedule(2021)
    test_race_id = schedule['RoundNumber'].iloc[1] if len(schedule) > 1 else 1

    sesh = get_session(2021, test_race_id)
    laps = load_laps_from_session(sesh)

    weather_data = laps.get_weather_data()
    laps = laps.reset_index(drop = True)
    weather_data = weather_data.reset_index(drop = True)

    joined = pd.concat([laps, weather_data.loc[:, ~(weather_data.columns == 'Time')]], axis =1)
    
    joined['Year'] = 2021
    joined['Track'] = schedule.loc[schedule['RoundNumber'] == test_race_id, 'EventName'].values[0]

    print(joined.head())
    joined.to_csv('lap_data.csv', index=False)
