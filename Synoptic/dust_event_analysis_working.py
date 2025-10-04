# Dust Event Detection Script (Auto-Matching + Wind Analysis + EPA PM10)

import pandas as pd
import requests
import time
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from geopy.distance import geodesic
import matplotlib.pyplot as plt
from windrose import WindroseAxes
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

DUST_VISIBILITY_THRESHOLD = 400  # meters
DUST_DURATION_THRESHOLD_HOURS = 0.2  # 130 min
MESOWEST_TOKEN = os.getenv("MESOWEST_TOKEN", "demotoken")
EPA_EMAIL = "callumf@byu.edu"
EPA_KEY = "dunfrog78"
print(f"Using Synoptic token: {MESOWEST_TOKEN[:5]}...")

# ----------------------------
# MesoWest Station Lookup (Auto)
# ----------------------------
def find_nearest_station(site_id: str, site_lat, site_lon, variable="visibility"):
    url = "https://api.synopticdata.com/v2/stations/metadata"
    params = {
        "token": MESOWEST_TOKEN,
        "vars": variable,
        "within": "25",
        "radius": f"{site_lat},{site_lon},25",
        "status": "active",
        "output": "json"
    }
    response = requests.get(url, params=params)
    stations = response.json().get("STATION", [])

    best_station = None
    best_dist = float("inf")
    for s in stations:
        s_lat = float(s["LATITUDE"])
        s_lon = float(s["LONGITUDE"])
        dist = geodesic((site_lat, site_lon), (s_lat, s_lon)).km
        if dist < best_dist:
            best_station = s["STID"]
            best_dist = dist

    return best_station

# ----------------------------
# Fetch Data from MesoWest API
# ----------------------------
def fetch_mesowest_data(station: str, start: str, end: str, vars="visibility,wind_speed,wind_direction,relative_humidity") -> pd.DataFrame:
    """Fetch timeseries data from Synoptic/MesoWest.
    We omit `weather_cond` because that variable name is not supported on many stations.
    The precipitation filter will simply be skipped when weather codes are absent.
    """
    url = "https://api.synopticdata.com/v2/stations/timeseries"
    params = {
        "token": MESOWEST_TOKEN,
        "start": start,
        "end": end,
        "stid": station,
        "vars": vars,
        "obtimezone": "local",
        "output": "json"
    }
    response = requests.get(url, params=params)
    data = response.json()
    if not data.get("SUMMARY") or data["SUMMARY"].get("RESPONSE_CODE") != 1:
        raise ValueError(f"Failed to fetch data for {station}: {data.get('SUMMARY')}")

    station_data = data['STATION'][0]['OBSERVATIONS']
    timestamps = station_data['date_time']
    df = pd.DataFrame({"datetime": pd.to_datetime(timestamps)})

    for var in station_data:
        if var != "date_time":
            df[var] = station_data[var]
    return df

if __name__ == "__main__":
    udaq_sites = pd.read_csv("UDAQ sites.csv", encoding="latin1").rename(columns=str.strip)
    for year in range(2015, 2025):
        print(f"\n==================== Processing Year: {year} ====================\n")
        #process_sites_auto(udaq_sites, year=year)
