import requests
import json

def process_noaa_rt_stations(stations: list[str], NumberOfPoints: int) -> str:
    data_cols ={"YY":0, "MM":1, "DD":2, "hh":3, "mm":4, "WDIR":5, "WSPD":6, 
                       "GST":7, "WVHT":8, "DPD":9, "APD":10, "MWD":11, "PRES":12, 
                       "ATMP":13, "WTMP":14, "DEWP":15, "VIS": 16, "PTDY":17, "TIDE":18}
    json_formatted_data = {} #dict[str, list[dict[str,str]]]
    #time is in UTC (EST is UTC-5)
    for station in stations:
        data = requests.get(f'https://www.ndbc.noaa.gov/data/realtime2/{station}.txt')
        lines = _noaa_data_to_json(data.text, NumberOfPoints, data_cols)
        json_formatted_data.setdefault(station, []).extend(lines[2:])
    json_output: str = json.dumps(json_formatted_data, indent=4)
    return json_output

#~240 readings per day
def _noaa_data_to_json(url_data: str, numberoflines: int, titles: dict[str, int]) -> list[dict[str,str]]:
    #formats noaa data in a JSON friendly way
    dataarray = []
    temp = [data.split() for data in url_data.split('\n')]
    temp = temp[2:numberoflines+1] #first two indexes are headers
    temp[:] = [[data_point if data_point != "MM" else "" for data_point in data] for data in temp]
    dataarray = [{t:d for (t,d) in zip(titles, data)} for data in temp]
    return dataarray
