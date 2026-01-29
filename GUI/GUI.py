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
    
    def create_plan_observations_tab(self, notebook):
        """Wrapper for plan observations tab from Func_plan"""
        from Func_plan import create_plan_observations_tab as plan_func
        plan_func(self, notebook)

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
    # TLE BEREGNINGS METODER - DELEGEREDE TIL FUNC_CALCULATETLE
    # =================
    
    def log_tle_message(self, message):
        """Tilføj besked til TLE loggen med tidsstempel - delegeret til Func_CalculateTLE"""
        from Func_CalculateTLE import log_tle_message
        log_tle_message(self, message)
    
    def select_tle_directory(self):
        """Vælg mappe med CSV-fil til TLE beregning - delegeret til Func_CalculateTLE"""
        from Func_CalculateTLE import select_tle_directory
        select_tle_directory(self)
    
    def load_tle_csv_data(self, directory):
        """Load CSV file from folder for TLE calculation - delegeret til Func_CalculateTLE"""
        from Func_CalculateTLE import load_tle_csv_data
        load_tle_csv_data(self, directory)
    
    def xyz_to_radec(self, x, y, z):
        """Konverterer ECI-koordinater til RA/DEC - delegeret til Func_CalculateTLE"""
        from Func_CalculateTLE import xyz_to_radec
        return xyz_to_radec(self, x, y, z)
    
    def angle_diff_deg(self, a, b):
        """Beregner vinkelforskelle - delegeret til Func_CalculateTLE"""
        from Func_CalculateTLE import angle_diff_deg
        return angle_diff_deg(self, a, b)
    
    def calculate_tle_deviations(self, results_df):
        """Calculate TLE deviations and update plot - delegeret til Func_CalculateTLE"""
        from Func_CalculateTLE import calculate_tle_deviations
        calculate_tle_deviations(self, results_df)
    
    def update_tle_plot(self):
        """Update TLE deviation plot - delegeret til Func_CalculateTLE"""
        from Func_CalculateTLE import update_tle_plot
        update_tle_plot(self)
    
    def double_R(self, times, meas, positions, satid=99999):
        """Double-R IOD metode - delegeret til Func_CalculateTLE"""
        from Func_CalculateTLE import double_R
        return double_R(self, times, meas, positions, satid)
    
    def multilaplace(self, times, meas, positions, satid=99999):
        """Multi-Laplace IOD metode - delegeret til Func_CalculateTLE"""
        from Func_CalculateTLE import multilaplace
        return multilaplace(self, times, meas, positions, satid)
    
    def laplace(self, times, meas, positions, satid=99999):
        """Laplace IOD metode - delegeret til Func_CalculateTLE"""
        from Func_CalculateTLE import laplace
        return laplace(self, times, meas, positions, satid)
    
    def gauss(self, times, meas, positions, satid=99999):
        """Gauss IOD metode - delegeret til Func_CalculateTLE"""
        from Func_CalculateTLE import gauss
        return gauss(self, times, meas, positions, satid)
    
    def circular(self, times, meas, positions, satid=99999):
        """Circular orbit IOD metode - delegeret til Func_CalculateTLE"""
        from Func_CalculateTLE import circular
        return circular(self, times, meas, positions, satid)
    
    def gooding(self, times, meas, positions, satid=99999):
        """Gooding IOD metode - delegeret til Func_CalculateTLE"""
        from Func_CalculateTLE import gooding
        return gooding(self, times, meas, positions, satid)

    def parse_compact_tle_notation(self, s):
        """Parse kompakt TLE notation - delegeret til Func_CalculateTLE"""
        from Func_CalculateTLE import parse_compact_tle_notation
        return parse_compact_tle_notation(self, s)

    def _compact_tle_notation(self, value):
        """Konverter float til TLE kompakt notation - delegeret til Func_CalculateTLE"""
        from Func_CalculateTLE import _compact_tle_notation
        return _compact_tle_notation(self, value)

    def format_first_derivative(self, value):
        """Formatter mean motion dot til TLE - delegeret til Func_CalculateTLE"""
        from Func_CalculateTLE import format_first_derivative
        return format_first_derivative(self, value)

    def format_tle(self, ta0, ele0, params, a):
        """Konverter orbdtools TLE data til standard TLE format - delegeret til Func_CalculateTLE"""
        from Func_CalculateTLE import format_tle
        return format_tle(self, ta0, ele0, params, a)
    
    def calculate_tle_checksum(self, line):
        """Beregn TLE checksum - delegeret til Func_CalculateTLE"""
        from Func_CalculateTLE import calculate_tle_checksum
        return calculate_tle_checksum(self, line)
    
    def beregn_TLE_fra_observationer(self, Sat_RA, Sat_DEC, X_obs, Y_obs, Z_obs, DATE_OBS, NoradID, metode, index_list=None):
        """Hovedfunktion til at beregne TLE fra observationer - delegeret til Func_CalculateTLE"""
        from Func_CalculateTLE import beregn_TLE_fra_observationer
        return beregn_TLE_fra_observationer(self, Sat_RA, Sat_DEC, X_obs, Y_obs, Z_obs, DATE_OBS, NoradID, metode, index_list)
    
    def calculate_tle_from_observations(self):
        """Beregner TLE baseret på valgte parametre - delegeret til Func_CalculateTLE"""
        from Func_CalculateTLE import calculate_tle_from_observations
        calculate_tle_from_observations(self)
    
    def show_tle_3d_plot(self):
        """Show 3D plot of calculated TLE - delegeret til Func_CalculateTLE"""
        from Func_CalculateTLE import show_tle_3d_plot
        show_tle_3d_plot(self)
    
    def save_tle_results(self):
        """Save TLE results to CSV file - delegeret til Func_CalculateTLE"""
        from Func_CalculateTLE import save_tle_results
        save_tle_results(self)
    
    def load_tle_csv_data(self, directory):
        """Load CSV file from folder for TLE calculation - delegeret til Func_CalculateTLE"""
        from Func_CalculateTLE import load_tle_csv_data
        load_tle_csv_data(self, directory)

if __name__ == "__main__":
    root = tk.Tk()
    app = TkinterDemo(root)
    root.mainloop()
    
