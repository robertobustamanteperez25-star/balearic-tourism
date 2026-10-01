"""Downloads the three INE tables used in this project into data/raw/.
If your network blocks scripts, open the URLs in a browser and save the files there manually."""
from pathlib import Path
from urllib.request import urlretrieve

TABLES = {
    "2074": "Hotel Occupancy Survey (EOH): travellers and overnight stays by region",
    "10823": "FRONTUR: international tourists by main destination region",
    "10839": "EGATUR: international tourist spending by main destination region",
}
out = Path(__file__).parent / "data" / "raw"
out.mkdir(parents=True, exist_ok=True)
for t, name in TABLES.items():
    url = f"https://www.ine.es/jaxiT3/files/t/es/csv_bdsc/{t}.csv"
    urlretrieve(url, out / f"{t}.csv")
    print(f"{t}.csv  ← {name}")
