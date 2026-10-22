import os
import requests
from dotenv import load_dotenv

load_dotenv()
key = os.getenv("RAPIDAPI_KEY") or ""
print("key length:", len(key))
print("has space or quote:", key != key.strip() or '"' in key or "'" in key)

url = "https://cricbuzz-cricket.p.rapidapi.com/matches/v1/live"
headers = {
    "x-rapidapi-key": key,
    "x-rapidapi-host": "cricbuzz-cricket.p.rapidapi.com",
}
r = requests.get(url, headers=headers, timeout=15)
print("status:", r.status_code)
print(r.text[:300])