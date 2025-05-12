#!/usr/bin/python -u
# built-ins
from datetime import datetime
import json
import requests
import re

# external dependencies
from bs4 import BeautifulSoup

def process_noaa_rt_stations(stations: list[str]) -> str:
    """
    Processes real-time NOAA data for a list of stations and formats it into a JSON-friendly format.

    Args:
        stations (list[str]): A list of station identifiers (e.g., "BLTM2", "CHCM2").

    Returns:
        str: A JSON-formatted string of processed data, or None if no data was found.
    """
    if not isinstance(stations, list):
        return None
    data_cols = ["YY", "MM", "DD", "hh", "mm", "WDIR", "WSPD", 
                    "GST", "WVHT", "DPD", "APD", "MWD", "PRES", 
                    "ATMP", "WTMP", "DEWP", "VIS", "PTDY", "TIDE"]
    processed_data = []
    #time is in UTC (EST is UTC-5)
    for station in stations:
        data = requests.get(f'https://www.ndbc.noaa.gov/data/realtime2/{station}.txt')
        lines = _aggregate_noaa_data(data.text, data_cols)
        if lines is None:
            continue
        processed_data.extend(lines)
    if processed_data == []:
        return None
    params = _batch_noaa_data(processed_data, data_cols)
    chart_data = _convert_to_chart_data(params, data_cols)
    json_data = json.dumps(chart_data, indent=4)
    return json_data

#~240 readings per day
def _aggregate_noaa_data(url_data: str, titles: list[str]) -> list[dict[str,str]] | None:
    """
    Aggregates NOAA data from the raw text into a list of dictionaries, one dictionary per reading.

    Args:
        url_data (str): Raw text data retrieved from NOAA for a given station.
        titles (list[str]): List of column names to be used as dictionary keys.

    Returns:
        list[dict[str,str]]: A list of dictionaries where each dictionary represents one data point
        None: Data retrieval failed due to page not existing.
    """
    dataarray = []
    if "404 Not Found" in url_data:
        return None
    lines = [data.split() for data in url_data.split('\n')]
    # First two lines are headers and last line could be empty
    # Read in lines in reverse so final JSON is in ascending order
    lines = lines[-2:3:-1] 
    dataarray = [{t:d for (t,d) in zip(titles, data)} for data in lines]
    return dataarray

def _batch_noaa_data(unbatched_data: dict[str, str], titles: list[str]) -> dict[str, dict[str, float | str]]:
    """
    Batches the NOAA data into daily averages for each parameter and rounds the results to one decimal place.

    Args:
        unbatched_data (dict[str, str]): A list of dictionaries where each dictionary represents
            individual parameter data for a specific timestamp.
        titles (list[str]): A list of column names (parameters), including date/time fields and measured variables.

    Returns:
        dict[str, dict[str, float | str]]: A dictionary where:
            - Each key is a date string in 'YY-MM-DD' format.
            - Each value is a dictionary mapping parameter names (e.g., 'WSPD', 'WTMP') to:
                - The averaged float value for that day, rounded to one decimal place, or
                - An empty string if no valid data points were available.
    """
    titles = titles[5:] # First five are the date and time
    parameters = {}
    for time_point in unbatched_data:
        date = f"{time_point['YY']}-{time_point['MM']}-{time_point['DD']}"
        parameters.setdefault(date, {title:[] for title in titles}) # Sets empty list for each param
        for key in titles:
            if time_point[key] != "MM": # Adds all not null values to list
                parameters[date][key].append(float(time_point[key]))
    for date in parameters:
        for title in titles:
            data_points = parameters[date][title] # Grabs list of data points per param per day
            if data_points != [] and isinstance(data_points, list):
                # Averages points per param per day
                parameters[date][title] = round(sum(data_points)/len(data_points), 1)
            elif data_points == []:
                parameters[date][title] = ""
    return parameters

def _convert_to_chart_data(parameters: [dict[str, str]], titles: list[str]) -> str:
    """
    Converts date-keyed NOAA parameter data into a list of chart-ready dictionaries.

    Each dictionary in the output corresponds to a single parameter and includes:
      - 'name': the parameter name (e.g., 'WTMP')
      - 'labels': list of date strings (e.g., '2025-05-09') where valid data is present
      - 'values': corresponding list of parameter values for those dates

    Args:
        parameters (dict[str, dict[str, str | float]]): Dictionary with dates as keys and parameter-value dictionaries as values.
        titles (list[str]): Full list of NOAA column titles (including date/time fields).

    Returns:
        list[dict[str, list]]: A list of dictionaries, each containing 'name', 'labels', and 'values' for a single parameter.
    """
    titles = titles[5:]
    chart_data = {title: {"name": title, "labels": [], "values": []} for title in titles}
    for date in parameters:
        label = datetime.strptime(date, "%Y-%m-%d").strftime("%b %d")
        for title in titles:
            value = parameters[date].get(title)
            if value != "":
                chart_data[title]["labels"].append(label)
                chart_data[title]["values"].append(value)
    return list(chart_data.values())
