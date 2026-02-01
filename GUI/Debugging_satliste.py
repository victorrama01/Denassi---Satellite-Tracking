import subprocess
import sys

# Check Chrome version
result = subprocess.run(['wmic', 'datafile', 'where', 'name="C:\\\\Program Files\\\\Google\\\\Chrome\\\\Application\\\\chrome.exe"', 'get', 'Version'], 
                       capture_output=True, text=True)
print("Chrome version:", result.stdout)

# Check system time
import datetime
print("System time:", datetime.datetime.now())

# Test internet connection
import requests
try:
    r = requests.get('https://in-the-sky.org', timeout=5)
    print(f"in-the-sky.org status: {r.status_code}")
except Exception as e:
    print(f"Cannot reach in-the-sky.org: {e}")

# Check webdriver-manager cache
from pathlib import Path
cache_dir = Path.home() / '.wdm'
print(f"WebDriver cache exists: {cache_dir.exists()}")
if cache_dir.exists():
    print(f"Cache contents: {list(cache_dir.glob('*'))}")