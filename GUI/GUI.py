import tkinter as tk
from tkinter import ttk, messagebox, filedialog, colorchooser
from tkinter import Menu, Canvas, Text, Scrollbar
import threading
from datetime import datetime, date, timedelta
import pandas as pd
import numpy as np
import time
import os
import re

# Import dine funktioner fra Heavens-Above koden
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.service import Service
    from bs4 import BeautifulSoup
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        WEBDRIVER_MANAGER_AVAILABLE = True
    except ImportError:
        WEBDRIVER_MANAGER_AVAILABLE = False
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    WEBDRIVER_MANAGER_AVAILABLE = False
    
import re
import requests

# Import leapfrog funktioner
try:
    from Func_fagprojekt import calculate_satellite_data, ra_dec_to_eci
    from skyfield.api import Topos, load, EarthSatellite
    SKYFIELD_AVAILABLE = True
except ImportError:
    SKYFIELD_AVAILABLE = False

# Import til plotly plots
try:
    import plotly.graph_objects as go
    import plotly.offline as pyo
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

# Import til PWI4 teleskop kontrol (erstatter ASCOM)
try:
    from pwi4_client import PWI4Telescope
    from astropy.io import fits
    PWI4_AVAILABLE = True
except ImportError:
    PWI4_AVAILABLE = False

# Import Moravian kamera support
try:
    from moravian_camera_official import MoravianCameraOfficial
    MORAVIAN_AVAILABLE = True
except ImportError:
    MORAVIAN_AVAILABLE = False

# Import til billede analyse
try:
    from skimage import morphology
    import cv2
    from scipy.ndimage import zoom, label, find_objects
    from scipy.ndimage import zoom
    import subprocess
    from tqdm import tqdm
    from matplotlib.patches import Circle
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from PIL import Image, ImageTk
    plt.ioff()  # Turn off interactive mode for GUI integration
    SKIMAGE_AVAILABLE = True
except ImportError:
    SKIMAGE_AVAILABLE = False
    plt = None
    FigureCanvasTkAgg = None

# Import til TLE beregning (orbdtools)
try:
    from orbdtools import ArcObs, Body, KeprvTrans
    from astropy.time import Time
    ORBDTOOLS_AVAILABLE = True
except ImportError:
    ORBDTOOLS_AVAILABLE = False

