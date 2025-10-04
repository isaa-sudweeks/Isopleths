
import pandas as pd
import requests
import time

def clean_address(addr):
    cleaned = str(addr).replace('\xa0', ' ').strip()
    return f"{cleaned}, UT"


def geocode_address(address):
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": address, "format": "json"}
    headers = {"User-Agent": "UDAQ-Geocoder"}
    response = requests.get(url, params=params, headers=headers)
    response.raise_for_status()
    results = response.json()
    if results:
        return float(results[0]['lat']), float(results[0]['lon'])
    return None, None

# Load your UDAQ sites file
df = pd.read_csv("UDAQ sites.csv", encoding="latin1")
df["Full_Address"] = df["Station Address"].apply(clean_address)

latitudes, longitudes = [], []
for addr in df["Full_Address"]:
    lat, lon = geocode_address(addr)
    latitudes.append(lat)
    longitudes.append(lon)
    time.sleep(1)  # avoid rate-limiting

df["Latitude"] = latitudes
df["Longitude"] = longitudes

# Save result
df.to_csv("UDAQ_sites_geocoded.csv", index=False)
print("Done. File saved as UDAQ_sites_geocoded.csv")
