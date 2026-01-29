"""
Henter vejrdata fra AAG CloudWatcher SOLO vejrstation
"""

import requests
from typing import Dict, Any, Optional


class CloudWatcherSOLOHenter:
    """Henter vejrdata fra CloudWatcher SOLO"""
    
    def __init__(self, base_url: str = "http://172.16.1.10/"):
        self.url = base_url.rstrip('/') + '/cgi-bin/cgiLastData'
    
    def hent(self) -> Optional[Dict[str, Any]]:
        """Henter vejrdata som dictionary"""
        try:
            response = requests.get(self.url, timeout=5)
            response.raise_for_status()
            
            vejrdata = {}
            for line in response.text.strip().split('\n'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    try:
                        vejrdata[key] = float(value) if '.' in value else int(value)
                    except ValueError:
                        vejrdata[key] = value
            
            return vejrdata
        except Exception as e:
            print(f"Fejl ved hentning af vejrdata: {e}")
            return None


def hent_vejrdata(url: str = "http://172.16.1.10/") -> Optional[Dict[str, Any]]:
    """Simpel funktion til at hente vejrdata"""
    return CloudWatcherSOLOHenter(url).hent()


if __name__ == "__main__":
    vejrdata = hent_vejrdata()
    if vejrdata:
        print("Vejrdata:")
        for key, value in vejrdata.items():
            print(f"  {key}: {value}")
    else:
        print("   ✗ Kunne ikke hente vejrdata")