class TkinterDemo:
    def __init__(self, root):
        self.root = root
        self.root.title("Denassi - Specialkursus 2025")
        self.root.geometry("1200x800")
        
        # Satelit data variabler
        self.df_merged = None
        self.df_heavens = None
        
        # LeapFrog variabler
        self.df_leapfrog = None
        self.leapfrog_observation_running = False
        self.stop_observation = False
        
        # Tracking variabler
        self.tracking_running = False
        self.stop_tracking = False
        self.selected_tracking_satellite = None
        self.tracking_base_url = "http://localhost:8220"
        
        # Billede analyse variabler
        self.image_analysis_running = False
        self.stop_image_analysis = False
        self.analysis_directory = None
        self.tracking_pixelsum_radius = tk.IntVar(value=50)
        
        # Billedgennemgang variabler
        self.review_files = []
        self.review_index = 0
        self.review_directory = None
        self.review_downscale = 2
        
        # Beregn TLE variabler
        self.tle_calculation_data = None
        self.tle_csv_directory = None
        self.tle_plot_figure = None
        self.tle_csv_data = None  # DataFrame med indlæst CSV data
        self.tle_result = None  # Resultat fra TLE beregning
        self.selected_indices = [0, 1, 2]  # Valgte indices til TLE beregning
        
        # Moravian kamera variabler
        self.moravian_camera = None
        self.camera_connected = False
        self.camera_gain = tk.IntVar(value=1)
        self.camera_binning_x = tk.IntVar(value=2)
        self.camera_binning_y = tk.IntVar(value=2)
        self.selected_filter = tk.StringVar()
        
        # PWI4 teleskop
        self.pwi4_client = None
        self.pw4_url = "http://localhost:8220"
        
        # UR VARIABEL
        self.clock_var = tk.StringVar()
        
        self.create_menu()
        self.create_widgets()
        self.update_clock()  # Start uret
    
    def create_menu(self):
        """Wrapper for menu creation from Func_menu"""
        from Func_menu import create_menu as menu_func
        menu_func(self)
    
    def create_widgets(self):
        """Wrapper for widgets creation from Func_menu"""
        from Func_menu import create_widgets as widgets_func
        widgets_func(self)
    
    def update_clock(self):
        """Wrapper for update_clock from Func_menu"""
        from Func_menu import update_clock as clock_func
        clock_func(self)
    
    def update_satellite_colors(self):
        """Wrapper for update_satellite_colors from Func_menu"""
        from Func_menu import update_satellite_colors as colors_func
        colors_func(self)
    
    def sort_dataframe_by_starttime(self, df):
        """Wrapper for sort_dataframe_by_starttime from Func_menu"""
        from Func_menu import sort_dataframe_by_starttime as sort_func
        return sort_func(self, df)
    
    def create_kameraindstillinger_tab(self, notebook):
        """Wrapper for kameraindstillinger tab from Func_KameraInstillinger"""
        from Func_KameraInstillinger import create_kameraindstillinger_tab as kamera_func
        kamera_func(self, notebook)
    
    def create_satellite_tab(self, notebook):
        """Wrapper for satellite tab from Func_SatellitListe"""
        from Func_SatellitListe import create_satellite_tab as satellite_func
        satellite_func(self, notebook)
    
    def create_leapfrog_tab(self, notebook):
        """Wrapper for leapfrog tab from Func_Leapfrog"""
        from Func_Leapfrog import create_leapfrog_tab as leapfrog_func
        leapfrog_func(self, notebook)
    
    def create_tracking_tab(self, notebook):
        """Wrapper for tracking tab from Func_Tracking"""
        from Func_Tracking import create_tracking_tab as tracking_func
        tracking_func(self, notebook)
    
    def create_image_analysis_tab(self, notebook):
        """Wrapper for image analysis tab from Func_BilledeAnalyse"""
        from Func_BilledeAnalyse import create_image_analysis_tab as analysis_func
        analysis_func(self, notebook)
    
    def create_image_review_tab(self, notebook):
        """Wrapper for image review tab from Func_BilledGennemgang"""
        from Func_BilledGennemgang import create_image_review_tab as review_func
        review_func(self, notebook)
    
    def create_calculate_tle_tab(self, notebook):
        """Wrapper for calculate TLE tab from Func_CalculateTLE"""
        from Func_CalculateTLE import create_calculate_tle_tab as tle_func
        tle_func(self, notebook)

    # ================
    # Billedgennemgang Funktioner
    # ================
    def select_review_directory(self):
        """Wrapper for select_review_directory from Func_BilledGennemgang"""
        from Func_BilledGennemgang import select_review_directory as func
        func(self)
    
    def load_review_images(self):
        """Wrapper for load_review_images from Func_BilledGennemgang"""
        from Func_BilledGennemgang import load_review_images as func
        func(self)
    
    def show_review_image(self):
        """Wrapper for show_review_image from Func_BilledGennemgang"""
        from Func_BilledGennemgang import show_review_image as func
        func(self)
    
    def review_keep_file(self):
        """Wrapper for review_keep_file from Func_BilledGennemgang"""
        from Func_BilledGennemgang import review_keep_file as func
        func(self)
    
    def review_delete_file(self):
        """Wrapper for review_delete_file from Func_BilledGennemgang"""
        from Func_BilledGennemgang import review_delete_file as func
        func(self)
    
    def review_next_image(self):
        """Wrapper for review_next_image from Func_BilledGennemgang"""
        from Func_BilledGennemgang import review_next_image as func
        func(self)
    
    def review_log_message(self, message):
        """Wrapper for review_log_message from Func_BilledGennemgang"""
        from Func_BilledGennemgang import review_log_message as func
        func(self, message)
    
    # ================
    # Satelit Hentning Funktioner - Wrappers
    # ================
    def get_satellite_status(self, start_time_str, end_time_str, selected_date):
        """Wrapper for get_satellite_status from Func_SatellitListe"""
        from Func_SatellitListe import get_satellite_status as func
        return func(self, start_time_str, end_time_str, selected_date)

    def fetch_satellites_threaded(self):
        """Wrapper for fetch_satellites_threaded from Func_SatellitListe"""
        from Func_SatellitListe import fetch_satellites_threaded as func
        return func(self)

    def fetch_satellites(self):
        """Wrapper for fetch_satellites from Func_SatellitListe"""
        from Func_SatellitListe import fetch_satellites as func
        return func(self)

    def update_satellite_tree(self):
        """Wrapper for update_satellite_tree from Func_SatellitListe"""
        from Func_SatellitListe import update_satellite_tree as func
        return func(self)

    def save_satellite_list(self):
        """Wrapper for save_satellite_list from Func_SatellitListe"""
        from Func_SatellitListe import save_satellite_list as func
        return func(self)

    def clear_satellite_list(self):
        """Wrapper for clear_satellite_list from Func_SatellitListe"""
        from Func_SatellitListe import clear_satellite_list as func
        return func(self)

    def load_csv_file(self):
        """Wrapper for load_csv_file from Func_SatellitListe"""
        from Func_SatellitListe import load_csv_file as func
        return func(self)

    def validate_csv_data(self, df):
        """Wrapper for validate_csv_data from Func_SatellitListe"""
        from Func_SatellitListe import validate_csv_data as func
        return func(self, df)

    def fetch_active_tles(self, username, password):
        """Wrapper for fetch_active_tles from Func_SatellitListe"""
        from Func_SatellitListe import fetch_active_tles as func
        return func(self, username, password)

    def fetch_satellite_data_selenium(self, date, lat=55.781553, lng=12.514595, period='morning'):
        """Wrapper for fetch_satellite_data_selenium from Func_SatellitListe"""
        from Func_SatellitListe import fetch_satellite_data_selenium as func
        return func(self, date, lat, lng, period)

    def fetch_satellite_data_with_tle(self, date, username, password, lat=55.781553, lng=12.514595, period='morning', utc_offset=2):
        """Wrapper for fetch_satellite_data_with_tle from Func_SatellitListe"""
        from Func_SatellitListe import fetch_satellite_data_with_tle as func
        return func(self, date, username, password, lat, lng, period, utc_offset)

    def open_file(self):
        """Wrapper for open_file from Func_SatellitListe"""
        from Func_SatellitListe import open_file as func
        return func(self)

    def load_csv_file_direct(self, filename):
        """Wrapper for load_csv_file_direct from Func_SatellitListe"""
        from Func_SatellitListe import load_csv_file_direct as func
        return func(self, filename)

    def save_file(self):
        """Wrapper for save_file from Func_SatellitListe"""
        from Func_SatellitListe import save_file as func
        return func(self)
    def show_about(self):
        messagebox.showinfo("Om", "Satellite Tracking GUI - Udviklet til specialkursus og fagprojekt \n af Victor Rama Vestergaard og Viggo Fischer")
    
    # =================
    # MORAVIAN KAMERA KONTROL METODER
    # =================
    
    def log_camera_message(self, message):
        """Wrapper: Tilføj besked til kamera loggen med tidsstempel"""
        from Func_KameraInstillinger import log_camera_message as func
        return func(self, message)
    
    def log_satellite_message(self, message):
        """Wrapper: Tilføj besked til satelit loggen med tidsstempel"""
        from Func_KameraInstillinger import log_satellite_message as func
        return func(self, message)
    
    def connect_camera(self):
        """Wrapper: Tilslut til Moravian kamera"""
        from Func_KameraInstillinger import connect_camera as func
        return func(self)
    
    def disconnect_camera(self):
        """Wrapper: Afbryd forbindelse til Moravian kamera"""
        from Func_KameraInstillinger import disconnect_camera as func
        return func(self)
    
    def update_camera_info(self):
        """Wrapper: Opdater kamera information i GUI"""
        from Func_KameraInstillinger import update_camera_info as func
        return func(self)
    
    def update_temperature_display(self):
        """Wrapper: Opdater temperatur display"""
        from Func_KameraInstillinger import update_temperature_display as func
        return func(self)
    
    def update_gain_label(self, value):
        """Wrapper: Opdater gain værdi label når slider bevæges"""
        from Func_KameraInstillinger import update_gain_label as func
        return func(self, value)
    
    def set_camera_gain(self):
        """Wrapper: Sæt kamera gain"""
        from Func_KameraInstillinger import set_camera_gain as func
        return func(self)
    
    def set_camera_binning(self):
        """Wrapper: Sæt kamera binning"""
        from Func_KameraInstillinger import set_camera_binning as func
        return func(self)
    
    def set_camera_filter(self):
        """Wrapper: Sæt kamera filter"""
        from Func_KameraInstillinger import set_camera_filter as func
        return func(self)
    
    def take_test_image(self):
        """Wrapper: Tag et testbillede med 1 sekunds eksponering og fuld FITS header"""
        from Func_KameraInstillinger import take_test_image as func
        return func(self)
    
    def get_camera_for_observation(self):
        """Wrapper: Hent kamera til brug i observationer - returnerer None hvis ikke tilgængelig"""
        from Func_KameraInstillinger import get_camera_for_observation as func
        return func(self)
    
    def get_current_filter_name(self):
        """Wrapper: Hent navn på det aktuelt valgte filter"""
        from Func_KameraInstillinger import get_current_filter_name as func
        return func(self)
    
    def create_standard_fits_header(self, obstype, sat_name, exposure_start_time, exposure_end_time, 
                                   exposure_time, tle1, tle2, norad_id, camera=None, pw4_status=None, 
                                   ra_hours=None, dec_degrees=None, alt_degrees=None, az_degrees=None,
                                   image_width=None, image_height=None, x_binning=1, y_binning=1, filter_name=None,
                                   mid_exposure_time=None):
        """Wrapper: Opretter en standard FITS header til både LeapFrog og Tracking observationer"""
        from Func_KameraInstillinger import create_standard_fits_header as func
        return func(self, obstype, sat_name, exposure_start_time, exposure_end_time, 
                   exposure_time, tle1, tle2, norad_id, camera, pw4_status, 
                   ra_hours, dec_degrees, alt_degrees, az_degrees,
                   image_width, image_height, x_binning, y_binning, filter_name,
                   mid_exposure_time)

    # =================
    # LEAPFROG METODER
    # =================
    
    def log_message(self, message):
        """Wrapper: Tilføj besked til log"""
        from Func_Leapfrog import log_message as func
        return func(self, message)
    
    def get_selected_satellite(self):
        """Wrapper: Henter den valgte satellit fra satellitlisten"""
        from Func_Leapfrog import get_selected_satellite as func
        return func(self)
    
    def get_full_tle_from_selection(self, item):
        """Wrapper: Henter fulde TLE linjer fra den valgte satellit"""
        from Func_Leapfrog import get_full_tle_from_selection as func
        return func(self, item)
    
    def calculate_leapfrog_data(self):
        """Wrapper: Beregner LeapFrog data baseret på valgt satellit"""
        from Func_Leapfrog import calculate_leapfrog_data as func
        return func(self)
    
    def xyz_to_radec(self, x, y, z):
        """Wrapper: Konverter XYZ til RA/DEC"""
        from Func_Leapfrog import xyz_to_radec as func
        return func(x, y, z)
    
    def ra_deg_to_hms(self, ra_deg_array):
        """Wrapper: Konverter RA grader til HH:MM:SS format"""
        from Func_Leapfrog import ra_deg_to_hms as func
        return func(ra_deg_array)
    
    def tle_to_altaz(self, tle1, tle2, observer_lat, observer_lon, observer_ele, datetime_list, name="SAT"):
        """Wrapper: Beregn Alt/Az fra TLE"""
        from Func_Leapfrog import tle_to_altaz as func
        return func(self, tle1, tle2, observer_lat, observer_lon, observer_ele, datetime_list, name)
    
    def update_leapfrog_table(self):
        """Wrapper: Opdater LeapFrog data tabel"""
        from Func_Leapfrog import update_leapfrog_table as func
        return func(self)
    
    def show_leapfrog_plot(self):
        """Wrapper: Vis 3D plot af LeapFrog data"""
        from Func_Leapfrog import show_leapfrog_plot as func
        return func(self)
    
    def start_leapfrog_observation(self):
        """Wrapper: Start LeapFrog observation i separat tråd"""
        from Func_Leapfrog import start_leapfrog_observation as func
        return func(self)
    
    def stop_leapfrog_observation(self):
        """Wrapper: Stop LeapFrog observation"""
        from Func_Leapfrog import stop_leapfrog_observation as func
        return func(self)
    
    def wait_until(self, target_time):
        """Wrapper: Vent til det ønskede tidspunkt"""
        from Func_Leapfrog import wait_until as func
        return func(self, target_time)
    
    def hms_to_hours(self, hms_str):
        """Wrapper: Konverter RA HH:MM:SS.sss til decimal timer"""
        from Func_Leapfrog import hms_to_hours as func
        return func(self, hms_str)
    
    def run_leapfrog_observation(self):
        """Wrapper: Kør LeapFrog observation"""
        from Func_Leapfrog import run_leapfrog_observation as func
        return func(self)
    
    def _execute_leapfrog_observation(self):
        """Wrapper: Kør rigtig observation med PWI4"""
        from Func_Leapfrog import _execute_leapfrog_observation as func
        return func(self)
    

    # =================
    # TRACKING METODER
    # =================
    
    def tracking_log_message(self, message):
        """Tilføj besked til tracking log"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.tracking_log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.tracking_log_text.see(tk.END)
        self.root.update()
    
    def test_pw4_connection(self):
        """Test forbindelse til PlaneWave4"""
        try:
            url = self.pw4_url_entry.get().strip()
            if not url:
                self.pw4_status_label.config(text="Status: Ingen URL angivet", foreground='red')
                return
                
            self.pw4_status_label.config(text="Status: Tester forbindelse...", foreground='orange')
            self.root.update()
            
            # Prøv forskellige endpoints for at teste forbindelsen
            test_endpoints = ["/status", "/", "/mount/follow_tle"]
            
            for endpoint in test_endpoints:
                try:
                    response = requests.get(f"{url}{endpoint}", timeout=5)
                    if response.status_code in [200, 405]:  # 405 = Method Not Allowed (men server svarer)
                        self.pw4_status_label.config(text="Status: Forbindelse OK ✓", foreground='green')
                        self.tracking_log_message(f"PlaneWave4 forbindelse OK (testet {endpoint})")
                        return
                except:
                    continue
            
            # Hvis ingen endpoints svarede positivt
            self.pw4_status_label.config(text="Status: Ingen gyldige endpoints", foreground='red')
            self.tracking_log_message("PlaneWave4: Ingen kendte endpoints svarede")
                
        except requests.exceptions.Timeout:
            self.pw4_status_label.config(text="Status: Timeout", foreground='red')
            self.tracking_log_message("PlaneWave4 forbindelse timeout")
        except requests.exceptions.ConnectionError:
            self.pw4_status_label.config(text="Status: Kan ikke forbinde", foreground='red')
            self.tracking_log_message("Kan ikke forbinde til PlaneWave4")
        except Exception as e:
            self.pw4_status_label.config(text="Status: Fejl", foreground='red')
            self.tracking_log_message(f"Fejl ved test af PlaneWave4: {str(e)}")
    
    def get_selected_satellite_for_tracking(self):
        """Henter den valgte satellit fra satellitlisten til tracking"""
        try:
            selection = self.satellite_tree.selection()
            if not selection:
                messagebox.showwarning("Ingen valg", "Vælg venligst en satelitt fra 'Hent Satelitlister' fanen")
                return
            
            item = selection[0]
            values = self.satellite_tree.item(item, 'values')
            
            # Udtræk satellit information
            self.selected_tracking_satellite = {
                'SatName': values[0],
                'NORAD': values[1],
                'StartTime': values[2],
                'EndTime': values[4],
                'TLE1': self.get_full_tle_from_selection(item)[0],
                'TLE2': self.get_full_tle_from_selection(item)[1]
            }
            
            # Vis satellit info
            info_text = f"Satellit: {self.selected_tracking_satellite['SatName']}\n"
            info_text += f"NORAD ID: {self.selected_tracking_satellite['NORAD']}\n"
            info_text += f"Observation: {self.selected_tracking_satellite['StartTime']} - {self.selected_tracking_satellite['EndTime']}"
            
            self.tracking_sat_info_text.delete(1.0, tk.END)
            self.tracking_sat_info_text.insert(1.0, info_text)
            
            # Fyld manuel TLE felter ud
            self.manual_sat_name_entry.delete(0, tk.END)
            self.manual_sat_name_entry.insert(0, self.selected_tracking_satellite['SatName'])
            
            self.manual_tle1_entry.delete(0, tk.END)
            self.manual_tle1_entry.insert(0, self.selected_tracking_satellite['TLE1'])
            
            self.manual_tle2_entry.delete(0, tk.END)
            self.manual_tle2_entry.insert(0, self.selected_tracking_satellite['TLE2'])
            
            self.tracking_log_message(f"Valgt satellit til tracking: {self.selected_tracking_satellite['SatName']}")
            
        except Exception as e:
            messagebox.showerror("Fejl", f"Kunne ikke hente satellit information: {str(e)}")
            self.tracking_log_message(f"Fejl ved valg af satellit: {str(e)}")
    
    def use_manual_tle(self):
        """Brug manuelt indtastet TLE data"""
        try:
            sat_name = self.manual_sat_name_entry.get().strip()
            tle1 = self.manual_tle1_entry.get().strip()
            tle2 = self.manual_tle2_entry.get().strip()
            
            if not sat_name or not tle1 or not tle2:
                messagebox.showwarning("Manglende data", "Udfyld alle TLE felter")
                return
            
            # Validering af TLE format
            if not (tle1.startswith('1 ') and tle2.startswith('2 ')):
                messagebox.showerror("Ugyldig TLE", "TLE linje 1 skal starte med '1 ' og linje 2 med '2 '")
                return
            
            self.selected_tracking_satellite = {
                'SatName': sat_name,
                'NORAD': tle1[2:7].strip(),
                'StartTime': datetime.now().strftime('%H:%M:%S'),
                'EndTime': (datetime.now() + timedelta(hours=1)).strftime('%H:%M:%S'),
                'TLE1': tle1,
                'TLE2': tle2
            }
            
            # Vis satellit info
            info_text = f"Satellit: {self.selected_tracking_satellite['SatName']}\n"
            info_text += f"NORAD ID: {self.selected_tracking_satellite['NORAD']}\n"
            info_text += f"Manuel TLE data anvendt"
            
            self.tracking_sat_info_text.delete(1.0, tk.END)
            self.tracking_sat_info_text.insert(1.0, info_text)
            
            self.tracking_log_message(f"Manuel TLE data anvendt for: {sat_name}")
            
        except Exception as e:
            messagebox.showerror("Fejl", f"Kunne ikke anvende manuel TLE: {str(e)}")
            self.tracking_log_message(f"Fejl ved manuel TLE: {str(e)}")
    
    def validate_tracking_parameters(self):
        """Professionel validering af alle tracking parametre før observation"""
        try:
            # Validér exposure time
            exposure_time = float(self.exposure_time_entry.get())
            if exposure_time <= 0:
                messagebox.showerror("Parameter Fejl", "Exposure time skal være positiv (>0)")
                return False
            if exposure_time > 3600:  # 1 time max for sikkerhed
                result = messagebox.askyesno("Lang Eksponering", 
                    f"Exposure time er {exposure_time}s (>{exposure_time/60:.1f} min). Fortsæt?")
                if not result:
                    return False
        except ValueError:
            messagebox.showerror("Parameter Fejl", "Ugyldig exposure time - skal være et tal")
            return False
            
        try:
            # Validér interval
            interval = float(self.tracking_interval_entry.get())
            if interval <= 0:
                messagebox.showerror("Parameter Fejl", "Interval mellem billeder skal være positivt")
                return False
            if interval < exposure_time:
                messagebox.showwarning("Parameter Advarsel", 
                    f"Interval ({interval}s) er kortere end exposure time ({exposure_time}s)")
        except ValueError:
            messagebox.showerror("Parameter Fejl", "Ugyldig interval - skal være et tal")
            return False
            
        try:
            # Validér antal billeder
            num_images = int(self.num_images_entry.get())
            if num_images <= 0:
                messagebox.showerror("Parameter Fejl", "Antal billeder skal være positivt")
                return False
            if num_images > 1000:
                result = messagebox.askyesno("Mange Billeder", 
                    f"Du har valgt {num_images} billeder. Dette vil tage lang tid. Fortsæt?")
                if not result:
                    return False
        except ValueError:
            messagebox.showerror("Parameter Fejl", "Ugyldig antal billeder - skal være et helt tal")
            return False
            
        try:
            # Validér binning parametre (fra kameraindstillinger)
            x_binning = self.camera_binning_x.get()
            y_binning = self.camera_binning_y.get()
            
            if not (1 <= x_binning <= 16):
                messagebox.showerror("Parameter Fejl", "X-binning skal være mellem 1 og 16")
                return False
            if not (1 <= y_binning <= 16):
                messagebox.showerror("Parameter Fejl", "Y-binning skal være mellem 1 og 16")
                return False
                
            # Advar om asymmetrisk binning
            if x_binning != y_binning:
                result = messagebox.askyesno("Asymmetrisk Binning", 
                    f"Du har valgt {x_binning}x{y_binning} binning. Asymmetrisk binning kan give forvrængede billeder. Fortsæt?")
                if not result:
                    return False
                    
        except ValueError:
            messagebox.showerror("Parameter Fejl", "Ugyldig binning - skal være hele tal")
            return False
            
        # Validér PWI4 URL
        pw4_url = self.pw4_url_entry.get().strip()
        if not pw4_url:
            messagebox.showerror("Parameter Fejl", "PWI4 URL skal udfyldes")
            return False
        if not (pw4_url.startswith('http://') or pw4_url.startswith('https://')):
            messagebox.showerror("Parameter Fejl", "PWI4 URL skal starte med http:// eller https://")
            return False
            
        # Beregn total observationstid
        try:
            total_time = num_images * interval
            total_minutes = total_time / 60
            if total_minutes > 60:
                result = messagebox.askyesno("Lang Observation", 
                    f"Total observationstid: {total_minutes:.1f} minutter. Fortsæt?")
                if not result:
                    return False
        except:
            pass  # Variabler allerede valideret
            
        return True
    
    def start_tracking_observation(self):
        """Start tracking observation"""
        if not self.selected_tracking_satellite:
            messagebox.showwarning("Ingen satellit", "Vælg først en satelitt eller indtast manuel TLE")
            return
        
        if self.tracking_running:
            messagebox.showwarning("Tracking kører", "En tracking observation kører allerede")
            return
            
        # Tjek kamera tilgængelighed først
        camera = self.get_camera_for_observation()
        if camera is None:
            messagebox.showerror("Kamera ikke tilgængelig", 
                               "Moravian kamera ikke tilsluttet eller ikke tilgængeligt.\n\n"
                               "Tilslut kameraet i kameraindstillinger først.\n"
                               "Sørg for at Moravian SDK er installeret og kameraet er forbundet.")
            return
        
        # Valider parametre med professionel standard
        if not self.validate_tracking_parameters():
            return
            
        # Valider parametre
        try:
            exposure_time = float(self.exposure_time_entry.get())
            interval = float(self.tracking_interval_entry.get())
            num_images = int(self.num_images_entry.get())
            x_binning = self.camera_binning_x.get()
            y_binning = self.camera_binning_y.get()
            pw4_url = self.pw4_url_entry.get().strip()
            
            if exposure_time <= 0 or interval <= 0 or num_images <= 0:
                messagebox.showerror("Ugyldige parametre", "Alle værdier skal være positive")
                return
            
            if x_binning < 1 or y_binning < 1 or x_binning > 16 or y_binning > 16:
                messagebox.showerror("Ugyldig binning", "Binning skal være mellem 1 og 16")
                return
                
        except ValueError:
            messagebox.showerror("Ugyldige parametre", "Kontroller at alle parametre er gyldige tal")
            return
        
        # Skift knap tilstande
        self.start_tracking_btn.config(state='disabled')
        self.stop_tracking_btn.config(state='normal')
        
        # Start tracking i separat tråd
        self.stop_tracking = False
        self.tracking_running = True
        threading.Thread(target=self.run_tracking_observation, daemon=True).start()
    
    def stop_tracking_observation(self):
        """Stop tracking observation"""
        self.stop_tracking = True
        self.tracking_log_message("Stop signal sendt til tracking...")
    
    def optimized_camera_exposure_with_timing(self, camera, exposure_time, pw4_client, pw4_url, obstype='satellite'):
        """Optimeret kamera eksponering med præcise tidsstempler og PWI4 status hentning."""
        import time
        from datetime import datetime, timedelta
        
        # Pre-beregn præcise tidspunkter baseret på computerur
        planned_start_time = datetime.utcnow()
        planned_mid_time = planned_start_time + timedelta(seconds=exposure_time / 2.0)
        
        self.tracking_log_message(f"Planlagt {obstype}: {planned_start_time.strftime('%H:%M:%S.%f')[:-3]} -> {planned_mid_time.strftime('%H:%M:%S.%f')[:-3]}")
        
        # Start eksponering så tæt på planlagt tid som muligt
        actual_start_time = datetime.utcnow()
        camera.start_exposure(exposure_time, use_shutter=True)
        
        # Beregn justeret midtertidspunkt baseret på faktisk start
        start_delay = (actual_start_time - planned_start_time).total_seconds()
        adjusted_mid_time = planned_mid_time + timedelta(seconds=start_delay)
        
        if abs(start_delay * 1000) > 5:  # Log kun hvis delay > 5ms
            self.tracking_log_message(f"Kamera start delay: {start_delay*1000:.1f}ms")
        
        # Præcis venting til midtertidspunkt
        pw4_status = None
        timing_accuracy = 0.0
        
        while datetime.utcnow() < adjusted_mid_time:
            if self.stop_tracking:  # Check for user stop
                try:
                    camera.abort_exposure()
                    self.tracking_log_message(f"{obstype.title()} eksponering afbrudt af bruger")
                except:
                    pass
                return None
                
            # Vent i små intervaller for høj præcision
            remaining_seconds = (adjusted_mid_time - datetime.utcnow()).total_seconds()
            if remaining_seconds > 0.01:  # Hvis mere end 10ms tilbage
                time.sleep(min(0.001, remaining_seconds / 2))  # Sleep max 1ms
            else:
                break
        
        # Hent PWI4 status så præcist som muligt ved midtertidspunkt
        actual_mid_time = datetime.utcnow()
        timing_accuracy = abs((actual_mid_time - adjusted_mid_time).total_seconds() * 1000)  # ms
        
        try:
            if (obstype == 'Tracking' or obstype == 'LeapFrog') and pw4_client:
                # Brug PWI4 klient for Tracking og LeapFrog billeder
                status = pw4_client.get_status()
                if status:
                    pw4_status = {
                        'mount': {
                            'ra_apparent_hours': status['ra_apparent_hours'],
                            'dec_apparent_degs': status['dec_apparent_degs'],
                            'ra_j2000_hours': status['ra_j2000_hours'],
                            'dec_j2000_degs': status['dec_j2000_degs'],
                            'ra_apparent_degs': status['ra_apparent_hours'] * 15.0,
                            'ra_j2000_degs': status['ra_j2000_hours'] * 15.0,
                            'is_slewing': status['slewing'],
                            'is_tracking': status['tracking'],
                            'altitude_degs': status['altitude_degs'],
                            'azimuth_degs': status['azimuth_degs'],
                            'julian_date': status['julian_date'],
                            'distance_to_sun_degs': status['distance_to_sun_degs'],
                            'field_angle_degs': status['field_angle_degs']
                        },
                        'site': {
                            'latitude_degs': status['latitude_degs'],
                            'longitude_degs': status['longitude_degs'],
                            'height_meters': status['height_meters']
                        },
                        'pwi4': {
                            'version': 'PWI4 HTTP API'
                        }
                    }
            elif obstype == 'starfield':
                # Brug HTTP direkte for stjernehimmel billeder
                import requests
                status_response = requests.get(f"{pw4_url}/status", timeout=5)
                if status_response.status_code == 200:
                    lines = status_response.text.strip().splitlines()
                    pw4_data = {}
                    for line in lines:
                        if "=" in line:
                            key, value = line.split("=", 1)
                            pw4_data[key.strip()] = value.strip()
                    
                    pw4_status = {
                        'mount': {
                            'ra_apparent_hours': float(pw4_data.get('mount.ra_apparent_hours', 0)),
                            'dec_apparent_degs': float(pw4_data.get('mount.dec_apparent_degs', 0)),
                            'ra_j2000_hours': float(pw4_data.get('mount.ra_j2000_hours', 0)),
                            'dec_j2000_degs': float(pw4_data.get('mount.dec_j2000_degs', 0)),
                            'ra_apparent_degs': float(pw4_data.get('mount.ra_apparent_degs', 0)),
                            'ra_j2000_degs': float(pw4_data.get('mount.ra_j2000_degs', 0)),
                            'is_slewing': pw4_data.get('mount.is_slewing', 'false').lower() == 'true',
                            'is_tracking': pw4_data.get('mount.is_tracking', 'false').lower() == 'true',
                            'altitude_degs': float(pw4_data.get('mount.altitude_degs', 0)),
                            'azimuth_degs': float(pw4_data.get('mount.azimuth_degs', 0)),
                            'julian_date': float(pw4_data.get('mount.julian_date', 0)),
                            'distance_to_sun_degs': float(pw4_data.get('mount.distance_to_sun_degs', 0)),
                            'field_angle_degs': float(pw4_data.get('rotator.field_angle_degs', 0))
                        },
                        'site': {
                            'latitude_degs': float(pw4_data.get('site.latitude_degs', 0)),
                            'longitude_degs': float(pw4_data.get('site.longitude_degs', 0)),
                            'height_meters': float(pw4_data.get('site.height_meters', 0))
                        },
                        'pwi4': {
                            'version': pw4_data.get('pwi4.version', 'Unknown')
                        }
                    }
            
            self.tracking_log_message(f"PWI4 status hentet: {actual_mid_time.strftime('%H:%M:%S.%f')[:-3]} (nøjagtighed: {timing_accuracy:.1f}ms)")
            
        except Exception as pw4_error:
            self.tracking_log_message(f"PWI4 status fejl ({obstype}): {str(pw4_error)}")
        
        # Vent på eksponering færdig
        camera.wait_for_image(timeout=exposure_time + 2) # Venter maks 2 sekunder ekstra
        
        # Hent billede og noter præcis sluttid
        if self.stop_tracking:
            return None
            
        if camera.image_ready():
            # Noter tid FØR billedhentning (dette er nærmere det faktiske eksposeringsslut)
            exposure_end_estimate = datetime.utcnow()
            img_data = camera.read_image()
            
            self.tracking_log_message(f"{obstype.title()} billede hentet: {img_data.shape} (slut: {exposure_end_estimate.strftime('%H:%M:%S.%f')[:-3]})")
            
            return {
                'image_data': img_data,
                'exposure_start_time': actual_start_time,
                'exposure_mid_time': actual_mid_time,
                'exposure_end_time': exposure_end_estimate,
                'pw4_status': pw4_status,
                'timing_accuracy': timing_accuracy,
                'obstype': obstype
            }
        else:
            raise Exception(f"{obstype.title()} kamera billede ikke klar efter timeout")
    
    def run_tracking_observation(self):
        """Kør tracking observation med PlaneWave4"""
        try:
            self.tracking_log_message("Starter tracking observation...")
            
            # Hent parametre (binning fra kameraindstillinger)
            exposure_time = float(self.exposure_time_entry.get())
            interval = float(self.tracking_interval_entry.get())
            num_images = int(self.num_images_entry.get())
            x_binning = self.camera_binning_x.get()
            y_binning = self.camera_binning_y.get()
            pw4_url = self.pw4_url_entry.get().strip()
            
            sat_name = self.selected_tracking_satellite['SatName']
            tle1 = self.selected_tracking_satellite['TLE1']
            tle2 = self.selected_tracking_satellite['TLE2']
            
            self.tracking_log_message(f"Satellit: {sat_name}")
            self.tracking_log_message(f"Exposure time: {exposure_time}s, Interval: {interval}s, Antal billeder: {num_images}")
            self.tracking_log_message(f"Binning: {x_binning}x{y_binning}")
            
            # Initialiser Moravian kamera
            camera = self.get_camera_for_observation()
            if camera is None:
                self.tracking_log_message("FEJL: Moravian kamera ikke tilsluttet")
                self.tracking_log_message("Tilslut kameraet i kameraindstillinger først")
                raise Exception("Moravian kamera ikke tilsluttet eller ikke tilgængeligt")
            
            # Sæt binning på kamera
            camera.set_binning(x_binning, y_binning)
            
            # Kamera konfiguration for Moravian kameraer
            info = camera.get_camera_info()
            camera_desc = info.get('description', 'Moravian Camera')
            ccd_width = info.get('width', 0)
            ccd_height = info.get('height', 0)
            
            self.tracking_log_message(f"Konfigurerer kamera: {camera_desc}")
            self.tracking_log_message(f"CCD størrelse: {ccd_width} x {ccd_height} pixels")
            self.tracking_log_message(f"Binning sat til: {x_binning}x{y_binning}")
            
            # Beregn korrekt billedstørrelse baseret på binning
            image_width = ccd_width // x_binning
            image_height = ccd_height // y_binning
            
            self.tracking_log_message(f"Beregnet billedstørrelse: {image_width}x{image_height} pixels")
            
            # Verificer binning
            max_binning_x = info.get('max_binning_x', 8)
            max_binning_y = info.get('max_binning_y', 8)
            
            if x_binning > max_binning_x or y_binning > max_binning_y:
                raise Exception(f"Binning {x_binning}x{y_binning} overstiger kamera max: {max_binning_x}x{max_binning_y}")
            
            self.tracking_log_message(f"Kamera konfiguration bekræftet:")
            self.tracking_log_message(f"  Binning: {camera.bin_x}x{camera.bin_y}")
            self.tracking_log_message(f"  Billedstørrelse: {image_width}x{image_height} pixels")
            
            # Temperatur info
            current_temp = info.get('temperature', None)
            if current_temp is not None:
                self.tracking_log_message(f"  Kamera temperatur: {current_temp:.1f}°C")
            
            # Start PlaneWave4 tracking
            self.tracking_log_message("Starter PWI4 satellit tracking...")
            
            try:
                # Opret PWI4 klient
                pw4_host = self.pw4_url.replace("http://", "").split(":")[0]
                pw4_port = int(self.pw4_url.split(":")[-1]) if ":" in self.pw4_url else 8220
                
                pwi4 = PWI4Telescope(host=pw4_host, port=pw4_port)
                
                if not pwi4.test_connection():
                    raise Exception(f"Kan ikke forbinde til PWI4 på {self.pw4_url}")
                
                pwi4.connect()
                self.tracking_log_message("PWI4 forbinder etableret")
                
                # Start satellit tracking
                pwi4.track_satellite_tle(sat_name, tle1, tle2)
                self.tracking_log_message("PWI4 satellit tracking startet")

                # Vent på slew færdig
                while pwi4.is_slewing() and not self.stop_tracking:
                    time.sleep(0.1)
                
            except Exception as e:
                self.tracking_log_message(f"PWI4 fejl: {str(e)}")
                return
            
            # Tag billeder med specified intervaller
            for i in range(num_images):
                if self.stop_tracking:
                    self.tracking_log_message("Tracking stoppet af bruger")
                    break
                
                # Opret outputmappe ved første billede
                if i == 0:
                    # Generer mappenavn: Tracking_SatellitNavn_NoradId_Måned_Dag
                    session_date = datetime.now().strftime('%m_%d')
                    safe_sat_name = "".join(c for c in sat_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
                    safe_sat_name = safe_sat_name.replace(' ', '_')
                    norad_id = self.selected_tracking_satellite['NORAD']
                    
                    output_dir = f"Tracking_{safe_sat_name}_{norad_id}_{session_date}"
                    
                    try:
                        os.makedirs(output_dir, exist_ok=True)
                        self.tracking_log_message(f"Oprettet outputmappe: {output_dir}")
                    except Exception as dir_error:
                        self.tracking_log_message(f"Kunne ikke oprette mappe {output_dir}: {str(dir_error)}")
                        output_dir = "."  # Brug nuværende mappe som fallback
                
                self.tracking_log_message(f"Tager billede {i+1}/{num_images}")
                
                # Tag stjernehimmel referencebillede efter første satellitbillede
                if i == 1:  # Efter det første billede (index 0)
                    try:
                        self.tracking_log_message("Afbryder satellit tracking for at tage stjernehimmel referencebillede...")
                        
                        # Stop PlaneWave4 satellit tracking
                        stop_response = requests.get(f"{pw4_url}/mount/stop", timeout=5)
                        if stop_response.status_code == 200:
                            self.tracking_log_message("PlaneWave4 satellit tracking stoppet")
                        else:
                            self.tracking_log_message(f"Kunne ikke stoppe satellit tracking: HTTP {stop_response.status_code}")
                        
                        # Start sidereal tracking (stjernehimmel)
                        sidereal_response = requests.get(f"{pw4_url}/mount/tracking_on", timeout=5)
                        if sidereal_response.status_code == 200:
                            self.tracking_log_message("Sidereal tracking (stjernehimmel) startet")
                        else:
                            self.tracking_log_message(f"Kunne ikke starte sidereal tracking: HTTP {sidereal_response.status_code}")
                        
                        # Vent lidt for at sikre tracking er stabiliseret
                        time.sleep(2)
                        
                        # Tag stjernehimmel billede med OPTIMERET timing
                        self.tracking_log_message("Tager stjernehimmel referencebillede (optimeret timing)...")
                        
                        # *** OPTIMERET STJERNEHIMMEL EKSPONERING ***
                        star_result = self.optimized_camera_exposure_with_timing(
                            camera=camera, 
                            exposure_time=exposure_time, 
                            pw4_client=None,  # Bruges ikke for stjernehimmel
                            pw4_url=pw4_url,
                            obstype='starfield'
                        )
                        
                        if star_result is None:  # Afbrudt af bruger
                            continue
                        
                        # Udpak resultater
                        star_img_data = star_result['image_data']
                        star_exposure_start_time = star_result['exposure_start_time']
                        star_exposure_end_time = star_result['exposure_end_time']
                        star_pw4_status = star_result['pw4_status']
                        
                        self.tracking_log_message(f"Stjernehimmel timing nøjagtighed: {star_result['timing_accuracy']:.1f}ms")
                        

                        
                        # Generer filnavn for stjernehimmel billede
                        star_filename = f"Starfield_ref_{safe_sat_name}_{norad_id}_001.fits"
                        star_filepath = os.path.join(output_dir, star_filename)
                        
                        # Hent filter information
                        filter_name = self.get_current_filter_name()
                        
                        # Opret FITS header for stjernehimmel billede
                        star_hdr = self.create_standard_fits_header(
                            obstype='stjernehimmel',
                            sat_name=sat_name,  # Beholder satellit navn for reference
                            exposure_start_time=star_exposure_start_time,
                            exposure_end_time=star_exposure_end_time,
                            exposure_time=exposure_time,
                            tle1=tle1,
                            tle2=tle2,
                            norad_id=self.selected_tracking_satellite['NORAD'],
                            camera=camera,
                            pw4_status=star_pw4_status,
                            image_width=star_img_data.shape[1],
                            image_height=star_img_data.shape[0],
                            filter_name=filter_name
                        )
                        
                        # Gem stjernehimmel FITS fil
                        star_img_data_uint16 = star_img_data.astype(np.uint16)
                        hdu = fits.PrimaryHDU(data=star_img_data_uint16, header=star_hdr)
                        hdu.writeto(star_filepath, overwrite=True)
                        
                        self.tracking_log_message(f"Stjernehimmel referencebillede gemt: {star_filename}")
                        
                        # Genstart satellit tracking
                        self.tracking_log_message("Genstarter satellit tracking...")
                        restart_response = requests.get(
                            f"{pw4_url}/mount/follow_tle",
                            params={
                                "line1": sat_name,
                                "line2": tle1,
                                "line3": tle2
                            },
                            timeout=10
                        )
                        
                        if restart_response.status_code == 200:
                            self.tracking_log_message("Satellit tracking genstartet succesfuldt")
                        else:
                            self.tracking_log_message(f"Fejl ved genstart af satellit tracking: HTTP {restart_response.status_code}")
                        
                        # Vent lidt for at sikre tracking er stabiliseret igen
                        time.sleep(2)
                        
                    except Exception as star_error:
                        self.tracking_log_message(f"Fejl ved stjernehimmel billede: {str(star_error)}")
                        # Fortsæt med normal observation selvom stjernehimmel fejlede
                
                try:
                    # *** OPTIMERET SATELLIT EKSPONERING ***
                    satellite_result = self.optimized_camera_exposure_with_timing(
                        camera=camera, 
                        exposure_time=exposure_time, 
                        pw4_client=pwi4,
                        pw4_url=pw4_url,
                        obstype='Tracking'
                    )
                    
                    if satellite_result is None:  # Afbrudt af bruger
                        break
                    
                    # Udpak resultater
                    img_data = satellite_result['image_data']
                    exposure_start_time = satellite_result['exposure_start_time'] 
                    exposure_mid_time = satellite_result['exposure_mid_time']
                    exposure_end_time = satellite_result['exposure_end_time']
                    pw4_status = satellite_result['pw4_status']
                    
                    self.tracking_log_message(f"Satellit timing nøjagtighed: {satellite_result['timing_accuracy']:.1f}ms")
                    
                    if self.stop_observation:
                        break

                    # Generer filnavn med nyt format
                    filename = f"Tracking_{safe_sat_name}_{norad_id}_{i+1:03d}.fits"
                    
                    # Komplet sti med mappe
                    filepath = os.path.join(output_dir, filename)
                    
                    # Hent filter information
                    filter_name = self.get_current_filter_name()
                    
                    # Opret FITS header med præcis timing for Tracking
                    hdr = self.create_standard_fits_header(
                        obstype='Tracking',
                        sat_name=sat_name,
                        exposure_start_time=exposure_start_time,
                        exposure_end_time=exposure_end_time,
                        exposure_time=exposure_time,
                        tle1=tle1,
                        tle2=tle2,
                        norad_id=self.selected_tracking_satellite['NORAD'],
                        camera=camera,
                        pw4_status=pw4_status,
                        image_width=img_data.shape[1],
                        image_height=img_data.shape[0],
                        filter_name=filter_name,
                        mid_exposure_time=exposure_mid_time
                    )
                    
                    # Tilføj tracking specifikke felter
                    hdr["COMMENT"] = f"Satellite tracking image {i+1}/{num_images}"
                    
                    # Gem FITS fil med komplet header
                    img_data_uint16 = img_data.astype(np.uint16)
                    hdu = fits.PrimaryHDU(data=img_data_uint16, header=hdr)
                    hdu.writeto(filepath, overwrite=True)
                    
                    self.tracking_log_message(f"Billede gemt: {filename}")
                    
                except Exception as img_error:
                    self.tracking_log_message(f"Fejl ved tag af billede {i+1}: {str(img_error)}")
                
                if self.stop_tracking:
                    break
                
                # Vent til næste billede
                if i < num_images - 1:  # Vent ikke efter sidste billede
                    self.tracking_log_message(f"Venter {interval}s til næste billede...")
                    
                    # Vent i små intervaller så vi kan stoppe hurtigt
                    wait_time = 0
                    while wait_time < interval and not self.stop_tracking:
                        time.sleep(0.1)
                        wait_time += 0.1
            
            if not self.stop_tracking:
                self.tracking_log_message("Tracking observation fuldført!")
            
            # Stop PWI4 tracking
            try:
                pwi4.stop_tracking()
                self.tracking_log_message("PWI4 tracking stoppet")
            except Exception as e:
                self.tracking_log_message(f"Fejl ved stop af PWI4: {str(e)}")
            
        except Exception as e:
            self.tracking_log_message(f"Fejl under tracking: {str(e)}")
        finally:
            self.tracking_running = False
            self.start_tracking_btn.config(state='normal')
            self.stop_tracking_btn.config(state='disabled')
            pwi4.park()
            self.tracking_log_message("Tracking session afsluttet")

    # =================
    # BILLEDE ANALYSE METODER
    # =================
    
    def analysis_log_message(self, message):
        """Tilføj besked til analyse log"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.analysis_log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.analysis_log_text.see(tk.END)
        self.root.update()
    
    def setup_plot_display(self, parent_frame):
        """Opsæt plot visning område med scrollbar"""
        # Canvas med scrollbar
        canvas_frame = ttk.Frame(parent_frame)
        canvas_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        self.plot_canvas = Canvas(canvas_frame, background='white')
        scrollbar = ttk.Scrollbar(canvas_frame, orient='vertical', command=self.plot_canvas.yview)
        self.plot_scrollable_frame = ttk.Frame(self.plot_canvas)
        
        self.plot_scrollable_frame.bind(
            "<Configure>",
            lambda e: self.plot_canvas.configure(scrollregion=self.plot_canvas.bbox("all"))
        )
        
        self.plot_canvas.create_window((0, 0), window=self.plot_scrollable_frame, anchor="nw")
        self.plot_canvas.configure(yscrollcommand=scrollbar.set)
        
        self.plot_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Placeholder label
        self.plot_placeholder = ttk.Label(self.plot_scrollable_frame, 
                                         text="Plots vil blive vist her efter analyse", 
                                         font=('Arial', 10), foreground='gray')
        self.plot_placeholder.pack(expand=True, pady=50)
    
    def select_analysis_directory(self):
        """Vælg mappe med billeder til analyse"""
        directory = filedialog.askdirectory(
            title="Vælg mappe med FITS billeder",
            initialdir=os.getcwd()
        )
        if directory:
            self.analysis_dir_entry.delete(0, tk.END)
            self.analysis_dir_entry.insert(0, directory)
            self.analysis_directory = directory
    
    def select_astap_path(self):
        """Vælg ASTAP executable"""
        filepath = filedialog.askopenfilename(
            title="Vælg ASTAP executable",
            filetypes=[("Executable files", "*.exe"), ("All files", "*.*")],
            initialdir=r"C:\Program Files\astap"
        )
        if filepath:
            self.astap_path_entry.delete(0, tk.END)
            self.astap_path_entry.insert(0, filepath)
    
    def start_image_analysis(self):
        """Start billede analyse i separat tråd"""
        if self.image_analysis_running:
            messagebox.showwarning("Analyse kører", "En analyse kører allerede")
            return
        
        # Valider input
        directory = self.analysis_dir_entry.get().strip()
        astap_path = self.astap_path_entry.get().strip()
        
        if not directory or not os.path.exists(directory):
            messagebox.showerror("Fejl", "Vælg en gyldig mappe med billeder")
            return
        
        if not astap_path or not os.path.exists(astap_path):
            messagebox.showerror("Fejl", "Vælg en gyldig ASTAP executable")
            return
        
        try:
            pixelscale = float(self.pixelscale_entry.get())
            if pixelscale <= 0:
                raise ValueError("Pixelscale skal være positiv")
        except ValueError:
            messagebox.showerror("Fejl", "Indtast en gyldig pixelscale (grader/pixel)")
            return
        
        # Validér tracking pixelsum radius
        try:
            radius = self.tracking_pixelsum_radius.get()
            if radius < 1 or radius > 1000:
                raise ValueError("Radius skal være mellem 1 og 1000 pixels")
        except ValueError:
            messagebox.showerror("Fejl", "Indtast en gyldig radius for pixelsum (1-1000 pixels)")
            return
        
        # Tjek for FITS filer
        fits_files = [f for f in os.listdir(directory) if f.lower().endswith('.fits')]
        if not fits_files:
            messagebox.showerror("Fejl", "Ingen FITS filer fundet i mappen")
            return
        
        # Start analyse
        self.start_analysis_btn.config(state='disabled')
        self.stop_analysis_btn.config(state='normal')
        self.stop_image_analysis = False
        
        threading.Thread(target=self.run_image_analysis, daemon=True).start()
    
    def stop_image_analysis(self):
        """Stop billede analyse"""
        self.stop_image_analysis = True
        self.analysis_log_message("Stop signal sendt...")
    
    def run_image_analysis(self):
        """Kør billede analyse"""
        try:
            self.image_analysis_running = True
            self.analysis_log_message("Starter billede analyse...")
            
            directory = self.analysis_dir_entry.get().strip()
            astap_path = self.astap_path_entry.get().strip()
            pixelscale = float(self.pixelscale_entry.get())
            save_plots = self.save_plots_var.get()
            
            # Find FITS filer
            fits_files = sorted([f for f in os.listdir(directory) if f.lower().endswith('.fits')])
            self.analysis_log_message(f"Fundet {len(fits_files)} FITS filer")
            
            # Analyser første fil for at bestemme observation type
            first_file = os.path.join(directory, fits_files[0])
            with fits.open(first_file) as hdul:
                header = hdul[0].header
            
            obstype = header.get('OBSTYPE', 'Unknown')
            sat_name = header.get('OBJECT', 'Unknown')
            norad_id = header.get('NORAD_ID', 'Unknown')
            
            self.analysis_log_message(f"Observation type: {obstype}")
            self.analysis_log_message(f"Satellit: {sat_name} (NORAD: {norad_id})")
            
            # Opret output CSV navn
            output_filename = f"data_{sat_name}_{norad_id}.csv"
            output_path = os.path.join(directory, output_filename)
            
            if obstype == 'LeapFrog':
                result_df = self.analyze_leapfrog_images(directory, fits_files, astap_path, pixelscale, save_plots)
            elif obstype == 'Tracking' or obstype == 'stjernehimmel':
                result_df = self.analyze_tracking_images(directory, fits_files, astap_path, pixelscale, save_plots)
            else:
                raise ValueError(f"Ukendt observation type: {obstype}")
            
            # Gem resultater
            result_df.to_csv(output_path, index=False)
            self.analysis_log_message(f"Resultater gemt i: {output_filename}")
            
            if not self.stop_image_analysis:
                self.analysis_log_message("Billede analyse fuldført!")
                
                # Vis plots efter analysen hvis ønsket
                if save_plots:
                    self.root.after(100, lambda: self.display_plots_in_gui(directory))
            
        except Exception as e:
            self.analysis_log_message(f"Fejl under analyse: {str(e)}")
            messagebox.showerror("Fejl", f"Billede analyse fejlede: {str(e)}")
        finally:
            self.image_analysis_running = False
            self.start_analysis_btn.config(state='normal')
            self.stop_analysis_btn.config(state='disabled')
            self.analysis_progress_var.set(0)

    def run_astap_on_directory(self, directory, astap_exe=r"C:\Program Files\astap\astap.exe"):
        """Kør ASTAP på alle FITS filer i en mappe og returner resultater som DataFrame"""
        results = []

        # find alle fits filer
        for filename in os.listdir(directory):
            if filename.lower().endswith(".fits"):
                filepath = os.path.join(directory, filename)
                wcsfile = os.path.join(directory, filename.replace(".fits", ".wcs"))

                # kør astap
                result = subprocess.run(
                    [astap_exe, "-f", filepath, "-wcs", wcsfile],
                    capture_output=True, text=True
                )

                if result.returncode != 0:
                    self.analysis_log_message(f"ASTAP fejlede for {filename}: {result.stderr}")
                    continue
                else:
                    self.analysis_log_message(f"ASTAP gennemført for {filename}")

                # læs header fra wcs-filen
                if os.path.exists(wcsfile):
                    with fits.open(wcsfile) as hdul:
                        header = hdul[0].header
                        

                    # konverter header til dict
                    header_dict = {k: header[k] for k in header.keys() if k != ''}

                    # tilføj filnavn
                    header_dict["filename"] = filename

                    results.append(header_dict)
                    os.remove(wcsfile)

        # lav dataframe af alle headere
        df = pd.DataFrame(results)

        # Slet alle .ini-filer i output-mappen (ASTAP kan have lavet dem)
        for f in os.listdir(directory):
            if f.lower().endswith('.ini'):
                try:
                    os.remove(os.path.join(directory, f))
                except Exception:
                    pass

        return df
    
    def analyze_leapfrog_images(self, directory, fits_files, astap_path, pixelscale, save_plots):
        """Analyser LeapFrog billeder"""
        self.analysis_log_message("Starter LeapFrog analyse...")
        
        if not SKIMAGE_AVAILABLE:
            raise ImportError("Manglende biblioteker: skimage, cv2, scipy")
        
        from Func_fagprojekt import pixel_to_radec, compute_cd
        
        results = []
        total_files = len(fits_files)
        
        # Kør ASTAP på alle billeder først
        self.analysis_log_message("Kører ASTAP plate solving på alle billeder...")
        try:
            df_astap = self.run_astap_on_directory(directory, astap_path)
            self.analysis_log_message(f"ASTAP gennemført på {len(df_astap)} billeder")
        except Exception as e:
            self.analysis_log_message(f"ADVARSEL: ASTAP fejlede: {str(e)}")
            df_astap = None
        
        for i, filename in enumerate(fits_files):
            if self.stop_image_analysis:
                break
            
            self.analysis_log_message(f"Behandler LeapFrog fil {i+1}/{total_files}: {filename}")
            self.analysis_progress_var.set((i / total_files) * 100)
            
            filepath = os.path.join(directory, filename)
            
            try:
                # Læs FITS fil og header
                with fits.open(filepath) as hdul:
                    image_data = hdul[0].data.astype(np.float32)
                    header = hdul[0].header
                
                # Udtræk alle headers fra FITS-filen med deres originale navne
                file_data = dict(header)
                # Tilføj filnavn (fra FITS er det ikke med)
                file_data['filename'] = filename
                
                # Beregn observatørens ECI position fra lat/lon/ele og tidspunkt
                try:
                    from skyfield.api import load, wgs84
                    from astropy.time import Time
                    
                    ts = load.timescale()
                    obs_time_str = file_data.get('DATE-OBS', '')
                    
                    # Parse tidspunkt
                    if 'T' in obs_time_str:
                        obs_dt = datetime.strptime(obs_time_str, '%Y-%m-%dT%H:%M:%S.%f')
                    else:
                        obs_dt = datetime.strptime(obs_time_str, '%Y-%m-%d %H:%M:%S.%f')
                    
                    t = ts.utc(obs_dt.year, obs_dt.month, obs_dt.day, 
                              obs_dt.hour, obs_dt.minute, obs_dt.second + obs_dt.microsecond/1e6)
                    
                    # Beregn ECI position
                    lat = file_data.get('LAT-OBS', 0)
                    lon = file_data.get('LONG-OBS', 0)
                    ele = file_data.get('ELEV-OBS', 0)
                    
                    earth_location = wgs84.latlon(lat, lon, ele)
                    eci_pos = earth_location.at(t).position.km
                    
                    file_data['X_obs'] = eci_pos[0]
                    file_data['Y_obs'] = eci_pos[1]
                    file_data['Z_obs'] = eci_pos[2]
                    
                except Exception as e:
                    self.analysis_log_message(f"  Advarsel: Kunne ikke beregne ECI position: {str(e)}")
                    file_data['X_obs'] = np.nan
                    file_data['Y_obs'] = np.nan
                    file_data['Z_obs'] = np.nan
                
                # Find satellitlinje med billedbehandling
                sat_coords = self.find_satellite_line_leapfrog(image_data, header, save_plots, filepath, i)
                file_data.update(sat_coords)
                
                # Opdater observationstid hvis vi har en korrigeret tid
                if sat_coords.get('corrected_obs_time'):
                    diff = (pd.to_datetime(sat_coords['corrected_obs_time']) - pd.to_datetime(file_data['DATE-OBS'])).total_seconds()
                    self.analysis_log_message(f"ændrede DATE-OBS med {diff} s")
                    file_data['DATE-OBS'] = sat_coords['corrected_obs_time']
                
                # Tilføj ASTAP WCS data hvis tilgængeligt
                if df_astap is not None and filename in df_astap['filename'].values:
                    astap_row = df_astap[df_astap['filename'] == filename].iloc[0]
                    file_data['CRPIX1'] = astap_row.get('CRPIX1', np.nan)
                    file_data['CRPIX2'] = astap_row.get('CRPIX2', np.nan)
                    file_data['CRVAL1'] = astap_row.get('CRVAL1', np.nan)
                    file_data['CRVAL2'] = astap_row.get('CRVAL2', np.nan)
                    file_data['CD1_1'] = astap_row.get('CD1_1', np.nan)
                    file_data['CD1_2'] = astap_row.get('CD1_2', np.nan)
                    file_data['CD2_1'] = astap_row.get('CD2_1', np.nan)
                    file_data['CD2_2'] = astap_row.get('CD2_2', np.nan)
                    file_data['CROTA2_ASTAP'] = astap_row.get('CROTA2', np.nan)
                    
                    # Konverter pixel koordinater til RA/DEC hvis vi har både WCS og satellit position
                    if not np.isnan(file_data.get('x_sat', np.nan)) and not np.isnan(file_data['CRVAL1']):
                        try:
                            x_sat = file_data['x_sat']
                            y_sat = file_data['y_sat']
                            ra_sat, dec_sat = pixel_to_radec(x_sat, y_sat, astap_row)
                            file_data['Sat_RA_Behandlet'] = ra_sat
                            file_data['Sat_DEC_Behandlet'] = dec_sat
                            self.analysis_log_message(f"Satellit RA/DEC: {ra_sat:.6f}°, {dec_sat:.6f}°\n =============================")

                            
                            # Beregn selvberegnet CD matrix til sammenligning
                            cdelt1 = astap_row.get('CDELT1', np.nan)
                            cdelt2 = astap_row.get('CDELT2', np.nan)
                            crota2 = astap_row.get('CROTA2', 0)
                            dec_tel = file_data.get('DEC', 0)
                            
                            if not np.isnan(cdelt1) and not np.isnan(cdelt2):
                                cd11_python, cd12_python, cd21_python, cd22_python = compute_cd(
                                    cdelt1, cdelt2, crota2, dec_tel
                                )
                                file_data['CD1_1_python'] = cd11_python
                                file_data['CD1_2_python'] = cd12_python
                                file_data['CD2_1_python'] = cd21_python
                                file_data['CD2_2_python'] = cd22_python
                        except Exception as e:
                            self.analysis_log_message(f"  Fejl ved RA/DEC konvertering: {str(e)}")
                
                results.append(file_data)
                
            except Exception as e:
                self.analysis_log_message(f"Fejl i fil {filename}: {str(e)}")
                # Tilføj tom række for at bevare rækkefølge
                error_data = {'filename': filename, 'error': str(e)}
                results.append(error_data)
        
        self.analysis_progress_var.set(100)
        return pd.DataFrame(results)
    
    def analyze_tracking_images(self, directory, fits_files, astap_path, pixelscale, save_plots):
        """Analyser Tracking billeder"""
        self.analysis_log_message("Starter Tracking analyse...")
        
        if not SKIMAGE_AVAILABLE:
            raise ImportError("Manglende biblioteker: skimage, cv2, scipy")
        
        from Func_fagprojekt import pixel_to_radec, compute_cd
        
        results = []
        total_files = len(fits_files)
        
        # Find stjernehimmel reference billede
        starfield_ref = None
        for filename in fits_files:
            if 'starfield_ref' in filename.lower():
                starfield_ref = filename
                break
        
        if starfield_ref:
            self.analysis_log_message(f"Fundet stjernehimmel reference: {starfield_ref}")
            # Analyser reference billede med ASTAP
            ref_offset = self.analyze_starfield_reference(directory, starfield_ref, astap_path)
        else:
            self.analysis_log_message("Ingen stjernehimmel reference fundet - bruger standard offset")
            ref_offset = {'ra_offset': 0, 'dec_offset': 0, 'rotation_offset': 0}
        
        for i, filename in enumerate(fits_files):
            if self.stop_image_analysis:
                break
            
            self.analysis_log_message(f"Behandler Tracking fil {i+1}/{total_files}: {filename}")
            self.analysis_progress_var.set((i / total_files) * 100)
            
            filepath = os.path.join(directory, filename)
            
            try:
                # Læs FITS fil og header
                with fits.open(filepath) as hdul:
                    image_data = hdul[0].data.astype(np.float32)
                    header = hdul[0].header
                
                # Udtræk alle headers fra FITS-filen med deres originale navne
                file_data = dict(header)
                # Tilføj filnavn (fra FITS er det ikke med)
                file_data['filename'] = filename
                
                # Beregn observatørens ECI position fra lat/lon/ele og tidspunkt
                try:
                    from skyfield.api import load, wgs84
                    from astropy.time import Time
                    
                    ts = load.timescale()
                    obs_time_str = file_data.get('DATE-OBS', '')
                    
                    # Parse tidspunkt
                    if 'T' in obs_time_str:
                        obs_dt = datetime.strptime(obs_time_str, '%Y-%m-%dT%H:%M:%S.%f')
                    else:
                        obs_dt = datetime.strptime(obs_time_str, '%Y-%m-%d %H:%M:%S.%f')
                    
                    t = ts.utc(obs_dt.year, obs_dt.month, obs_dt.day, 
                              obs_dt.hour, obs_dt.minute, obs_dt.second + obs_dt.microsecond/1e6)
                    
                    # Beregn ECI position
                    lat = file_data.get('LAT-OBS', 0)
                    lon = file_data.get('LONG-OBS', 0)
                    ele = file_data.get('ELEV-OBS', 0)
                    
                    earth_location = wgs84.latlon(lat, lon, ele)
                    eci_pos = earth_location.at(t).position.km
                    
                    file_data['X_obs'] = eci_pos[0]
                    file_data['Y_obs'] = eci_pos[1]
                    file_data['Z_obs'] = eci_pos[2]
                    
                except Exception as e:
                    self.analysis_log_message(f"  Advarsel: Kunne ikke beregne ECI position: {str(e)}")
                    file_data['X_obs'] = np.nan
                    file_data['Y_obs'] = np.nan
                    file_data['Z_obs'] = np.nan
                
                # Tilføj offset fra stjernehimmel reference
                file_data.update(ref_offset)
                
                # Beregn CD matrix for tracking billeder
                # Tracking billeder har andre kolonnenavne end leapfrog
                try:
                    # Hent pixel scale - skal justeres for binning
                    xbinning = file_data.get('XBINNING', 1)
                    ybinning = file_data.get('YBINNING', 1)
                    cdelt1 = pixelscale * xbinning  # grader per pixel
                    cdelt2 = pixelscale * ybinning
                    
                    # CROTA2 er gemt som field_angle_degs i tracking billeder
                    # Hent CROTA2 fra header og tilføj rotation offset fra ASTAP
                    crota2_header = header.get('CROTA2', 0)
                    crota2 = crota2_header + ref_offset.get('rotation_offset', 0)
                    
                    self.analysis_log_message(f"CROTA2 fra header: {crota2_header:.3f}°, offset: {ref_offset.get('rotation_offset', 0):.3f}°, bruger: {crota2:.3f}°")
                    
                    # Beregn reference pixels (center af billede)
                    crpix1 = file_data.get('NAXIS1', 0) / 2.0
                    crpix2 = file_data.get('NAXIS2', 0) / 2.0
                    
                    # Beregn reference værdi (teleskopets pointing med offset)
                    crval1 = file_data.get('RA', 0) + ref_offset.get('ra_offset', 0)
                    crval2 = file_data.get('DEC', 0) + ref_offset.get('dec_offset', 0)
                    
                    # Beregn CD matrix
                    cd11, cd12, cd21, cd22 = compute_cd(
                        cdelt1, cdelt2, crota2, crval2
                    )
                    
                    file_data['CDELT1'] = cdelt1
                    file_data['CDELT2'] = cdelt2
                    file_data['CROTA2'] = crota2
                    file_data['CRPIX1'] = crpix1
                    file_data['CRPIX2'] = crpix2
                    file_data['CRVAL1'] = crval1
                    file_data['CRVAL2'] = crval2
                    file_data['CD1_1'] = cd11
                    file_data['CD1_2'] = cd12
                    file_data['CD2_1'] = cd21
                    file_data['CD2_2'] = cd22
                    
                except Exception as e:
                    self.analysis_log_message(f"  Fejl ved CD matrix beregning: {str(e)}")
                
                # Find satellitposition
                if 'starfield_ref' not in filename.lower():  # Skip reference billede
                    sat_coords = self.find_satellite_position_tracking(
                        image_data, header, pixelscale, save_plots, filepath, i)
                    file_data.update(sat_coords)
                    
                    # Konverter pixel koordinater til RA/DEC hvis vi har position
                    if not np.isnan(file_data.get('x_sat', np.nan)) and 'CD1_1' in file_data:
                        try:
                            x_sat = file_data['x_sat']
                            y_sat = file_data['y_sat']
                            
                            # Brug pixel_to_radec funktionen
                            # Opret en Series der ligner astap_row
                            import pandas as pd
                            header_row = pd.Series({
                                'CRPIX1': file_data['CRPIX1'],
                                'CRPIX2': file_data['CRPIX2'],
                                'CRVAL1': file_data['CRVAL1'],
                                'CRVAL2': file_data['CRVAL2'],
                                'CD1_1': file_data['CD1_1'],
                                'CD1_2': file_data['CD1_2'],
                                'CD2_1': file_data['CD2_1'],
                                'CD2_2': file_data['CD2_2']
                            })
                            
                            ra_sat, dec_sat = pixel_to_radec(x_sat, y_sat, header_row)
                            file_data['Sat_RA_Behandlet'] = ra_sat
                            file_data['Sat_DEC_Behandlet'] = dec_sat
                            self.analysis_log_message(f"Satellit RA/DEC: {ra_sat:.6f}°, {dec_sat:.6f}°\n =============================")
                        except Exception as e:
                            self.analysis_log_message(f"Fejl ved RA/DEC konvertering: {str(e)}")
                
                results.append(file_data)
                
            except Exception as e:
                self.analysis_log_message(f"Fejl i fil {filename}: {str(e)}")
                error_data = {'filename': filename, 'error': str(e)}
                results.append(error_data)
        
        self.analysis_progress_var.set(100)
        return pd.DataFrame(results)
    
    def find_satellite_line_leapfrog(self, image_data, header, save_plots, filepath, csv_index=None):
        """Find satellitlinje i LeapFrog billeder med intelligent tidskorrektion"""
        try:
            
            skalering = 4
            height, width = image_data.shape
            height, width = height/skalering, width/skalering
            
            # Nedskalerer billedet med cv2
            data_small = cv2.resize(image_data, (0, 0), fx=1/skalering, fy=1/skalering)

            # Gemmer til plot (kopier før ændringer)
            data_plot = data_small.copy()
            data_plot[data_plot > 1000] = 1000  # Clip høje værdier for bedre visning

            # Fjern pixels under medianen+5
            data_small[data_small < np.median(data_small)+5] = 0

            # Fjern objekter bestående af mindre end 100 pixels
            num_labels, labels_im = cv2.connectedComponents(data_small.astype(np.uint8))
            # Beregn størrelsen af hver komponent vectoriseret
            label_counts = np.bincount(labels_im.flat)
            # Find labels der skal fjernes (mindre end 100 pixels)
            small_labels = np.where(label_counts < 100)[0]
            # Opret mask for alle små objekter på én gang
            small_objects_mask = np.isin(labels_im, small_labels)
            # Fjern alle små objekter i én operation
            data_small[small_objects_mask] = 0

            #gør billedet binært
            _, binary_image = cv2.threshold(data_small, 1, 1, cv2.THRESH_BINARY)
                    
            # Find linjer med Hough transform
            binary_uint8 = (binary_image * 255).astype(np.uint8)
            lines = cv2.HoughLinesP(binary_uint8, 1, np.pi / 180, threshold=100, 
                                   minLineLength=25*skalering, maxLineGap=10)
            
            if lines is not None:
                self.analysis_log_message(f"Antal linjer fundet: {len(lines)}")
            else:
                self.analysis_log_message("❌ Ingen linjer fundet af Hough transform")
            
            result = {'antal_linjer': 0, 'x_sat': np.nan, 'y_sat': np.nan, 'corrected_obs_time': None}
            
            if lines is not None:
                antal_linjer = len(lines)
                
                best_line = max(lines, key=lambda l: np.hypot(l[0][2] - l[0][0], l[0][3] - l[0][1]))
                x1, y1, x2, y2 = best_line[0]
                
                # Tjek om linje rammer billedkanten
                edge_margin = 50
                is_edge1 = (x1 < edge_margin or x1 > width - edge_margin or
                           y1 < edge_margin or y1 > height - edge_margin)
                is_edge2 = (x2 < edge_margin or x2 > width - edge_margin or
                           y2 < edge_margin or y2 > height - edge_margin)
                
                self.analysis_log_message(f"Linje punkter:({x1:.0f},{y1:.0f})({x2:.0f},{y2:.0f})")
                self.analysis_log_message(f"Kant: Punkt1={is_edge1}, Punkt2={is_edge2}")
                
                # === INTELLIGENT TIDSKORREKTION ===
                # Hent data fra FITS header
                tle1 = header.get('TLE1', None)
                tle2 = header.get('TLE2', None)
                # Prøv DATE-STA først, derefter DATE_STA som fallback
                tidsstempel_start = header.get('DATE-STA', '') or header.get('DATE_STA', '')
                tidsstempel_slut = header.get('DATE-END', '') or header.get('DATE_END', '')
                longitude = header.get('LONG-OBS', 0)
                latitude = header.get('LAT-OBS', 0)  # Note: bruges LAT-OBS ikke LAT--OBS som i original
                elevation = header.get('ELEV-OBS', 0)
                rotation_angle = header.get('CROTA2', 0)
                
                corrected_obs_time = None
                
                if tle1 and tle2 and tidsstempel_start and tidsstempel_slut:
                    try:
                        # Parse tidsstempler
                        obs_time_start = datetime.strptime(tidsstempel_start, '%Y-%m-%dT%H:%M:%S.%f')
                        obs_time_slut = datetime.strptime(tidsstempel_slut, '%Y-%m-%dT%H:%M:%S.%f')
                        
                        # Beregn midtertidspunkt for satellitretningsberegning
                        delta_obs_time = obs_time_slut - obs_time_start
                        obs_time_mid = obs_time_start + timedelta(seconds=delta_obs_time.total_seconds()/2)
                        
                        # Beregn satellitretning med Skyfield ved midtertidspunkt
                        from skyfield.api import load, EarthSatellite, wgs84
                        ts = load.timescale()
                        t_mid = ts.utc(obs_time_mid.year, obs_time_mid.month, obs_time_mid.day, 
                                      obs_time_mid.hour, obs_time_mid.minute, obs_time_mid.second)
                        
                        satellite = EarthSatellite(tle1, tle2, name='sat', ts=ts)
                        observer = wgs84.latlon(latitude, longitude, elevation)
                        difference = satellite - observer
                        topocentric = difference.at(t_mid)
                        enu_velocity = topocentric.velocity.km_per_s
                        east_velocity = enu_velocity[0]
                        
                        self.analysis_log_message(f"Satellit bevæger sig mod {'øst' if east_velocity > 0 else 'vest'}")
                        
                        # Beregn skillelinje baseret på rotation
                        theta_rad = np.radians(-rotation_angle)  # MINUS som i original
                        x_c = (width - 1) / 2
                        y_c = (height - 1) / 2
                        nx = np.sin(theta_rad)
                        ny = np.cos(theta_rad)
                        
                        # Intelligent positionsbestemmelse baseret på kantdetektering
                        if is_edge1 or is_edge2:
                            self.analysis_log_message("Satellit linje rammer billedkant")
                            
                            if is_edge1:
                                non_edge_point = (x2, y2)
                                edge_point = (x1, y1)
                            else:
                                non_edge_point = (x1, y1)
                                edge_point = (x2, y2)
                            
                            mid_x, mid_y = non_edge_point
                            
                            # Beregn side-værdi for kantpunkt
                            px, py = edge_point
                            dx_p = px - x_c
                            dy_p = y_c - py  # Y er "nedad" i billedkoordinater
                            side_p = dx_p * ny - dy_p * nx
                            
                            # Bestem tidskorrektion baseret på satellitretning og kantposition
                            if side_p >= 0:  # Kantpunkt i vest
                                if east_velocity > 0:
                                    self.analysis_log_message("Kantpunkt i vest, satellit mod øst → slutpunkt, brug DATE-END")
                                    corrected_obs_time = obs_time_slut
                                else:
                                    self.analysis_log_message("Kantpunkt i vest, satellit mod vest → startpunkt, brug DATE-BEG")
                                    corrected_obs_time = obs_time_start
                            else:  # Kantpunkt i øst
                                if east_velocity > 0:
                                    self.analysis_log_message("Kantpunkt i øst, satellit mod øst → startpunkt, brug DATE-BEG")
                                    corrected_obs_time = obs_time_start
                                else:
                                    self.analysis_log_message("Kantpunkt i øst, satellit mod vest → slutpunkt, brug DATE-END")
                                    corrected_obs_time = obs_time_slut
                        else:
                            # Ingen kant - brug midtpunkt og halv exposure tid
                            mid_x = (x1 + x2) // 2
                            mid_y = (y1 + y2) // 2
                            corrected_obs_time = obs_time_start + pd.Timedelta(seconds=delta_obs_time.total_seconds()/2)
                            self.analysis_log_message(f"Ingen kant - midtpunkt, +{delta_obs_time.total_seconds()/2:.2f} sek")
                            
                    except Exception as e:
                        self.analysis_log_message(f"Advarsel: Tidskorrektion fejlede: {str(e)}")
                        # Fallback til standard metode
                        if is_edge1 or is_edge2:
                            if is_edge1:
                                mid_x, mid_y = x2, y2
                            else:
                                mid_x, mid_y = x1, y1
                        else:
                            mid_x = (x1 + x2) // 2
                            mid_y = (y1 + y2) // 2
                else:
                    # Manglende header data - brug standard metode
                    if is_edge1 or is_edge2:
                        if is_edge1:
                            mid_x, mid_y = x2, y2
                        else:
                            mid_x, mid_y = x1, y1
                    else:
                        mid_x = (x1 + x2) // 2
                        mid_y = (y1 + y2) // 2
                
                result = {
                    'antal_linjer': antal_linjer,
                    'x_sat': mid_x*skalering,
                    'y_sat': mid_y*skalering,
                    'x1': x1*skalering, 'y1': y1*skalering, 'x2': x2*skalering, 'y2': y2*skalering,
                    'corrected_obs_time': corrected_obs_time.strftime('%Y-%m-%dT%H:%M:%S.%f') if corrected_obs_time else None,
                    'rotation_angle': rotation_angle  # Tilføj rotation vinkel til plotting
                }
                
                # Plot hvis ønsket
                if save_plots:
                    self.plot_leapfrog_result(image_data, result, filepath, save_plots, csv_index)
            else:
                self.analysis_log_message("Ingen satellitlinje fundet - returnerer tomt resultat")
            

            return result
            
        except Exception as e:
            self.analysis_log_message(f"Fejl ved linjefinding: {str(e)}")
            return {'antal_linjer': 0, 'x_sat': np.nan, 'y_sat': np.nan, 'corrected_obs_time': None, 'error': str(e)}
    
    def find_satellite_position_tracking(self, image_data, header, pixelscale, save_plots, filepath, csv_index=None):
        """Find satellitposition i Tracking billeder"""
        try:
            # Find lyseste objekter
            num_top_pixels = 1000
            flat_indices = np.argpartition(image_data.ravel(), -num_top_pixels)[-num_top_pixels:]
            sorted_indices = flat_indices[np.argsort(image_data.ravel()[flat_indices])[::-1]]
            sorted_positions = np.unravel_index(sorted_indices, image_data.shape)
            
            # Lav maske omkring lyseste områder
            neighbor_radius = 80
            mask = np.zeros_like(image_data, dtype=bool)
            
            for y, x in zip(sorted_positions[0], sorted_positions[1]):
                y_start = max(0, y - neighbor_radius)
                y_end = min(image_data.shape[0], y + neighbor_radius + 1)
                x_start = max(0, x - neighbor_radius)
                x_end = min(image_data.shape[1], x + neighbor_radius + 1)
                mask[y_start:y_end, x_start:x_end] = True
            
            # Threshold og label objekter
            thresholded_data = mask & (image_data > np.median(image_data) + 30) # Virkede med mean + 0.75*std
            labeled_array, num_features = label(thresholded_data)
            object_slices = find_objects(labeled_array)
            
            # Find lyseste objekt der er stort nok
            brightest_object_slice = None
            max_val = -np.inf
            
            for slice_ in object_slices:
                if slice_ is None:
                    continue
                region = image_data[slice_]
                if region.shape[0] >= 20 and region.shape[1] >= 20:
                    region_mean = np.mean(region)
                    if region_mean > max_val:
                        max_val = region_mean
                        brightest_object_slice = slice_
            
            result = {'x_sat': np.nan, 'y_sat': np.nan, 'pixel_sum': np.nan}
            
            if brightest_object_slice is not None:
                y_start, y_stop = brightest_object_slice[0].start, brightest_object_slice[0].stop
                x_start, x_stop = brightest_object_slice[1].start, brightest_object_slice[1].stop
                y_center = (y_start + y_stop - 1) // 2
                x_center = (x_start + x_stop - 1) // 2
                
                # Beregn pixelsum i cirkel omkring centrum
                radius_pixelsum = self.tracking_pixelsum_radius.get()
                Y_grid, X_grid = np.ogrid[:image_data.shape[0], :image_data.shape[1]]
                distance_from_center = np.sqrt((X_grid - x_center)**2 + (Y_grid - y_center)**2)
                circular_mask = distance_from_center <= radius_pixelsum
                pixel_sum = np.sum(image_data[circular_mask])
                
                result = {
                    'x_sat': x_center,
                    'y_sat': y_center,
                    'pixel_sum': pixel_sum,
                    'image_median': np.median(image_data),
                    'image_mean': np.mean(image_data)
                }
                
                # Plot hvis ønsket
                if save_plots:
                    self.plot_tracking_result(image_data, result, filepath, save_plots, radius_pixelsum, csv_index)
            
            return result
            
        except Exception as e:
            self.analysis_log_message(f"Fejl ved positionsfinding: {str(e)}")
            return {'x_sat': np.nan, 'y_sat': np.nan, 'pixel_sum': np.nan, 'error': str(e)}
    
    def analyze_starfield_reference(self, directory, starfield_file, astap_path):
        """Analyser stjernehimmel reference med ASTAP"""
        try:
            self.analysis_log_message(f"Analyserer stjernehimmel reference med ASTAP...")
            
            filepath = os.path.join(directory, starfield_file)
            wcsfile = os.path.join(directory, starfield_file.replace(".fits", ".wcs"))
            
            # Kør ASTAP
            result = subprocess.run(
                [astap_path, "-f", filepath, "-wcs", wcsfile],
                capture_output=True, text=True
            )
            
            if result.returncode != 0:
                self.analysis_log_message(f"ASTAP fejlede: {result.stderr}")
                return {'ra_offset': 0, 'dec_offset': 0, 'rotation_offset': 0}
            
            # Læs WCS resultater
            if os.path.exists(wcsfile):
                with fits.open(wcsfile) as hdul:
                    wcs_header = hdul[0].header
                
                # Sammenlign med forventet position fra FITS header
                with fits.open(filepath) as hdul:
                    original_header = hdul[0].header
                
                expected_ra = original_header.get('RA', 0)
                expected_dec = original_header.get('DEC', 0)
                expected_rotation = original_header.get('field_angle_degs', 0)
                
                actual_ra = wcs_header.get('CRVAL1', expected_ra)
                actual_dec = wcs_header.get('CRVAL2', expected_dec)
                actual_rotation = wcs_header.get('CROTA2', expected_rotation)
                
                ra_offset = actual_ra - expected_ra
                dec_offset = actual_dec - expected_dec
                rotation_offset = actual_rotation - expected_rotation
                
                self.analysis_log_message(f"ASTAP offset: RA={ra_offset:.6f}°, DEC={dec_offset:.6f}°, ROT={rotation_offset:.3f}°")
                
                # Ryd op
                os.remove(wcsfile)
                
                return {
                    'ra_offset': ra_offset,
                    'dec_offset': dec_offset, 
                    'rotation_offset': rotation_offset
                }
            else:
                self.analysis_log_message("ASTAP producerede ingen WCS fil")
                return {'ra_offset': 0, 'dec_offset': 0, 'rotation_offset': 0}
                
        except Exception as e:
            self.analysis_log_message(f"Fejl ved ASTAP analyse: {str(e)}")
            return {'ra_offset': 0, 'dec_offset': 0, 'rotation_offset': 0}
    
    def plot_leapfrog_result(self, image_data, result, filepath, save_plot, csv_index=None):
        """Plot LeapFrog resultat - gemmer kun til fil, viser ikke interaktivt"""
        try:
            if not plt:
                return
            
            # Kun gem plot til fil - vis IKKE interaktivt fra worker thread
            if not save_plot:
                return  # Spring over hvis vi ikke gemmer
            
            # Downscale til visning
            target_height, target_width = 639, 958
            original_height, original_width = image_data.shape
            scale_y = target_height / original_height
            scale_x = target_width / original_width
            
            downscaled_image = zoom(image_data, (scale_y, scale_x), order=1)
            downscaled_image = np.clip(downscaled_image, None, 600)
            
            
            # Scale koordinater
            if not np.isnan(result['x_sat']):
                scaled_x = result['x_sat'] * scale_x
                scaled_y = result['y_sat'] * scale_y
                
                # Brug Agg backend for at undgå GUI
                import matplotlib
                matplotlib.use('Agg')
                from matplotlib.patches import Circle
                
                plt.figure(figsize=(12, 8))
                plt.imshow(downscaled_image, cmap='gray')
                plt.scatter(scaled_x, scaled_y, color='green', marker='x', s=100, label='Satellit position')
                
                if 'x1' in result:
                    scaled_x1 = result['x1'] * scale_x
                    scaled_y1 = result['y1'] * scale_y
                    scaled_x2 = result['x2'] * scale_x
                    scaled_y2 = result['y2'] * scale_y
                    
                    # Tilføj cirkler omkring endepunkterne i stedet for linje
                    circle_radius = 5  # Radius i pixels for cirklerne
                    circle1 = Circle((scaled_x1, scaled_y1), circle_radius, edgecolor='red', 
                                   facecolor='none', linewidth=1, label='Endepunkt 1')
                    circle2 = Circle((scaled_x2, scaled_y2), circle_radius, edgecolor='blue', 
                                   facecolor='none', linewidth=1, label='Endepunkt 2')
                    plt.gca().add_patch(circle1)
                    plt.gca().add_patch(circle2)
                
                # Tilføj øst/vest skillelinje hvis vi har rotation data
                if 'rotation_angle' in result:
                    rotation_angle = result['rotation_angle']
                    
                    # Samme beregning som i Func_fagprojekt.py (inspiration fra markeret kode)
                    theta_rad = np.radians(-rotation_angle)  # MINUS som i original
                    
                    # Brug scaled dimensioner
                    height_scaled, width_scaled = downscaled_image.shape
                    x_c = (width_scaled - 1) / 2
                    y_c = (height_scaled - 1) / 2
                    
                    # Beregn linjens retning (samme som i Func_fagprojekt.py)
                    dx_line = np.sin(theta_rad)
                    dy_line = -np.cos(theta_rad)
                    
                    # Find linjens endepunkter (går gennem centrum)
                    t_vals = np.linspace(-max(width_scaled, height_scaled), max(width_scaled, height_scaled), 1000)
                    x_line_all = x_c + t_vals * dx_line
                    y_line_all = y_c + t_vals * dy_line
                    
                    # Begræns til billedets grænser
                    mask_inside = (
                        (x_line_all >= 0) & (x_line_all < width_scaled) &
                        (y_line_all >= 0) & (y_line_all < height_scaled)
                    )
                    x_line = x_line_all[mask_inside]
                    y_line = y_line_all[mask_inside]
                    
                    # Tegn skillelinjen
                    plt.plot(x_line, y_line, color='yellow', linewidth=2, linestyle='--', 
                            label='Øst/Vest skillelinje', alpha=0.8)
                    
                    # Tilføj tekst labels for øst og vest
                    # Hvis linjen er nord-syd, skal øst/vest placeres vinkelret på linjen
                    # Beregn vinkelret retning til skillelinjen
                    offset = 50  # pixels
                    # Vinkelret retning: rotér 90 grader
                    dx_perp = -dy_line  # Vinkelret X-komponent
                    dy_perp = dx_line   # Vinkelret Y-komponent
                    
                    # Placér øst til venstre for linjen (negativ vinkelret retning)
                    east_x = x_c - offset * dx_perp
                    east_y = y_c - offset * dy_perp
                    # Placér vest til højre for linjen (positiv vinkelret retning)
                    west_x = x_c + offset * dx_perp
                    west_y = y_c + offset * dy_perp
                    
                    plt.text(west_x, west_y, 'VEST', color='yellow', fontsize=12, 
                            fontweight='bold', ha='center', va='center',
                            bbox=dict(boxstyle='round,pad=0.3', facecolor='black', alpha=0.7))
                    plt.text(east_x, east_y, 'ØST', color='yellow', fontsize=12, 
                            fontweight='bold', ha='center', va='center',
                            bbox=dict(boxstyle='round,pad=0.3', facecolor='black', alpha=0.7))
                
                plt.legend()
                # Use CSV index in title if available
                if csv_index is not None:
                    plt.title(f"Plot {csv_index+1:03d}: LeapFrog analyse - {os.path.basename(filepath)}")
                else:
                    plt.title(f"LeapFrog analyse: {os.path.basename(filepath)}")
                plt.xlabel("Pixel X")
                plt.ylabel("Pixel Y")
                
                # Gem til fil med samme navn som FITS-fil, bare .png
                plot_path = filepath.replace('.fits', '.png')
                plt.savefig(plot_path, dpi=150, bbox_inches='tight')
                plt.close()  # Vigtigt: luk figuren
                
                self.analysis_log_message(f"Plot gemt")
                
        except Exception as e:
            self.analysis_log_message(f"Fejl ved plotting: {str(e)}")
    
    def plot_tracking_result(self, image_data, result, filepath, save_plot, radius, csv_index=None):
        """Plot Tracking resultat - gemmer kun til fil, viser ikke interaktivt"""
        try:
            if not plt:
                return
            
            # Kun gem plot til fil - vis IKKE interaktivt fra worker thread
            if not save_plot:
                return  # Spring over hvis vi ikke gemmer
            
            # Downscale til visning
            target_height, target_width = 639, 958
            original_height, original_width = image_data.shape
            scale_y = target_height / original_height
            scale_x = target_width / original_width
            
            downscaled_image = zoom(image_data, (scale_y, scale_x), order=1)
            
            # Scale koordinater
            if not np.isnan(result['x_sat']):
                scaled_x = result['x_sat'] * scale_x
                scaled_y = result['y_sat'] * scale_y
                scaled_radius = radius * min(scale_x, scale_y)
                
                # Vis kun gyldige pixels for at undgå problemer med display
                valid_pixels = downscaled_image[downscaled_image > 0]
                if len(valid_pixels) > 0:
                    vmin = np.percentile(valid_pixels, 5)
                    vmax = np.percentile(valid_pixels, 99)
                else:
                    vmin, vmax = 0, 1
                
                # Brug Agg backend for at undgå GUI
                import matplotlib
                matplotlib.use('Agg')
                
                plt.figure(figsize=(12, 8))
                plt.imshow(downscaled_image, cmap='gray', vmin=vmin, vmax=vmax)
                
                # Tilføj cirkel og centrum
                circle = Circle((scaled_x, scaled_y), scaled_radius, edgecolor='cyan', 
                               facecolor='none', linewidth=2, label=f'Pixelsum radius ({radius}px)')
                plt.gca().add_patch(circle)
                plt.scatter(scaled_x, scaled_y, color='red', marker='+', s=100, label='Satellit centrum')
                
                plt.legend()
                # Use CSV index in title if available
                if csv_index is not None:
                    plt.title(f"Plot {csv_index+1:03d}: Tracking analyse - {os.path.basename(filepath)}\n"
                             f"Pixel sum: {result.get('pixel_sum', 0):.0f}")
                else:
                    plt.title(f"Tracking analyse: {os.path.basename(filepath)}\n"
                             f"Pixel sum: {result.get('pixel_sum', 0):.0f}")
                plt.xlabel("Pixel X")
                plt.ylabel("Pixel Y")
                
                # Gem til fil med samme navn som FITS-fil, bare .png
                plot_path = filepath.replace('.fits', '.png')
                plt.savefig(plot_path, dpi=150, bbox_inches='tight')
                plt.close()  # Vigtigt: luk figuren
                
                self.analysis_log_message(f"Plot gemt: {os.path.basename(plot_path)}")
                
        except Exception as e:
            self.analysis_log_message(f"Fejl ved plotting: {str(e)}")

    def display_plots_in_gui(self, directory):
        """Vis plot billeder i GUI'ens plot visning widget"""
        try:
            # Fjern placeholder
            if hasattr(self, 'plot_placeholder'):
                self.plot_placeholder.destroy()
            
            # Ryd eksisterende plots
            for widget in self.plot_scrollable_frame.winfo_children():
                widget.destroy()
            
            # Find alle gemte plot filer
            plot_files = sorted([f for f in os.listdir(directory) if f.endswith('.png')])
            
            if not plot_files:
                ttk.Label(self.plot_scrollable_frame, 
                         text="Ingen plots fundet", 
                         font=('Arial', 10), foreground='red').pack(pady=20)
                return
            
            self.analysis_log_message(f"Viser {len(plot_files)} plots i GUI...")
            
            # Vis hvert plot
            for i, plot_file in enumerate(plot_files):
                plot_path = os.path.join(directory, plot_file)
                
                try:
                    # Load billede med PIL
                    from PIL import Image, ImageTk
                    img = Image.open(plot_path)
                    
                    # Resize til GUI (maksimal bredde 450px for bedre visning)
                    max_width = 550
                    if img.width > max_width:
                        ratio = max_width / img.width
                        new_height = int(img.height * ratio)
                        img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
                    
                    # Konverter til tkinter format
                    photo = ImageTk.PhotoImage(img)
                    
                    # Frame for denne plot
                    plot_frame = ttk.LabelFrame(self.plot_scrollable_frame, 
                                              text=f"{i+1}. {plot_file.replace('_plot.png', '')}")
                    plot_frame.pack(fill='x', padx=5, pady=5)
                    
                    # Label til at vise billedet
                    img_label = tk.Label(plot_frame, image=photo)
                    img_label.image = photo  # Behold reference
                    img_label.pack(padx=5, pady=5)
                    
                except Exception as e:
                    # Fejl frame
                    error_frame = ttk.LabelFrame(self.plot_scrollable_frame, 
                                               text=f"Fejl: {plot_file}")
                    error_frame.pack(fill='x', padx=5, pady=5)
                    
                    ttk.Label(error_frame, 
                             text=f"Kunne ikke indlæse: {str(e)}", 
                             foreground='red').pack(padx=5, pady=5)
            
            # Opdater scroll region
            self.plot_scrollable_frame.update_idletasks()
            self.plot_canvas.configure(scrollregion=self.plot_canvas.bbox("all"))
            
            self.analysis_log_message(f"Plots vist i GUI - scroll for at se alle")
                
        except Exception as e:
            self.analysis_log_message(f"Fejl ved visning af plots i GUI: {str(e)}")

    def show_plots_manual(self):
        """Manuel visning af plots i GUI fra valgt mappe"""
        directory = self.analysis_dir_entry.get().strip()
        
        if not directory or not os.path.exists(directory):
            # Lad brugeren vælge en mappe
            directory = filedialog.askdirectory(
                title="Vælg mappe med plot billeder",
                initialdir=os.getcwd()
            )
            if not directory:
                return
                
        self.display_plots_in_gui(directory)

    def show_analysis_plots(self, directory):
        """Vis alle gemte analyse plots efter analysen er færdig"""
        try:
            import matplotlib
            matplotlib.use('TkAgg')  # Skift tilbage til GUI backend for visning
            
            # Find alle gemte plot filer
            plot_files = [f for f in os.listdir(directory) if f.endswith('_plot.png')]
            
            if not plot_files:
                self.analysis_log_message("Ingen plot filer fundet til visning")
                return
            
            self.analysis_log_message(f"Viser {len(plot_files)} gemte plots...")
            
            # Vis op til 6 plots ad gangen
            max_plots_per_window = 6
            
            for i in range(0, len(plot_files), max_plots_per_window):
                batch = plot_files[i:i+max_plots_per_window]
                
                # Beregn subplot layout
                n_plots = len(batch)
                if n_plots <= 2:
                    rows, cols = 1, n_plots
                elif n_plots <= 4:
                    rows, cols = 2, 2
                else:
                    rows, cols = 2, 3
                
                fig, axes = plt.subplots(rows, cols, figsize=(15, 10))
                if n_plots == 1:
                    axes = [axes]
                elif rows == 1 or cols == 1:
                    axes = axes.flatten()
                else:
                    axes = axes.flatten()
                
                for j, plot_file in enumerate(batch):
                    img_path = os.path.join(directory, plot_file)
                    
                    # Læs og vis billede
                    from PIL import Image
                    img = Image.open(img_path)
                    axes[j].imshow(img)
                    axes[j].set_title(plot_file.replace('_plot.png', ''), fontsize=10)
                    axes[j].axis('off')
                
                # Skjul tomme subplots
                for k in range(n_plots, len(axes)):
                    axes[k].axis('off')
                
                plt.tight_layout()
                plt.show()
                
        except Exception as e:
            self.analysis_log_message(f"Fejl ved visning af plots: {str(e)}")


    # =================
    # TLE BEREGNINGS METODER
    # =================
    
    def log_tle_message(self, message):
        """Tilføj besked til TLE loggen med tidsstempel"""
        try:
            if hasattr(self, 'tle_log_text'):
                timestamp = datetime.now().strftime('%H:%M:%S')
                log_entry = f"[{timestamp}] {message}\n"
                self.tle_log_text.insert(tk.END, log_entry)
                self.tle_log_text.see(tk.END)
                self.root.update()
        except:
            pass
    
    def select_tle_directory(self):
        """Vælg mappe med CSV-fil til TLE beregning"""
        directory = filedialog.askdirectory(
            title="Vælg mappe med data CSV-fil",
            initialdir=os.getcwd()
        )
        if directory:
            self.tle_dir_entry.delete(0, tk.END)
            self.tle_dir_entry.insert(0, directory)
            self.tle_csv_directory = directory
            
            # Automatisk indlæs data
            self.load_tle_csv_data(directory)
    
    def load_tle_csv_data(self, directory):
        """Load CSV file from folder for TLE calculation"""
        try:
            self.log_tle_message(f"Searching for CSV file in: {directory}")
            
            # Find CSV files starting with 'data'
            csv_files = [f for f in os.listdir(directory) if f.lower().startswith('data') and f.lower().endswith('.csv')]
            
            if not csv_files:
                self.log_tle_message("❌ No CSV files found starting with 'data'")
                self.tle_status_label.config(text="No data CSV file found in folder", foreground='red')
                messagebox.showerror("Error", "No CSV files found starting with 'data' in the selected folder")
                return
            
            # Use first file
            csv_file = csv_files[0]
            csv_path = os.path.join(directory, csv_file)
            self.log_tle_message(f"Found CSV file: {csv_file}")
            
            # Load CSV file
            df = pd.read_csv(csv_path)
            self.log_tle_message(f"✅ Loaded {len(df)} observations")

            # Filter out rows with OBSTYPE = 'stjernehimmel'
            if 'OBSTYPE' in df.columns:
                before_filter = len(df)
                df = df[df['OBSTYPE'] != 'stjernehimmel']
                after_filter = len(df)
                if before_filter != after_filter:
                    filtered_count = before_filter - after_filter
                    self.log_tle_message(f"Filtered out {filtered_count} starfield observations")
                    self.log_tle_message(f"✅ {after_filter} observations remaining after filtering")
            
            # Filter out rows where Sat_RA_Behandlet has no value
            if 'Sat_RA_Behandlet' in df.columns:
                before_filter = len(df)
                df = df[df['Sat_RA_Behandlet'].notna()]
                after_filter = len(df)
                if before_filter != after_filter:
                    filtered_count = before_filter - after_filter
                    self.log_tle_message(f"Filtered out {filtered_count} observations without processed data")
                    self.log_tle_message(f"✅ {after_filter} observations remaining after filtering")
            
            # Check that required columns exist for TLE calculation
            required_columns = ['Sat_RA_Behandlet', 'Sat_DEC_Behandlet', 'X_obs', 'Y_obs', 'Z_obs', 'DATE-OBS']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                self.log_tle_message(f"❌ Missing columns: {', '.join(missing_columns)}")
                messagebox.showerror("Error", f"CSV file is missing the following columns:\n{', '.join(missing_columns)}")
                return
            
            # Store data
            self.tle_csv_data = df
            
            # Update index dropdown menus
            self.log_tle_message("Updating index options...")
            indices = [str(i) for i in range(len(df))]
            
            self.index1_combo['values'] = indices
            self.index2_combo['values'] = indices
            self.index3_combo['values'] = indices
            
            # Set default selection (first, middle, last)
            if len(df) >= 3:
                middle_idx = len(df) // 2
                self.index1_combo.set(str(0))
                self.index2_combo.set(str(middle_idx))
                self.index3_combo.set(str(len(df) - 1))
                self.log_tle_message(f"✅ Default indices set: 0, {middle_idx}, {len(df)-1}")
            else:
                self.log_tle_message("WARNING: Less than 3 observations in CSV!")
                messagebox.showwarning("Warning", "CSV file contains less than 3 observations.\nAt least 3 observations are required for TLE calculation.")
            
            # Update status
            self.tle_status_label.config(text=f"✅ Data loaded: {csv_file} ({len(df)} obs.)", foreground='green')
            self.log_tle_message(f"✅ CSV data ready for TLE calculation")
            self.log_tle_message(f"   Columns: {', '.join(df.columns.tolist()[:10])}{'...' if len(df.columns) > 10 else ''}")
            
            # Check if TLE columns exist and calculate deviations if yes
            if 'TLE1' in df.columns and 'TLE2' in df.columns:
                self.log_tle_message("TLE columns found - calculating deviations...")
                self.calculate_tle_deviations(df)
            else:
                self.log_tle_message("TLE1 and TLE2 columns not found - cannot calculate deviations yet")
            
        except Exception as e:
            error_msg = f"Error loading CSV: {str(e)}"
            self.log_tle_message(f"❌ {error_msg}")
            self.tle_status_label.config(text="Error loading", foreground='red')
            messagebox.showerror("Error", error_msg)
            import traceback
            print(traceback.format_exc())
    
    def xyz_to_radec(self, x, y, z):
        """
        Konverterer ECI-koordinater (x,y,z) [km] til RA (grader) og DEC (grader).
        """
        r = np.array([x, y, z], dtype=float)
        norm = np.linalg.norm(r)
        if norm == 0:
            raise ValueError("Vector has zero length")

        # RA i radianer
        ra_rad = np.arctan2(r[1], r[0])
        if ra_rad < 0:
            ra_rad += 2*np.pi  # sikre 0–360°

        # DEC i radianer
        dec_rad = np.arcsin(r[2] / norm)

        ra_degrees = np.degrees(ra_rad)
        dec_degrees = np.degrees(dec_rad)

        return ra_degrees, dec_degrees
    
    def angle_diff_deg(self, a, b):
        """Returnerer vinkel-differens a-b i grader, wrap omkring 360, i intervallet [-180, 180]."""
        d = (a - b + 180) % 360 - 180
        return d
    
    def calculate_tle_deviations(self, results_df):
        """Calculate TLE deviations and update plot"""
        try:
            # Get TLE data from DataFrame
            if 'TLE1' not in results_df.columns or 'TLE2' not in results_df.columns:
                self.log_tle_message("❌ TLE1 and/or TLE2 columns not found in data")
                return
                
            tle_line1, tle_line2 = results_df['TLE1'].iloc[0], results_df['TLE2'].iloc[0]
            
            self.log_tle_message("Calculating satellite positions from TLE...")
            
            # Check required columns for calculate_satellite_data
            required_cols = ['DATE-OBS', 'LONG-OBS', 'ELEV-OBS']
            missing_cols = [col for col in required_cols if col not in results_df.columns]
            
            # Check LAT column (can have two different names)
            has_lat = 'LAT-OBS' in results_df.columns or 'LAT--OBS' in results_df.columns
            if not has_lat:
                missing_cols.append('LAT-OBS or LAT--OBS')
            
            if missing_cols:
                self.log_tle_message(f"❌ Missing columns for satellite calculation: {missing_cols}")
                self.log_tle_message(f"Available columns: {list(results_df.columns)}")
                return
            
            # Check if Func_fagprojekt functions are available
            try:
                # Reset DataFrame index to ensure sequential integer indices (0,1,2...)
                # This is necessary because calculate_satellite_data expects sequential indices
                df_for_calc = results_df.reset_index(drop=True)
                #df_for_calc = results_df.copy()
                self.log_tle_message(f"Reset DataFrame index for calculation")
                
                # Calculate satellite data
                afstand, vinkel, sat_pos, earth_pos, obs_points = calculate_satellite_data(
                    df_for_calc, tle_line1, tle_line2
                )
            except Exception as func_error:
                self.log_tle_message(f"❌ Error in calculate_satellite_data: {str(func_error)}")
                self.log_tle_message(f"Error type: {type(func_error).__name__}")
                self.log_tle_message("Check that Func_fagprojekt.py is available and compatible")
                # Log DataFrame info for debugging
                self.log_tle_message(f"DataFrame columns: {list(results_df.columns)}")
                self.log_tle_message(f"DataFrame shape: {results_df.shape}")
                self.log_tle_message(f"DataFrame index: {results_df.index.tolist()}")
                if len(results_df) > 0:
                    sample_row = results_df.iloc[0]
                    self.log_tle_message(f"First row example: DATE-OBS={sample_row.get('DATE-OBS', 'MISSING')}")
                    self.log_tle_message(f"LAT-OBS/LAT--OBS: {sample_row.get('LAT-OBS', sample_row.get('LAT--OBS', 'MISSING'))}")
                import traceback
                self.log_tle_message(f"Detailed error:\n{traceback.format_exc()}")
                return
            
            satellite_positions = np.array(sat_pos)
            observation_points = np.array(obs_points)
            
            # Calculate relative positions
            x_list = satellite_positions[:, 0] - observation_points[:, 0]
            y_list = satellite_positions[:, 1] - observation_points[:, 1]
            z_list = satellite_positions[:, 2] - observation_points[:, 2]
            
            # Convert to RA/DEC
            self.log_tle_message("Converting to RA/DEC coordinates...")
            ra_tle = []
            dec_tle = []
            for i in range(len(x_list)):
                ra, dec = self.xyz_to_radec(x_list[i], y_list[i], z_list[i])
                ra_tle.append(ra)
                dec_tle.append(dec)
            
            ra_tle = np.array(ra_tle)
            dec_tle = np.array(dec_tle)
            
            # Get observed positions
            try:
                sat_ra_behandlet = results_df['Sat_RA_Behandlet'].values
                sat_dec_behandlet = results_df['Sat_DEC_Behandlet'].values
                sat_ra_teleskop = results_df['RA_J2000'].values * 15  # Convert from hours to degrees
                sat_dec_teleskop = results_df['DEC'].values
            except KeyError as e:
                self.log_tle_message(f"❌ Missing column: {str(e)}")
                self.log_tle_message("Check that CSV file contains all necessary columns")
                return
            
            # Calculate deviations
            self.log_tle_message("Calculating deviations...")
            delta_ra_teleskop = self.angle_diff_deg(sat_ra_teleskop, ra_tle)
            delta_dec_teleskop = self.angle_diff_deg(sat_dec_teleskop, dec_tle)
            delta_ra_behandlet = self.angle_diff_deg(sat_ra_behandlet, ra_tle)
            delta_dec_behandlet = self.angle_diff_deg(sat_dec_behandlet, dec_tle)
            
            # Calculate time in seconds after first measurement
            if 'JD' in results_df.columns:
                jd_first = results_df["JD"].iloc[0]
                seconds_after_first_measurement = (results_df["JD"] - jd_first) * 86400
            else:
                # Calculate time from DATE-OBS column
                times_dt = pd.to_datetime(results_df['DATE-OBS'])
                first_time = times_dt.iloc[0]
                seconds_after_first_measurement = (times_dt - first_time).dt.total_seconds()
            
            # Store data
            self.tle_calculation_data = {
                'seconds': seconds_after_first_measurement,
                'delta_ra_behandlet': delta_ra_behandlet,
                'delta_dec_behandlet': delta_dec_behandlet,
                'delta_ra_teleskop': delta_ra_teleskop,
                'delta_dec_teleskop': delta_dec_teleskop,
                'sat_pos_tle_original': satellite_positions
            }
            
            self.log_tle_message(f"✅ Calculated deviations for {len(delta_ra_behandlet)} data points")
            
            # Update plot
            self.log_tle_message("Updating plot...")
            self.update_tle_plot()
            
        except Exception as e:
            error_msg = f"Error calculating TLE deviations: {str(e)}"
            self.log_tle_message(f"❌ {error_msg}")
            messagebox.showerror("Error", error_msg)
            import traceback
            print(traceback.format_exc())
    
    def update_tle_plot(self):
        """Update TLE deviation plot"""
        try:
            if self.tle_calculation_data is None:
                return
            
            # Get data
            seconds = self.tle_calculation_data['seconds']
            delta_ra_behandlet = self.tle_calculation_data['delta_ra_behandlet']
            delta_dec_behandlet = self.tle_calculation_data['delta_dec_behandlet']
            delta_ra_teleskop = self.tle_calculation_data['delta_ra_teleskop']
            delta_dec_teleskop = self.tle_calculation_data['delta_dec_teleskop']
            
            # Clear previous plot
            for ax in self.tle_plot_axes:
                ax.clear()
            
            # RA deviations (top subplot)
            indices = list(range(len(seconds)))
            self.tle_plot_axes[0].plot(indices, delta_ra_behandlet, label='Satellite ΔRA', 
                                      marker='o', linestyle='', color='blue')
            self.tle_plot_axes[0].plot(indices, delta_ra_teleskop, label='Telescope ΔRA', 
                                      marker='o', linestyle='', color='orange', fillstyle='none')
            
            # Connect points with dashed lines
            for i in range(len(seconds)):
                self.tle_plot_axes[0].plot([i, i], 
                                          [delta_ra_behandlet[i], delta_ra_teleskop[i]], 
                                          'k--', alpha=0.3, linewidth=0.8)
            
            self.tle_plot_axes[0].set_xlabel('Observation Index')
            self.tle_plot_axes[0].set_ylabel('Deviation (degrees)')
            self.tle_plot_axes[0].set_title('ΔRA: Observed - TLE')
            self.tle_plot_axes[0].legend()
            self.tle_plot_axes[0].grid(True, alpha=0.3)
            
            # DEC deviations (bottom subplot)
            self.tle_plot_axes[1].plot(indices, delta_dec_behandlet, label='Satellite ΔDEC', 
                                      marker='o', linestyle='', color='blue')
            self.tle_plot_axes[1].plot(indices, delta_dec_teleskop, label='Telescope ΔDEC', 
                                      marker='o', linestyle='', color='orange', fillstyle='none')
            
            # Connect points with dashed lines
            for i in range(len(seconds)):
                self.tle_plot_axes[1].plot([i, i], 
                                          [delta_dec_behandlet[i], delta_dec_teleskop[i]], 
                                          'k--', alpha=0.3, linewidth=0.8)
            
            self.tle_plot_axes[1].set_xlabel('Observation Index')
            self.tle_plot_axes[1].set_ylabel('Deviation (degrees)')
            self.tle_plot_axes[1].set_title('ΔDEC: Observed - TLE')
            self.tle_plot_axes[1].legend()
            self.tle_plot_axes[1].grid(True, alpha=0.3)
            
            # Update figure
            self.tle_plot_figure.tight_layout()
            self.tle_canvas.draw()
            
            self.log_tle_message("✅ Plot updated successfully")
            
        except Exception as e:
            error_msg = f"Error updating plot: {str(e)}"
            self.log_tle_message(f"❌ {error_msg}")
            print(error_msg)
            import traceback
            print(traceback.format_exc())
    
    # =================
    # TLE BEREGNINGS FUNKTIONER (fra notebook)
    # =================
    
    def double_R(self, times, meas, positions, satid=99999):
        """Double-R IOD metode"""
        arc_optical = ArcObs({'t': times, 'radec': meas, 'xyz_site': positions})
        arc_optical.lowess_smooth()
        
        earth = Body.from_name('Earth')
        arc_iod = arc_optical.iod(earth)
        arc_iod.doubleR(ellipse_only=False)
        self.log_tle_message(f"Double-R resultater:\n{arc_iod.df.to_string()}")
        
        result = arc_iod.df.iloc[0]
        
        ele0_dict = {
            'epoch': times[len(times)//2],
            'a': result['a'] / 6378.135,
            'ecc': result['ecc'],
            'inc': result['inc'],
            'raan': result['raan'],
            'argp': result['argp'],
            'M': result['M']
        }
        
        ta0, ele0, params = arc_optical._tle_generate(
            ele0_dict, satid, 
            reff='GCRF',
            bstar=0.0,
            classification='U',
            intldesg='00000A'
        )
        
        mu = 398600.4418
        coe = np.array([result['a']*6378.135, result['ecc'], result['inc'], 
                        result['raan'], result['argp'], result['nu']])
        rv = KeprvTrans.coe2rv(coe, mu)
        r = rv[0:3]
        v = rv[3:6]
        
        return (r, v, coe, (ta0, ele0, params))
    
    def multilaplace(self, times, meas, positions, satid=99999):
        """Multi-Laplace IOD metode"""
        arc_optical = ArcObs({'t': times, 'radec': meas, 'xyz_site': positions})
        arc_optical.lowess_smooth()
        
        earth = Body.from_name('Earth')
        arc_iod = arc_optical.iod(earth)
        arc_iod.multilaplace(ellipse_only=False)
        self.log_tle_message(f"Multi-Laplace resultater:\n{arc_iod.df.to_string()}")
        
        result = arc_iod.df.iloc[0]
        
        ele0_dict = {
            'epoch': times[len(times)//2],
            'a': result['a'] / 6378.135,
            'ecc': result['ecc'],
            'inc': result['inc'],
            'raan': result['raan'],
            'argp': result['argp'],
            'M': result['M']
        }
        
        ta0, ele0, params = arc_optical._tle_generate(
            ele0_dict, satid, 
            reff='GCRF',
            bstar=0.0,
            classification='U',
            intldesg='00000A'
        )
        
        mu = 398600.4418
        coe = np.array([result['a']*6378.135, result['ecc'], result['inc'], 
                        result['raan'], result['argp'], result['nu']])
        rv = KeprvTrans.coe2rv(coe, mu)
        r = rv[0:3]
        v = rv[3:6]
        
        return (r, v, coe, (ta0, ele0, params))
    
    def laplace(self, times, meas, positions, satid=99999):
        """Laplace IOD metode"""
        arc_optical = ArcObs({'t': times, 'radec': meas, 'xyz_site': positions})
        arc_optical.lowess_smooth()
        
        earth = Body.from_name('Earth')
        arc_iod = arc_optical.iod(earth)
        arc_iod.laplace(ellipse_only=False)
        self.log_tle_message(f"Laplace resultater:\n{arc_iod.df.to_string()}")
        
        result = arc_iod.df.iloc[0]
        
        ele0_dict = {
            'epoch': times[len(times)//2],
            'a': result['a'] / 6378.135,
            'ecc': result['ecc'],
            'inc': result['inc'],
            'raan': result['raan'],
            'argp': result['argp'],
            'M': result['M']
        }
        
        ta0, ele0, params = arc_optical._tle_generate(
            ele0_dict, satid, 
            reff='GCRF',
            bstar=0.0,
            classification='U',
            intldesg='00000A'
        )
        
        mu = 398600.4418
        coe = np.array([result['a']*6378.135, result['ecc'], result['inc'], 
                        result['raan'], result['argp'], result['nu']])
        rv = KeprvTrans.coe2rv(coe, mu)
        r = rv[0:3]
        v = rv[3:6]
        
        return (r, v, coe, (ta0, ele0, params))
    
    def gauss(self, times, meas, positions, satid=99999):
        """Gauss IOD metode"""
        arc_optical = ArcObs({'t': times, 'radec': meas, 'xyz_site': positions})
        arc_optical.lowess_smooth()
        
        earth = Body.from_name('Earth')
        arc_iod = arc_optical.iod(earth)
        arc_iod.gauss(ellipse_only=False)
        self.log_tle_message(f"Gauss resultater:\n{arc_iod.df.to_string()}")
        
        result = arc_iod.df.iloc[0]
        
        ele0_dict = {
            'epoch': times[len(times)//2],
            'a': result['a'] / 6378.135,
            'ecc': result['ecc'],
            'inc': result['inc'],
            'raan': result['raan'],
            'argp': result['argp'],
            'M': result['M']
        }
        
        ta0, ele0, params = arc_optical._tle_generate(
            ele0_dict, satid, 
            reff='GCRF',
            bstar=0.0,
            classification='U',
            intldesg='00000A'
        )
        
        mu = 398600.4418
        coe = np.array([result['a']*6378.135, result['ecc'], result['inc'], 
                        result['raan'], result['argp'], result['nu']])
        rv = KeprvTrans.coe2rv(coe, mu)
        r = rv[0:3]
        v = rv[3:6]
        
        return (r, v, coe, (ta0, ele0, params))
    
    def circular(self, times, meas, positions, satid=99999):
        """Circular orbit IOD metode"""
        arc_optical = ArcObs({'t': times, 'radec': meas, 'xyz_site': positions})
        arc_optical.lowess_smooth()
        
        earth = Body.from_name('Earth')
        arc_iod = arc_optical.iod(earth)
        arc_iod.circular(ellipse_only=False)
        self.log_tle_message(f"Circular resultater:\n{arc_iod.df.to_string()}")
        
        result = arc_iod.df.iloc[0]
        
        ele0_dict = {
            'epoch': times[len(times)//2],
            'a': result['a'] / 6378.135,
            'ecc': result['ecc'],
            'inc': result['inc'],
            'raan': result['raan'],
            'argp': result['argp'],
            'M': result['M']
        }
        
        ta0, ele0, params = arc_optical._tle_generate(
            ele0_dict, satid, 
            reff='GCRF',
            bstar=0.0,
            classification='U',
            intldesg='00000A'
        )
        
        mu = 398600.4418
        coe = np.array([result['a']*6378.135, result['ecc'], result['inc'], 
                        result['raan'], result['argp'], result['nu']])
        rv = KeprvTrans.coe2rv(coe, mu)
        r = rv[0:3]
        v = rv[3:6]
        
        return (r, v, coe, (ta0, ele0, params))
    
    def gooding(self, times, meas, positions, satid=99999):
        """Gooding IOD metode"""
        arc_optical = ArcObs({'t': times, 'radec': meas, 'xyz_site': positions})
        arc_optical.lowess_smooth()
        
        earth = Body.from_name('Earth')
        arc_iod = arc_optical.iod(earth)
        arc_iod.gooding(ellipse_only=False)
        self.log_tle_message(f"Gooding resultater:\n{arc_iod.df.to_string()}")
        
        result = arc_iod.df.iloc[0]
        
        ele0_dict = {
            'epoch': times[len(times)//2],
            'a': result['a'] / 6378.135,
            'ecc': result['ecc'],
            'inc': result['inc'],
            'raan': result['raan'],
            'argp': result['argp'],
            'M': result['M']
        }
        
        ta0, ele0, params = arc_optical._tle_generate(
            ele0_dict, satid, 
            reff='GCRF',
            bstar=0.0,
            classification='U',
            intldesg='00000A'
        )
        
        mu = 398600.4418
        coe = np.array([result['a']*6378.135, result['ecc'], result['inc'], 
                        result['raan'], result['argp'], result['nu']])
        rv = KeprvTrans.coe2rv(coe, mu)
        r = rv[0:3]
        v = rv[3:6]
        
        return (r, v, coe, (ta0, ele0, params))

    def parse_compact_tle_notation(self, s):
        """Parse kompakt TLE notation som '34500-3' -> float"""
        if s is None or s.strip() in ['', '00000-0']:
            return 0.0
        s = s.strip()
        m = re.match(r'^([+-]?)(\d{5})([+-])(\d+)$', s)
        if not m:
            raise ValueError(f"Uventet kompakt TLE-format: {s!r}")
        sign_mant, mantissa_str, sign_exp, exp_str = m.groups()
        mantissa = int(mantissa_str) / 1e5
        exp = int(exp_str) if sign_exp == '+' else -int(exp_str)
        value = mantissa * (10 ** exp)
        if sign_mant == '-':
            value = -value
        return value

    def _compact_tle_notation(self, value):
        """Konverter float til TLE kompakt notation som '34500-3' eller '-4500-5'
        
        Format: [±]XXXXX[±]Y hvor:
        - Første tegn er valgfrit minustegn for negativ mantissa
        - XXXXX er mantissa (5 cifre)
        - [±] er eksponent fortegn (+ eller -)
        - Y er eksponent (1-2 cifre)
        """
        if abs(value) < 5e-12:
            return "00000-0"
        
        s = f"{value:.5e}"
        mant_str, exp_str = s.split('e')
        mant = abs(float(mant_str))
        exp = int(exp_str)
        
        mantissa_int = int(round(mant * 1e5))
        if mantissa_int >= 100000:
            mantissa_int //= 10
            exp += 1
        
        sign_exp = '-' if exp < 0 else '+'
        exp_abs = abs(exp)
        sign_prefix = '-' if value < 0 else ''
        
        # Returnér uden padding - padding skal ske i Line 1 konstruktionen
        return f"{sign_prefix}{mantissa_int:05d}{sign_exp}{exp_abs}"

    def format_first_derivative(self, value):
        """Formatter mean motion dot til TLE: fx .00000186 eller -.0000186"""
        s = f"{value:.8f}"
        # Fjern ledende "0" før decimalpunktet, men behold minustegn hvis negativt
        if s.startswith("0"):
            s = s[1:]  # " 0.xxxxx" -> ".xxxxx"
        elif s.startswith("-0"):
            s = "-" + s[2:]  # "-0.xxxxx" -> "-.xxxxx"
        return s

    def format_tle(self, ta0, ele0, params, a):
        """Konverter orbdtools TLE data til standard TLE format (2 linjer)"""
        satid, reff, bstar, nddot, classification, intldesg, elnum, revnum = params
        n, ecc, inc, raan, argp, M = ele0

        # Epoch
        epoch_year = ta0.datetime.year % 100
        day_of_year = int(ta0.yday.split(':')[1])
        hour = ta0.datetime.hour
        minute = ta0.datetime.minute
        second = ta0.datetime.second + ta0.datetime.microsecond / 1e6
        frac = (hour + minute/60 + second/3600) / 24.0
        frac_str = f"{frac:.8f}"
        if frac_str.startswith("0"):
            frac_str = frac_str[1:]
        epoch_str = f"{epoch_year:02d}{day_of_year:03d}{frac_str}"
        if len(epoch_str) != 14:
            raise ValueError(f"Forkert epoch-længde: {epoch_str!r} (len={len(epoch_str)})")

        # Beregn mean motion fra a hvis nødvendigt
        GM = 3.986004415e5
        a_km = a
        n_rad = np.sqrt(GM / a_km**3)
        n_revperday = (n_rad / (2 * np.pi)) * 86400.0

        # Hent originale TLE-værdier hvis DataFrame findes
        df = getattr(self, "tle_csv_data", None)
        if df is not None and 'TLE1' in df.columns:
            original_tle1 = str(df['TLE1'].iloc[0])

            # Hent international designator (kolonne 10–17, 0-index 9:17)
            intldesg = original_tle1[9:17].strip()

            # Hent elementnummer (kolonne 65–68, 0-index 64:68)
            orig_elnum_str = original_tle1[64:68].strip()
            if orig_elnum_str.isdigit():
                orig_elnum = int(orig_elnum_str)
                # Læg +1 til hvis det ikke er 999
                elnum = orig_elnum + 1 if orig_elnum != 999 else 999
            else:
                elnum = int(elnum)

            # First derivative: kolonne 34–43, python slice 33:43
            try:
                first_deriv_str = original_tle1[33:43]
                mean_motion_dot = float(first_deriv_str.strip())
            except:
                mean_motion_dot = 0.0

            # Second derivative (ddot) kompakt notation: 45–52, slice 44:52
            try:
                ddot_field = original_tle1[44:52]
                nddot = self.parse_compact_tle_notation(ddot_field)
            except:
                nddot = 0.0

            # BSTAR kompakt notation: 54–61, slice 53:61
            try:
                bstar_field = original_tle1[53:61]
                bstar = self.parse_compact_tle_notation(bstar_field)
            except:
                bstar = 0.0

        # Formatter first derivative
        mean_motion_dot_str = self.format_first_derivative(mean_motion_dot)
        # Højre-justér mean_motion_dot_str til præcis 10 tegn
        mean_motion_dot_str = f"{mean_motion_dot_str:>10s}"

        # Formatter ddot og bstar til kompakt notation
        ddot_str = self._compact_tle_notation(nddot)
        bstar_str = self._compact_tle_notation(bstar)

        # Line 1
        # TLE format (kolonne-baseret):
        # 1 25544U 98067A   08264.51782528 -.00002182  00000-0 -11606-4 0  2927
        # Kolonne 34-43: mean motion dot (10 tegn), kolonne 45-52: ddot (8 tegn), kolonne 54-61: bstar (8 tegn)
        
        line1_data = (
            f"1 {satid:5d}{classification}"
            f" {intldesg:8s} "
            f"{epoch_str:14s} "
            f"{mean_motion_dot_str} "
            f"{ddot_str:>8s} "
            f"{bstar_str:>8s}"
            f" 0 {int(elnum):>4d}"
        )
        checksum1 = self.calculate_tle_checksum(line1_data)
        line1 = line1_data[:68] + str(checksum1)  # placer checksum i kolonne 69

        # Line 2
        ecc_str = f"{int(round(ecc * 1e7)):07d}"
        line2_data = (
            f"2 {satid:5d} "
            f"{inc:8.4f} "
            f"{raan:8.4f} "
            f"{ecc_str} "
            f"{argp:8.4f} "
            f"{M:8.4f} "
            f"{n_revperday:11.8f}"
            f"{int(revnum):5d}"
        )
        checksum2 = self.calculate_tle_checksum(line2_data)
        line2 = f"{line2_data}{checksum2}"

        return line1, line2
    
    def calculate_tle_checksum(self, line):
        """Beregn TLE checksum (modulo 10 sum af cifre, hvor - tæller som 1)"""
        checksum = 0
        for char in line:
            if char.isdigit():
                checksum += int(char)
            elif char == '-':
                checksum += 1
        return checksum % 10
    
    def beregn_TLE_fra_observationer(self, Sat_RA, Sat_DEC, X_obs, Y_obs, Z_obs, DATE_OBS, NoradID, metode, index_list=None):

        """Hovedfunktion til at beregne TLE fra observationer ved hjælp af forskellige IOD metoder"""
        if not ORBDTOOLS_AVAILABLE:
            self.log_tle_message("❌ FEJL: orbdtools ikke tilgængelig!")
            messagebox.showerror("Fejl", "orbdtools biblioteket er ikke installeret.\n\nInstaller med: pip install orbdtools")
            return None
        
        metode_funktioner = {
            'double_R': self.double_R,
            'multilaplace': self.multilaplace,
            'laplace': self.laplace,
            'gauss': self.gauss,
            'circular': self.circular,
            'gooding': self.gooding
        }
        
        if metode not in metode_funktioner:
            raise ValueError(f"Ukendt metode '{metode}'. Tilgængelige metoder: {list(metode_funktioner.keys())}")
        
        # Konverter input til numpy arrays
        Sat_RA = np.array(Sat_RA)
        Sat_DEC = np.array(Sat_DEC)
        X_obs = np.array(X_obs)
        Y_obs = np.array(Y_obs)
        Z_obs = np.array(Z_obs)
        
        if not isinstance(DATE_OBS, pd.Series):
            DATE_OBS = pd.to_datetime(DATE_OBS)
        
        angles = np.array([Sat_RA, Sat_DEC]).T
        positions = np.array([X_obs, Y_obs, Z_obs]).T
        
        if index_list is None:
            n = len(DATE_OBS)
            middle_idx = n // 2
            index_list = [0, middle_idx, n-1]
        
        # Tjek om vi bruger gooding metoden (kan håndtere alle datapunkter)
        if metode == 'gooding':
            # Gooding metoden: brug alle datapunkter
            self.log_tle_message(f"Bruger metode: {metode} (alle {len(DATE_OBS)} datapunkter)")
            
            if isinstance(DATE_OBS, pd.Series):
                tider_pandas = DATE_OBS.values
            else:
                tider_pandas = np.array(DATE_OBS)
            
            tider = Time(tider_pandas)
            r_ = positions
            angles_ = angles
        else:
            # Andre metoder: brug kun de 3 valgte indices
            if len(index_list) != 3:
                raise ValueError(f"index_list skal indeholde præcis 3 indices, fik {len(index_list)}")
            
            idx = index_list
            self.log_tle_message(f"Bruger metode: {metode} (indices: {idx})")
            
            if isinstance(DATE_OBS, pd.Series):
                tider_pandas = np.array([DATE_OBS.iloc[idx[0]], DATE_OBS.iloc[idx[1]], DATE_OBS.iloc[idx[2]]])
            else:
                tider_pandas = np.array([DATE_OBS[idx[0]], DATE_OBS[idx[1]], DATE_OBS[idx[2]]])
            
            tider = Time(tider_pandas)
            r_ = np.array([positions[idx[0]], positions[idx[1]], positions[idx[2]]])
            angles_ = np.array([angles[idx[0]], angles[idx[1]], angles[idx[2]]])
        
        metode_funktion = metode_funktioner[metode]
        R, v, coe, tle_data = metode_funktion(tider, angles_, r_, satid=NoradID)
        
        ta0, ele0, params = tle_data
        line1, line2 = self.format_tle(ta0, ele0, params, coe[0])
        
        return {
            'r': R,
            'v': v, 
            'coe': coe,
            'tle': tle_data,
            'tle_lines': (line1, line2),
            'method': metode
        }
    
    def log_tle_message(self, message):
        """Tilføj besked til TLE loggen med tidsstempel"""
        try:
            if hasattr(self, 'tle_log_text'):
                timestamp = datetime.now().strftime('%H:%M:%S')
                log_entry = f"[{timestamp}] {message}\n"
                self.tle_log_text.insert(tk.END, log_entry)
                self.tle_log_text.see(tk.END)  # Scroll til bunden
                self.root.update_idletasks()  # Opdater GUI
        except Exception as e:
            print(f"Log fejl: {e}")
    
    def calculate_tle_from_observations(self):
        """Beregner TLE baseret på valgte parametre"""
        try:
            # Tjek om data er indlæst
            if self.tle_csv_data is None:
                messagebox.showwarning("Ingen data", "Indlæs først en CSV-fil med observationsdata")
                self.log_tle_message("❌ Ingen data indlæst")
                return
            
            # Hent valgte indices
            try:
                idx1 = int(self.index1_combo.get())
                idx2 = int(self.index2_combo.get())
                idx3 = int(self.index3_combo.get())
                index_list = [idx1, idx2, idx3]
            except:
                messagebox.showerror("Fejl", "Vælg 3 gyldige indices")
                self.log_tle_message("❌ Ugyldige indices valgt")
                return
            
            # Validér at indices er forskellige
            if len(set(index_list)) != 3:
                messagebox.showerror("Fejl", "Vælg 3 forskellige indices")
                self.log_tle_message("❌ Indices skal være forskellige")
                return
            
            # Hent valgt metode
            metode = self.tle_method_combo.get()
            
            self.log_tle_message(f"Starter TLE beregning...")
            self.log_tle_message(f"Metode: {metode}")
            self.log_tle_message(f"Indices: {index_list}")
            
            # Hent data fra CSV
            df = self.tle_csv_data
            
            # Ekstraher nødvendige kolonner
            Sat_RA = df['Sat_RA_Behandlet'].values
            Sat_DEC = df['Sat_DEC_Behandlet'].values
            X_obs = df['X_obs'].values
            Y_obs = df['Y_obs'].values
            Z_obs = df['Z_obs'].values
            DATE_OBS = pd.to_datetime(df['DATE-OBS'])
            NoradID = int(df['NORAD_ID'].iloc[0]) if 'NORAD_ID' in df.columns else 99999
            
            self.log_tle_message(f"NORAD ID: {NoradID}")
            
            # Kald beregningsfunktionen
            result = self.beregn_TLE_fra_observationer(
                Sat_RA=Sat_RA,
                Sat_DEC=Sat_DEC,
                X_obs=X_obs,
                Y_obs=Y_obs,
                Z_obs=Z_obs,
                DATE_OBS=DATE_OBS,
                NoradID=NoradID,
                metode=metode,
                index_list=index_list
            )
            
            if result is None:
                self.log_tle_message("❌ TLE beregning fejlede")
                return
            
            # Gem resultat
            self.tle_result = result

            self.save_tle_results()
            
            # Vis TLE linjer
            line1, line2 = result['tle_lines']
            self.tle_line1_text.delete(1.0, tk.END)
            self.tle_line1_text.insert(1.0, line1)
            self.tle_line2_text.delete(1.0, tk.END)
            self.tle_line2_text.insert(1.0, line2)
            
            self.log_tle_message("✅ TLE genereret:")
            self.log_tle_message(f"{line1}")
            self.log_tle_message(f"{line2}")
            
            # Vis orbital elementer
            coe = result['coe']
            r = result['r']
            v = result['v']
            
            orbital_text = f"Position (r) [km]:\n"
            orbital_text += f"  x: {r[0]:.3f}\n"
            orbital_text += f"  y: {r[1]:.3f}\n"
            orbital_text += f"  z: {r[2]:.3f}\n\n"
            
            orbital_text += f"Hastighed (v) [km/s]:\n"
            orbital_text += f"  vx: {v[0]:.6f}\n"
            orbital_text += f"  vy: {v[1]:.6f}\n"
            orbital_text += f"  vz: {v[2]:.6f}\n\n"
            
            orbital_text += f"Classical Orbital Elements:\n"
            orbital_text += f"  a (semi-major axis): {coe[0]:.3f} [km]\n"
            orbital_text += f"  e (eccentricity): {coe[1]:.6f}\n"
            orbital_text += f"  i (inclination): {coe[2]:.4f}°\n"
            orbital_text += f"  Ω (RAAN): {coe[3]:.4f}°\n"
            orbital_text += f"  ω (arg of perigee): {coe[4]:.4f}°\n"
            orbital_text += f"  ν (true anomaly): {coe[5]:.4f}°"
            
            self.orbital_elements_text.delete(1.0, tk.END)
            self.orbital_elements_text.insert(1.0, orbital_text)
            
            self.log_tle_message(f"✅ Orbital elementer beregnet")
            
            # Tilføj beregnede TLE linjer til DataFrame og beregn afvigelser
            if self.tle_csv_data is not None:
                self.log_tle_message("Tilføjer TLE linjer til data og beregner afvigelser...")
                df_updated = self.tle_csv_data.copy()
                df_updated['TLE1_beregnet'] = line1
                df_updated['TLE2_beregnet'] = line2
                self.tle_csv_data = df_updated  # Opdater den gemte data
                self.calculate_tle_deviations(df_updated)
            
            messagebox.showinfo("Succes", f"TLE beregnet succesfuldt med {metode} metoden!")
            
        except Exception as e:
            error_msg = f"Fejl ved TLE beregning: {str(e)}"
            self.log_tle_message(f"❌ {error_msg}")
            messagebox.showerror("Fejl", error_msg)
            import traceback
            print(traceback.format_exc())
    
    def show_tle_3d_plot(self):
        """Show 3D plot of calculated TLE"""
        try:
            if self.tle_result is None:
                messagebox.showwarning("No Result", "Calculate a TLE first")
                return
            
            if not PLOTLY_AVAILABLE:
                messagebox.showerror("Error", "Plotly not available")
                return
            
            self.log_tle_message("Generating 3D plot...")
            
            # Create 3D plot (similar to LeapFrog plot)
            earth_radius = 6371
            u, v = np.mgrid[0:2*np.pi:100j, 0:np.pi:50j]
            x = earth_radius * np.cos(u) * np.sin(v)
            y = earth_radius * np.sin(u) * np.sin(v)
            z = earth_radius * np.cos(v)
            
            fig = go.Figure()
            
            # Add Earth
            fig.add_trace(go.Surface(
                x=x, y=y, z=z,
                colorscale='Blues',
                opacity=0.5,
                showscale=False,
                name='Earth'
            ))
            
            # Calculate satellite orbit from TLE
            satellite = None  # Initialize satellite variable
            ts_times = None  # Initialize ts_times for reuse

            # Get data
            df = self.tle_csv_data
            
            if SKYFIELD_AVAILABLE:
                ts = load.timescale()
                
                # Get calculated TLE from DataFrame
                if 'Calculated_TLE_Line1' in df.columns and 'Calculated_TLE_Line2' in df.columns:
                    line1 = df['Calculated_TLE_Line1'].iloc[0]
                    line2 = df['Calculated_TLE_Line2'].iloc[0]
                    
                    self.log_tle_message(f"TLE Lines from DataFrame:\n{line1}\n{line2}")
                    
                else:
                    self.log_tle_message("Calculated_TLE_Line1/Calculated_TLE_Line2 columns not found in CSV")
                    # Fallback to self.tle_result if DataFrame columns not found
                    if self.tle_result and 'tle_lines' in self.tle_result:
                        line1, line2 = self.tle_result['tle_lines']
                        self.log_tle_message(f"Fallback to TLE from tle_result:\n{line1}\n{line2}")
                    else:
                        line1, line2 = None, None
                        self.log_tle_message("❌ No TLE data available")
                
                # Validate calculated TLE data
                if line1 and line2:
                    self.log_tle_message("Creating satellite from calculated TLE...")
                    
                    try:
                        satellite = EarthSatellite(line1, line2, 'Calculated TLE', ts)
                        self.log_tle_message("✅ Calculated TLE satellite created successfully")
                    except Exception as e:
                        self.log_tle_message(f"❌ Could not create satellite from calculated TLE: {str(e)}")
                        satellite = None
                else:
                    self.log_tle_message("❌ Calculated TLE data missing or empty")
                    satellite = None
                
                if satellite is not None:
                    # Use times from data
                    times = pd.to_datetime(df['DATE-OBS'])
                    t_center = times.iloc[len(times)//2]
                    
                    # Generate times +/- 45 min
                    time_range = [t_center + pd.Timedelta(seconds=delta) for delta in np.arange(-45*60, 45*60 + 5, 5)]
                    
                    # Convert to Skyfield format
                    years = [t.year for t in time_range]
                    months = [t.month for t in time_range]
                    days = [t.day for t in time_range]
                    hours = [t.hour for t in time_range]
                    minutes = [t.minute for t in time_range]
                    seconds = [t.second + t.microsecond/1e6 for t in time_range]
                    
                    ts_times = ts.utc(years, months, days, hours, minutes, seconds)
                    
                    # Calculate positions
                    tle_positions = satellite.at(ts_times).position.km.T
                    
                    # Plot orbit
                    fig.add_trace(go.Scatter3d(
                        x=tle_positions[:, 0],
                        y=tle_positions[:, 1],
                        z=tle_positions[:, 2],
                        mode='lines',
                        name=f'Calculated TLE ({self.tle_result["method"]})',
                        line=dict(width=3, color='red')
                    ))
                
                    # Plot original TLE if available and we have valid time intervals
                    if 'TLE1' in df.columns and 'TLE2' in df.columns and 'ts_times' in locals():
                        original_tle1 = df['TLE1'].iloc[0]
                        original_tle2 = df['TLE2'].iloc[0]
                        
                        if pd.notna(original_tle1) and pd.notna(original_tle2) and original_tle1.strip() and original_tle2.strip():
                            self.log_tle_message("Plotting original TLE...")
                            
                            try:
                                original_satellite = EarthSatellite(original_tle1, original_tle2, 'Original TLE', ts)
                                
                                # Calculate positions for original TLE (same time interval)
                                original_tle_positions = original_satellite.at(ts_times).position.km.T
                            
                                
                                # Plot original orbit
                                fig.add_trace(go.Scatter3d(
                                    x=original_tle_positions[:, 0],
                                    y=original_tle_positions[:, 1],
                                    z=original_tle_positions[:, 2],
                                    mode='lines',
                                    name='Original TLE',
                                    line=dict(width=3, color='blue', dash='dot')
                                ))
                                
                                self.log_tle_message("✅ Original TLE added to plot")
                                
                            except Exception as e:
                                self.log_tle_message(f"⚠️ Could not plot original TLE: {str(e)}")
                        else:
                            self.log_tle_message("⚠️ Original TLE data missing or empty")
                    else:
                        self.log_tle_message("⚠️ TLE1/TLE2 columns not found in CSV or no time interval")
                else:
                    self.log_tle_message("⚠️ Could not create calculated TLE satellite")
                    
            else:
                self.log_tle_message("⚠️ Skyfield not available, cannot show calculated orbit from TLE")
            
            # Calculate satellite positions based on RA/DEC from CSV and distance from TLE
            if satellite is not None and 'Sat_RA_Behandlet' in df.columns and 'Sat_DEC_Behandlet' in df.columns:
                self.log_tle_message("Calculating satellite positions from RA/DEC and TLE distance...")
                
                # Get RA/DEC from CSV
                sat_ra_behandlet = df['Sat_RA_Behandlet'].values  # degrees
                sat_dec_behandlet = df['Sat_DEC_Behandlet'].values  # degrees
                obs_times = pd.to_datetime(df['DATE-OBS'])
                
                # Convert observation times to Skyfield format
                obs_years = [t.year for t in obs_times]
                obs_months = [t.month for t in obs_times]
                obs_days = [t.day for t in obs_times]
                obs_hours = [t.hour for t in obs_times]
                obs_minutes = [t.minute for t in obs_times]
                obs_seconds = [t.second + t.microsecond/1e6 for t in obs_times]
                
                ts_obs_times = ts.utc(obs_years, obs_months, obs_days, obs_hours, obs_minutes, obs_seconds)
                self.log_tle_message(f"Times for satellite {ts_obs_times}")
                # Calculate satellite positions from TLE at observation times
                tle_sat_positions = satellite.at(ts_obs_times).position.km
                
                # Calculate distance from observer to satellite (from TLE)
                obs_x = df['X_obs'].values
                obs_y = df['Y_obs'].values
                obs_z = df['Z_obs'].values
                obs_positions = np.array([obs_x, obs_y, obs_z]).T
                
                distances = []
                for i in range(len(tle_sat_positions.T)):
                    sat_pos = tle_sat_positions.T[i]
                    obs_pos = obs_positions[i]
                    distance = np.linalg.norm(sat_pos - obs_pos)
                    distances.append(distance)
                
                distances = np.array(distances)
                if np.isnan(distances).any():
                    self.log_tle_message("❌ Calculated distances contain NaN values")
                
                
                # Convert RA/DEC + distance to ECI xyz coordinates
                self.log_tle_message("Converting RA/DEC/Distance to ECI xyz...")
                sat_xyz_from_radec = []
                
                for i in range(len(sat_ra_behandlet)):
                    ra_rad = np.radians(sat_ra_behandlet[i])
                    dec_rad = np.radians(sat_dec_behandlet[i])
                    dist = distances[i]
                    
                    # Spherical to Cartesian coordinates (relative to observer)
                    x_rel = dist * np.cos(dec_rad) * np.cos(ra_rad)
                    y_rel = dist * np.cos(dec_rad) * np.sin(ra_rad)
                    z_rel = dist * np.sin(dec_rad)
                    
                    # Add observer position to get absolute ECI coordinates
                    x_abs = x_rel + obs_positions[i][0]
                    y_abs = y_rel + obs_positions[i][1]
                    z_abs = z_rel + obs_positions[i][2]
                    
                    sat_xyz_from_radec.append([x_abs, y_abs, z_abs])
                
                sat_xyz_from_radec = np.array(sat_xyz_from_radec)
                
                # Plot satellite positions calculated from RA/DEC and TLE distance
                fig.add_trace(go.Scatter3d(
                    x=sat_xyz_from_radec[:, 0],
                    y=sat_xyz_from_radec[:, 1],
                    z=sat_xyz_from_radec[:, 2],
                    mode='markers',
                    name='Satellite pos. obs (RA/DEC + TLE dist.)',
                    marker=dict(size=5, color='red', symbol='diamond')
                ))
                
                self.log_tle_message(f"✅ Added {len(sat_xyz_from_radec)} satellite positions from RA/DEC")

                # Plot satellite positions from TLE
                fig.add_trace(go.Scatter3d(
                    x=self.tle_calculation_data['sat_pos_tle_original'][:, 0],
                    y=self.tle_calculation_data['sat_pos_tle_original'][:, 1],
                    z=self.tle_calculation_data['sat_pos_tle_original'][:, 2],
                    mode='markers',
                    name='Satellite pos. TLE',
                    marker=dict(size=5, color='blue', symbol='diamond')
                ))
            
            # Plot observation points
            obs_x = df['X_obs'].values
            obs_y = df['Y_obs'].values
            obs_z = df['Z_obs'].values
            
            fig.add_trace(go.Scatter3d(
                x=obs_x,
                y=obs_y,
                z=obs_z,
                mode='markers',
                name='Observer positions',
                marker=dict(size=3, color='orange', symbol='circle')
            ))
            
            # Layout
            fig.update_layout(
                scene=dict(
                    xaxis_title='X (km)',
                    yaxis_title='Y (km)',
                    zaxis_title='Z (km)',
                    aspectmode='data'
                ),
                title=f'TLE Calculation ({self.tle_result["method"]} method)',
                showlegend=True
            )
            
            # Show plot
            pyo.plot(fig, filename='tle_3d_plot.html', auto_open=True)
            
            self.log_tle_message("✅ 3D plot shown in browser")
            
        except Exception as e:
            error_msg = f"Error plotting: {str(e)}"
            self.log_tle_message(f"❌ {error_msg}")
            messagebox.showerror("Error", error_msg)
    
    def save_tle_results(self):
        """Save TLE results to CSV file"""
        try:
            if self.tle_result is None:
                messagebox.showwarning("No Result", "Calculate a TLE first")
                return
            
            if self.tle_csv_directory is None:
                messagebox.showwarning("No File", "Load a CSV file first")
                return
            
            self.log_tle_message("Saving results to CSV...")
            
            # Find CSV file again
            csv_files = [f for f in os.listdir(self.tle_csv_directory) if f.startswith('data') and f.endswith('.csv')]
            
            if not csv_files:
                messagebox.showerror("Error", "Could not find CSV file in folder")
                return
            
            csv_path = os.path.join(self.tle_csv_directory, csv_files[0])
            
            # Load CSV
            df = pd.read_csv(csv_path)
            
            # Add new columns with TLE data
            line1, line2 = self.tle_result['tle_lines']
            df['Calculated_TLE_Line1'] = line1
            df['Calculated_TLE_Line2'] = line2
            df['TLE_Method'] = self.tle_result['method']
            
            # Add orbital elements
            coe = self.tle_result['coe']
            df['TLE_a_km'] = coe[0]
            df['TLE_ecc'] = coe[1]
            df['TLE_inc_deg'] = coe[2]
            df['TLE_raan_deg'] = coe[3]
            df['TLE_argp_deg'] = coe[4]
            df['TLE_nu_deg'] = coe[5]
            
            # Add position and velocity
            r = self.tle_result['r']
            v = self.tle_result['v']
            df['TLE_r_x_km'] = r[0]
            df['TLE_r_y_km'] = r[1]
            df['TLE_r_z_km'] = r[2]
            df['TLE_v_x_kms'] = v[0]
            df['TLE_v_y_kms'] = v[1]
            df['TLE_v_z_kms'] = v[2]
            
            # Save updated CSV
            df.to_csv(csv_path, index=False)
            
            self.log_tle_message(f"✅ Results saved to: {csv_files[0]}")
            self.log_tle_message(f"Added columns:")
            self.log_tle_message(f"- Calculated_TLE_Line1, Calculated_TLE_Line2")
            self.log_tle_message(f"- TLE_Method, orbital elements (a,e,i,Ω,ω,ν)")
            self.log_tle_message(f"- Position (r_x,r_y,r_z) and velocity (v_x,v_y,v_z)")
            
            
        except Exception as e:
            error_msg = f"Error saving: {str(e)}"
            self.log_tle_message(f"❌ {error_msg}")
            messagebox.showerror("Error", error_msg)

if __name__ == "__main__":
    root = tk.Tk()
    app = TkinterDemo(root)
    root.mainloop()
    
