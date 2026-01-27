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
    
    def optimized_camera_exposure_with_timing(self, camera, exposure_time, pw4_client, pw4_url, obstype='satellite'):
        """Wrapper: Optimeret kamera eksponering med præcise tidsstempler"""
        from Func_KameraInstillinger import optimized_camera_exposure_with_timing as func
        return func(self, camera, exposure_time, pw4_client, pw4_url, obstype)

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
        """Wrapper for tracking log message"""
        from Func_Tracking import tracking_log_message
        return tracking_log_message(self, message)
    
    def test_pw4_connection(self):
        """Wrapper for testing PWI4 connection"""
        from Func_Tracking import test_pw4_connection
        return test_pw4_connection(self)
    
    def get_selected_satellite_for_tracking(self):
        """Wrapper for getting selected satellite"""
        from Func_Tracking import get_selected_satellite_for_tracking
        return get_selected_satellite_for_tracking(self)
    
    def use_manual_tle(self):
        """Wrapper for using manual TLE"""
        from Func_Tracking import use_manual_tle
        return use_manual_tle(self)
    
    def validate_tracking_parameters(self):
        """Wrapper for validating tracking parameters"""
        from Func_Tracking import validate_tracking_parameters
        return validate_tracking_parameters(self)
    
    def start_tracking_observation(self):
        """Wrapper for starting tracking observation"""
        from Func_Tracking import start_tracking_observation
        return start_tracking_observation(self)
    
    def stop_tracking_observation(self):
        """Wrapper for stopping tracking observation"""
        from Func_Tracking import stop_tracking_observation
        return stop_tracking_observation(self)
    
    def run_tracking_observation(self):
        """Wrapper: Kør tracking observation med PlaneWave4"""
        from Func_Tracking import run_tracking_observation as func
        return func(self)

    # =================
    # BILLEDE ANALYSE METODER
    # =================
    
    def analysis_log_message(self, message):
        """Tilføj besked til analyse log - delegeret til Func_BilledeAnalyse"""
        from Func_BilledeAnalyse import analysis_log_message
        analysis_log_message(self, message)
    
    def setup_plot_display(self, parent_frame):
        """Opsæt plot visning område med scrollbar - delegeret til Func_BilledeAnalyse"""
        from Func_BilledeAnalyse import setup_plot_display
        setup_plot_display(self, parent_frame)
    
    def select_analysis_directory(self):
        """Vælg mappe med billeder til analyse - delegeret til Func_BilledeAnalyse"""
        from Func_BilledeAnalyse import select_analysis_directory
        select_analysis_directory(self)

    def select_astap_path(self):
        """Vælg ASTAP executable - delegeret til Func_BilledeAnalyse"""
        from Func_BilledeAnalyse import select_astap_path
        select_astap_path(self)

    def start_image_analysis(self):
        """Start billede analyse i separat tråd - delegeret til Func_BilledeAnalyse"""
        from Func_BilledeAnalyse import start_image_analysis
        start_image_analysis(self)

    def stop_image_analysis(self):
        """Stop billede analyse - delegeret til Func_BilledeAnalyse"""
        from Func_BilledeAnalyse import stop_image_analysis
        stop_image_analysis(self)
    
    def run_image_analysis(self):
        """Kør billede analyse - delegeret til Func_BilledeAnalyse"""
        from Func_BilledeAnalyse import run_image_analysis
        run_image_analysis(self)
    
    def run_astap_on_directory(self, directory, astap_exe=r"C:\Program Files\astap\astap.exe"):
        """Kør ASTAP på alle FITS filer i en mappe - delegeret til Func_BilledeAnalyse"""
        from Func_BilledeAnalyse import run_astap_on_directory
        return run_astap_on_directory(self, directory, astap_exe)
    
    def analyze_leapfrog_images(self, directory, fits_files, astap_path, pixelscale, save_plots):
        """Analyser LeapFrog billeder - delegeret til Func_BilledeAnalyse"""
        from Func_BilledeAnalyse import analyze_leapfrog_images
        return analyze_leapfrog_images(self, directory, fits_files, astap_path, pixelscale, save_plots)
    
    def analyze_tracking_images(self, directory, fits_files, astap_path, pixelscale, save_plots):
        """Analyser Tracking billeder - delegeret til Func_BilledeAnalyse"""
        from Func_BilledeAnalyse import analyze_tracking_images
        return analyze_tracking_images(self, directory, fits_files, astap_path, pixelscale, save_plots)
    
    def find_satellite_line_leapfrog(self, image_data, header, save_plots, filepath, csv_index=None):
        """Find satellitlinje i LeapFrog billeder - delegeret til Func_BilledeAnalyse"""
        from Func_BilledeAnalyse import find_satellite_line_leapfrog
        return find_satellite_line_leapfrog(self, image_data, header, save_plots, filepath, csv_index)
    
    def find_satellite_position_tracking(self, image_data, header, pixelscale, save_plots, filepath, csv_index=None):
        """Find satellitposition i Tracking billeder - delegeret til Func_BilledeAnalyse"""
        from Func_BilledeAnalyse import find_satellite_position_tracking
        return find_satellite_position_tracking(self, image_data, header, pixelscale, save_plots, filepath, csv_index)
    
    def analyze_starfield_reference(self, directory, starfield_file, astap_path):
        """Analyser stjernehimmel reference med ASTAP - delegeret til Func_BilledeAnalyse"""
        from Func_BilledeAnalyse import analyze_starfield_reference
        return analyze_starfield_reference(self, directory, starfield_file, astap_path)
    
    def plot_leapfrog_result(self, image_data, result, filepath, save_plot, csv_index=None):
        """Plot LeapFrog resultat - delegeret til Func_BilledeAnalyse"""
        from Func_BilledeAnalyse import plot_leapfrog_result
        plot_leapfrog_result(self, image_data, result, filepath, save_plot, csv_index)
    
    def plot_tracking_result(self, image_data, result, filepath, save_plot, radius, csv_index=None):
        """Plot Tracking resultat - delegeret til Func_BilledeAnalyse"""
        from Func_BilledeAnalyse import plot_tracking_result
        plot_tracking_result(self, image_data, result, filepath, save_plot, radius, csv_index)

    def display_plots_in_gui(self, directory):
        """Vis plot billeder i GUI'ens plot visning widget - delegeret til Func_BilledeAnalyse"""
        from Func_BilledeAnalyse import display_plots_in_gui
        display_plots_in_gui(self, directory)

    def show_plots_manual(self):
        """Manuel visning af plots i GUI fra valgt mappe - delegeret til Func_BilledeAnalyse"""
        from Func_BilledeAnalyse import show_plots_manual
        show_plots_manual(self)

    def show_analysis_plots(self, directory):
        """Vis alle gemte analyse plots efter analysen er færdig - delegeret til Func_BilledeAnalyse"""
        from Func_BilledeAnalyse import show_analysis_plots
        show_analysis_plots(self, directory)



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
    
