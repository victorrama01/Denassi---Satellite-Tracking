"""
PWI4 Telescope Client wrapper for satellite tracking.
Replaces ASCOM dependency with direct PWI4 HTTP API calls.
"""

import requests
import time
from datetime import datetime

class PWI4Telescope:
    """
    Wrapper for PlaneWave PWI4 telescope control via HTTP API.
    Provides a simplified interface for satellite tracking operations.
    """
    
    def __init__(self, host="localhost", port=8220, timeout=5):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.base_url = f"http://{host}:{port}"
        self.connected = False
        self.slewing = False
        
    def connect(self):
        """Connect to the PWI4 mount"""
        try:
            response = self.request("/mount/connect")
            self.connected = response['mount']['is_connected']
            return self.connected
        except Exception as e:
            print(f"Fejl ved tilslutning til PWI4: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from the PWI4 mount"""
        try:
            self.request("/mount/disconnect")
            self.connected = False
            return True
        except Exception as e:
            print(f"Fejl ved afbrydelse af PWI4: {e}")
            return False
    
    def slew_to_coordinates(self, ra_hours, dec_degs, coord_type="j2000"):
        """
        Slew telescope to specified RA/DEC coordinates.
        
        Args:
            ra_hours: Right Ascension in hours (0-24)
            dec_degs: Declination in degrees (-90 to +90)
            coord_type: "j2000" or "apparent"
        """
        try:
            if coord_type.lower() == "apparent":
                endpoint = "/mount/goto_ra_dec_apparent"
            else:
                endpoint = "/mount/goto_ra_dec_j2000"
            
            response = self.request(
                endpoint,
                ra_hours=ra_hours,
                dec_degs=dec_degs
            )
            
            self.slewing = response['mount']['is_slewing']
            return True
            
        except Exception as e:
            print(f"Fejl ved slew til RA={ra_hours}, DEC={dec_degs}: {e}")
            return False
    
    def slew_to_alt_az(self, alt_degs, az_degs):
        """
        Slew telescope to specified Alt/Az coordinates.
        
        Args:
            alt_degs: Altitude in degrees
            az_degs: Azimuth in degrees
        """
        try:
            response = self.request(
                "/mount/goto_alt_az",
                alt_degs=alt_degs,
                az_degs=az_degs
            )
            
            self.slewing = response['mount']['is_slewing']
            return True
            
        except Exception as e:
            print(f"Fejl ved slew til ALT={alt_degs}, AZ={az_degs}: {e}")
            return False
    
    def track_satellite_tle(self, sat_name, tle_line1, tle_line2):
        """
        Start tracking a satellite using TLE data.
        
        Args:
            sat_name: Satellite name (line 0 of TLE)
            tle_line1: First TLE line
            tle_line2: Second TLE line
        """
        try:
            response = self.request(
                "/mount/follow_tle",
                line1=sat_name,
                line2=tle_line1,
                line3=tle_line2
            )
            
            return True
            
        except Exception as e:
            print(f"Fejl ved start af satellit tracking: {e}")
            return False
    
    def start_tracking(self):
        """Start sidereal tracking (star field tracking)"""
        try:
            self.request("/mount/tracking_on")
            return True
        except Exception as e:
            print(f"Fejl ved start af sidereal tracking: {e}")
            return False
    
    def stop_tracking(self):
        """Stop tracking"""
        try:
            self.request("/mount/tracking_off")
            return True
        except Exception as e:
            print(f"Fejl ved stop af tracking: {e}")
            return False
    
    def stop_slew(self):
        """Stop current slew operation"""
        try:
            self.request("/mount/stop")
            self.slewing = False
            return True
        except Exception as e:
            print(f"Fejl ved stop af slew: {e}")
            return False
    
    def find_home(self):
        """Find home position (parking)"""
        try:
            self.request("/mount/find_home")
            return True
        except Exception as e:
            print(f"Fejl ved søgning af home position: {e}")
            return False
    
    def park(self):
        """Park the telescope"""
        try:
            self.request("/mount/park")
            return True
        except Exception as e:
            print(f"Fejl ved parkering af teleskop: {e}")
            return False
    
    def offset_ra_dec(self, ra_offset_arcsec=None, dec_offset_arcsec=None):
        """
        Apply offset to current position in RA/DEC.
        
        Args:
            ra_offset_arcsec: RA offset in arcseconds
            dec_offset_arcsec: DEC offset in arcseconds
        """
        try:
            params = {}
            if ra_offset_arcsec is not None:
                params['ra_add_arcsec'] = ra_offset_arcsec
            if dec_offset_arcsec is not None:
                params['dec_add_arcsec'] = dec_offset_arcsec
            
            self.request("/mount/offset", **params)
            return True
            
        except Exception as e:
            print(f"Fejl ved offset: {e}")
            return False
    
    def get_status(self):
        """
        Get current telescope status.
        
        Returns:
            dict with status information
        """
        try:
            status = self.request("/status")
            return {
                'connected': status['mount']['is_connected'],
                'slewing': status['mount']['is_slewing'],
                'tracking': status['mount']['is_tracking'],
                'ra_j2000_hours': status['mount']['ra_j2000_hours'],
                'dec_j2000_degs': status['mount']['dec_j2000_degs'],
                'ra_apparent_hours': status['mount']['ra_apparent_hours'],
                'dec_apparent_degs': status['mount']['dec_apparent_degs'],
                'altitude_degs': status['mount']['altitude_degs'],
                'azimuth_degs': status['mount']['azimuth_degs'],
                'julian_date': status['mount']['julian_date'],
                'field_angle_degs': status['mount']['field_angle_here_degs'],
                'distance_to_sun_degs': status['mount']['distance_to_sun_degs'],
                'latitude_degs': status['site']['latitude_degs'],
                'longitude_degs': status['site']['longitude_degs'],
                'height_meters': status['site']['height_meters']
            }
        except Exception as e:
            print(f"Fejl ved hentning af status: {e}")
            return None
    
    def wait_for_slew_complete(self, timeout_seconds=300):
        """
        Wait for slew to complete.
        
        Args:
            timeout_seconds: Maximum time to wait
            
        Returns:
            True if slew completed, False if timeout
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            try:
                status = self.get_status()
                if status and not status['slewing']:
                    self.slewing = False
                    return True
                time.sleep(0.5)
            except:
                time.sleep(0.5)
        
        print(f"Timeout ved venten på slew (>{timeout_seconds}s)")
        return False
    
    def is_slewing(self):
        """Check if telescope is currently slewing"""
        try:
            status = self.get_status()
            if status:
                self.slewing = status['slewing']
                return self.slewing
        except:
            pass
        return False
    
    def request(self, endpoint, **params):
        """
        Make HTTP request to PWI4.
        
        Args:
            endpoint: API endpoint (e.g., "/status")
            **params: Query parameters
            
        Returns:
            Parsed response dict
        """
        url = self.base_url + endpoint
        
        try:
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            # Parse response
            return self._parse_response(response.text)
            
        except requests.exceptions.Timeout:
            raise Exception(f"PWI4 timeout efter {self.timeout}s")
        except requests.exceptions.ConnectionError:
            raise Exception(f"Kan ikke forbinde til PWI4 på {self.host}:{self.port}")
        except Exception as e:
            raise Exception(f"PWI4 request fejl: {str(e)}")
    
    def _parse_response(self, response_text):
        """Parse PWI4 text response into nested dict"""
        response_dict = {}
        lines = response_text.strip().split('\n')
        
        for line in lines:
            if '=' not in line:
                continue
            
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip()
            
            # Convert value to appropriate type
            if value.lower() == 'true':
                value = True
            elif value.lower() == 'false':
                value = False
            else:
                try:
                    value = float(value)
                except ValueError:
                    pass
            
            # Create nested dict structure (e.g., "mount.ra_j2000_hours" -> response['mount']['ra_j2000_hours'])
            parts = key.split('.')
            current = response_dict
            
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            
            current[parts[-1]] = value
        
        return response_dict
    
    def test_connection(self):
        """Test if connection to PWI4 is working"""
        try:
            status = self.request("/status")
            return status is not None
        except Exception as e:
            print(f"Test forbindelse fejlede: {e}")
            return False
