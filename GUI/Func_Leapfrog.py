"""
Func_Leapfrog.py - LeapFrog Observation Tab Functions
Contains UI initialization for LeapFrog observation features
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
import time
import pandas as pd
import numpy as np
import os

# Check for optional dependencies
try:
    import plotly.graph_objects as go
    import plotly.offline as pyo
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

try:
    from pwi4_client import PWI4Telescope
    PWI4_AVAILABLE = True
except ImportError:
    PWI4_AVAILABLE = False


def create_leapfrog_tab(self, notebook):
    """Tab til LeapFrog observation"""
    leapfrog_frame = ttk.Frame(notebook)
    notebook.add(leapfrog_frame, text="LeapFrog Observation")
    
    # Opret en canvas og scrollbar for at gøre indholdet scrollbart
    canvas = tk.Canvas(leapfrog_frame)
    v_scrollbar = ttk.Scrollbar(leapfrog_frame, orient="vertical", command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)
    
    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=v_scrollbar.set)
    
    # Tilføj mousewheel scrolling
    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    canvas.bind("<MouseWheel>", _on_mousewheel)
    
    # Pack canvas og scrollbar
    canvas.pack(side="left", fill="both", expand=True)
    v_scrollbar.pack(side="right", fill="y")
    
    # Nu brug scrollable_frame som container i stedet for leapfrog_frame
    main_container = ttk.Frame(scrollable_frame)
    main_container.pack(fill='both', expand=True, padx=10, pady=10)
    
    # Opret to kolonner: venstre for widgets, højre for log
    left_frame = ttk.Frame(main_container)
    left_frame.pack(side='left', fill='both', expand=True, padx=(0, 5))
    
    right_frame = ttk.Frame(main_container) 
    right_frame.pack(side='right', fill='both', expand=False, padx=(5, 0))
    
    # Satelit valg sektion (venstre side)
    selection_frame = ttk.LabelFrame(left_frame, text="Satelit Valg")
    selection_frame.pack(fill='x', pady=(0, 10))
    
    ttk.Label(selection_frame, text="Vælg en satellit fra listen i 'Hent Satelitlister' fanen").pack(pady=5)
    
    button_frame = ttk.Frame(selection_frame)
    button_frame.pack(pady=5)
    
    ttk.Button(button_frame, text="Hent Valgt Satelitt", 
              command=self.get_selected_satellite).pack(side='left', padx=5)
    
    # Satelit info display
    info_frame = ttk.LabelFrame(selection_frame, text="Valgt Satelit Info")
    info_frame.pack(fill='x', pady=5)
    
    self.sat_info_text = tk.Text(info_frame, height=3, wrap='word')
    self.sat_info_text.pack(fill='x', padx=5, pady=5)
    
    # Plot sektion (venstre side)
    if PLOTLY_AVAILABLE:
        plot_frame = ttk.LabelFrame(left_frame, text="3D Plot")
        plot_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Button(plot_frame, text="Vis 3D Plot", 
                  command=self.show_leapfrog_plot).pack(pady=5)
    
    # Observation control sektion (venstre side)
    control_frame = ttk.LabelFrame(left_frame, text="Observation Control")
    control_frame.pack(fill='x', pady=(0, 10))
    
    # Parameter frame
    params_frame = ttk.LabelFrame(control_frame, text="Observation Parametre")
    params_frame.pack(fill='x', padx=5, pady=5)
    
    # PWI4 URL
    ttk.Label(params_frame, text="PWI4 URL:").grid(row=0, column=0, sticky='w', padx=5, pady=5)
    self.leapfrog_pw4_url_entry = ttk.Entry(params_frame, width=30)
    self.leapfrog_pw4_url_entry.grid(row=0, column=1, columnspan=3, padx=5, pady=5)
    self.leapfrog_pw4_url_entry.insert(0, "http://localhost:8220")
    
    # Timing parametre (binning styres nu fra kameraindstillinger)
    ttk.Label(params_frame, text="Exposure time (s):").grid(row=1, column=0, sticky='w', padx=5, pady=5)
    self.leapfrog_exposure_time_entry = ttk.Entry(params_frame, width=10)
    self.leapfrog_exposure_time_entry.grid(row=1, column=1, padx=5, pady=5)
    self.leapfrog_exposure_time_entry.insert(0, "1.0")
    
    ttk.Label(params_frame, text="Tid mellem obs (s):").grid(row=1, column=2, sticky='w', padx=5, pady=5)
    self.leapfrog_interval_entry = ttk.Entry(params_frame, width=10)
    self.leapfrog_interval_entry.grid(row=1, column=3, padx=5, pady=5)
    self.leapfrog_interval_entry.insert(0, "10.0")
    
    # PWI4 status
    if PWI4_AVAILABLE:
        pwi4_status = "PWI4 bibliotek tilgængeligt"
        status_color = 'green'
    else:
        pwi4_status = "ADVARSEL: PWI4 bibliotek ikke tilgængeligt"
        status_color = 'orange'
    
    status_label = ttk.Label(control_frame, text=f"Status: {pwi4_status}")
    status_label.pack(pady=2)
    if not PWI4_AVAILABLE:
        status_label.config(foreground='orange')
    
    # Control knapper
    control_button_frame = ttk.Frame(control_frame)
    control_button_frame.pack(pady=5)
    
    self.start_obs_btn = ttk.Button(control_button_frame, text="Start LeapFrog Observation", 
                                   command=self.start_leapfrog_observation)
    self.start_obs_btn.pack(side='left', padx=5)
    
    self.stop_obs_btn = ttk.Button(control_button_frame, text="Stop Observation", 
                                  command=self.stop_leapfrog_observation, state='disabled')
    self.stop_obs_btn.pack(side='left', padx=5)
    
    # Log sektion (højre side)
    log_frame = ttk.LabelFrame(right_frame, text="Observation Log")
    log_frame.pack(fill='both', expand=True)
    
    # Sæt en passende bredde på log området
    right_frame.configure(width=420)
    right_frame.pack_propagate(False)
    
    # Log text widget med scrollbar
    log_container = ttk.Frame(log_frame)
    log_container.pack(fill='both', expand=True, padx=5, pady=5)
    
    self.log_text = tk.Text(log_container, width=52, wrap='word')
    log_scrollbar = ttk.Scrollbar(log_container, orient='vertical', command=self.log_text.yview)
    self.log_text.configure(yscrollcommand=log_scrollbar.set)
    
    log_scrollbar.pack(side='right', fill='y')
    self.log_text.pack(side='left', fill='both', expand=True)
    
    # Clear log button
    ttk.Button(log_frame, text="Ryd Log", 
              command=lambda: self.log_text.delete(1.0, tk.END)).pack(pady=2)
    
    # Billedvisningssektion under loggen (højre side)
    image_frame = ttk.LabelFrame(right_frame, text="Seneste Billede")
    image_frame.pack(fill='x', pady=5)
    
    # Label til at vise billede
    self.leapfrog_image_label = ttk.Label(image_frame, text="Venter på billede...")
    self.leapfrog_image_label.pack(pady=10)

def log_message(self, message):
    """Tilføj besked til log"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
    self.log_text.see(tk.END)
    self.root.update()

def display_leapfrog_image(self, image_data):
    """Vis downscaled version af billedet under loggen"""
    try:
        from PIL import Image, ImageTk
        from scipy.ndimage import zoom
        
        # Downscale til visning
        target_height, target_width = 200, 300
        original_height, original_width = image_data.shape
        scale_y = target_height / original_height
        scale_x = target_width / original_width
        
        downscaled_image = zoom(image_data, (scale_y, scale_x), order=1)
        downscaled_image = np.clip(downscaled_image, None, 800)
        
        # Normaliser til 0-255 for visning
        normalized = ((downscaled_image - downscaled_image.min()) / (downscaled_image.max() - downscaled_image.min() + 1e-8) * 255).astype(np.uint8)
        
        # Konverter til PIL Image
        pil_image = Image.fromarray(normalized, mode='L')
        
        # Konverter til PhotoImage for Tkinter visning
        photo_image = ImageTk.PhotoImage(pil_image)
        
        # Opdater label
        self.leapfrog_image_label.config(image=photo_image, text="")
        self.leapfrog_image_label.image = photo_image  # Bevar reference
        self.root.update()
        
    except Exception as e:
        log_message(self, f"Fejl ved visning af billede: {str(e)}")

def get_selected_satellite(self):
    """Henter den valgte satellit fra satellitlisten"""
    try:
        selection = self.satellite_tree.selection()
        if not selection:
            messagebox.showwarning("Ingen valg", "Vælg venligst en satelitt fra listen")
            return
        
        item = selection[0]
        values = self.satellite_tree.item(item, 'values')
        
        # Udtræk satellit information
        self.selected_satellite = {
            'SatName': values[0],
            'NORAD': values[1],
            'StartTime': values[2],
            'EndTime': values[4],
            'TLE1': get_full_tle_from_selection(self, item)[0],
            'TLE2': get_full_tle_from_selection(self, item)[1]
        }
        
        # Vis satellit info
        info_text = f"Satellit: {self.selected_satellite['SatName']}\n"
        info_text += f"NORAD ID: {self.selected_satellite['NORAD']}\n"
        info_text += f"Observation: {self.selected_satellite['StartTime']} - {self.selected_satellite['EndTime']}"
        
        self.sat_info_text.delete(1.0, tk.END)
        self.sat_info_text.insert(1.0, info_text)
        
        log_message(self, f"Valgt satellit: {self.selected_satellite['SatName']}")
        
    except Exception as e:
        messagebox.showerror("Fejl", f"Kunne ikke hente satellit information: {str(e)}")

def get_full_tle_from_selection(self, item):
    """Henter fulde TLE linjer fra den valgte satellit"""
    try:
        # Find den fulde TLE fra df_merged baseret på valgte række
        item_values = self.satellite_tree.item(item, 'values')
        sat_name = item_values[0]
        norad_id = item_values[1]
        
        # Find satellitten i df_merged
        mask = (self.df_merged['SatName'] == sat_name) & (self.df_merged['NORAD'].astype(str) == str(norad_id))
        satellite_row = self.df_merged[mask].iloc[0]
        
        return satellite_row['TLE1'], satellite_row['TLE2']
        
    except Exception as e:
        log_message(self, f"Fejl ved hentning af TLE: {str(e)}")
        return None, None

def calculate_leapfrog_data(self):
    """Beregner LeapFrog data baseret på valgt satellit"""
    from Func_fagprojekt import calculate_satellite_data, ra_dec_to_eci
    from datetime import datetime, timedelta
    import pandas as pd
    import numpy as np
    from skyfield.api import Topos, load, EarthSatellite
    from tkinter import messagebox
    
    try:
        if not hasattr(self, 'selected_satellite'):
            messagebox.showwarning("Ingen satellit", "Vælg først en satellit")
            return
        
        log_message(self, "Beregner LeapFrog data...")
        
        # Hent koordinater og UTC offset fra satellit tab
        lat = float(self.lat_entry.get())
        lng = float(self.lng_entry.get())
        ele = float(self.ele_entry.get())
        utc_offset = float(self.utc_offset_entry.get())
        
        # Hent og valider interval mellem observationer
        try:
            interval_between_obs = float(self.leapfrog_interval_entry.get())
            if interval_between_obs <= 0 or interval_between_obs > 300:
                messagebox.showerror("Ugyldig interval", "Interval mellem observationer skal være mellem 0.1 og 300 sekunder")
                return
        except ValueError:
            messagebox.showerror("Ugyldig interval", "Interval skal være et gyldigt tal")
            return
        
        # Parse TLE og tider
        satellite_name = self.selected_satellite['SatName']
        satellite_id = self.selected_satellite['NORAD']
        start_time_str = self.selected_satellite['StartTime']
        end_time_str = self.selected_satellite['EndTime']
        tle_line1 = self.selected_satellite['TLE1']
        tle_line2 = self.selected_satellite['TLE2']
        
        # Beregn tidsintervaller - konverter til UTC for satellit beregninger
        today = datetime.now().date()
        # Start- og sluttider er allerede i lokal tid (med UTC offset), så vi konverterer til UTC
        # Håndter både HH:MM og HH:MM:SS formater
        try:
            start_tid_local = datetime.combine(today, datetime.strptime(start_time_str, "%H:%M:%S").time())
        except ValueError:
            start_tid_local = datetime.combine(today, datetime.strptime(start_time_str, "%H:%M").time())
        
        try:
            slut_tid_local = datetime.combine(today, datetime.strptime(end_time_str, "%H:%M:%S").time())
        except ValueError:
            slut_tid_local = datetime.combine(today, datetime.strptime(end_time_str, "%H:%M").time())
        
        # Konverter til UTC ved at trække UTC offset fra
        start_tid_utc = start_tid_local - timedelta(hours=utc_offset)
        slut_tid_utc = slut_tid_local - timedelta(hours=utc_offset)
        
        # Hent interval mellem observationer fra UI
        interval_between_obs = float(self.leapfrog_interval_entry.get())
        
        # Opret tidsintervaller baseret på brugervalgt interval i UTC
        tidspunkter_utc = [start_tid_utc + timedelta(seconds=i*interval_between_obs) for i in range(int((slut_tid_utc-start_tid_utc).total_seconds()/interval_between_obs)+1)]
        
        # Opret DataFrame med UTC tider for satellit beregninger
        self.df_leapfrog = pd.DataFrame({"DATE-OBS": [dt.strftime("%Y-%m-%d %H:%M:%S.%f") for dt in tidspunkter_utc]})
        self.df_leapfrog["LAT--OBS"] = lat
        self.df_leapfrog["LONG-OBS"] = lng
        self.df_leapfrog["ELEV-OBS"] = ele
        
        # Beregn satellit positioner (bruger UTC tider)
        afstand, vinkel, sat_pos, earth_pos, obs_points = calculate_satellite_data(self.df_leapfrog, tle_line1, tle_line2)
        sat_positions = np.array(sat_pos)
        obs_points = np.array(obs_points)
        
        # Beregn retning til satellit
        x_list = sat_positions[:,0] - obs_points[:,0]
        y_list = sat_positions[:,1] - obs_points[:,1]
        z_list = sat_positions[:,2] - obs_points[:,2]
        
        ra_tle, dec_tle = np.vectorize(xyz_to_radec)(x_list, y_list, z_list)
        self.df_leapfrog['Sat_RA'] = ra_tle
        self.df_leapfrog['Sat_DEC'] = dec_tle
        
        # Konverter RA til timer format
        self.df_leapfrog['Sat_RA_Hr'] = ra_deg_to_hms(ra_tle)
        
        # Beregn Alt/Az (bruger UTC tider)
        alt_list, az_list = tle_to_altaz(self, tle_line1, tle_line2, lat, lng, ele, tidspunkter_utc)
        self.df_leapfrog['Sat_Alt'] = alt_list
        self.df_leapfrog['Sat_Az'] = az_list
        
        # Konverter DATE-OBS tilbage til lokal tid for visning
        self.df_leapfrog['DATE-OBS'] = [(datetime.strptime(dt, "%Y-%m-%d %H:%M:%S.%f") + timedelta(hours=utc_offset)).strftime("%Y-%m-%d %H:%M:%S.%f") for dt in self.df_leapfrog['DATE-OBS']]
        
        # Beregn XYZ for plotting
        xyz = [ra_dec_to_eci(ra, dec, r) + obs for ra, dec, r, obs in zip(self.df_leapfrog['Sat_RA'], self.df_leapfrog['Sat_DEC'], afstand, obs_points)]
        self.df_leapfrog['xyz'] = xyz
        
        # Gem data til plotting
        self.sat_positions = sat_positions
        self.obs_points = obs_points
        self.afstand = afstand
        self.utc_offset = utc_offset  # Gem til senere brug
        
        log_message(self, f"LeapFrog data beregnet for {len(self.df_leapfrog)} punkter (interval: {interval_between_obs}s, UTC offset: {utc_offset} timer)")
        
    except Exception as e:
        log_message(self, f"Fejl ved beregning: {str(e)}")
        messagebox.showerror("Fejl", f"Kunne ikke beregne LeapFrog data: {str(e)}")

def xyz_to_radec(x, y, z):
    """Konverter XYZ til RA/DEC"""
    import numpy as np
    r = np.array([x, y, z], dtype=float)
    norm = np.linalg.norm(r)
    if norm == 0:
        raise ValueError("Vector has zero length")
    ra_rad = np.arctan2(r[1], r[0]) % (2*np.pi)
    dec_rad = np.arcsin(r[2]/norm)
    return np.degrees(ra_rad), np.degrees(dec_rad)

def ra_deg_to_hms(ra_deg_array):
    """Konverter RA grader til HH:MM:SS format"""
    import numpy as np
    RA_hours = ra_deg_array / 15
    hours = np.floor(RA_hours).astype(int)
    minutes = np.floor((RA_hours - hours)*60).astype(int)
    seconds = ((RA_hours - hours)*60 - minutes)*60
    return [f"{h:02d}:{m:02d}:{s:06.3f}" for h, m, s in zip(hours, minutes, seconds)]

def tle_to_altaz(self, tle1, tle2, observer_lat, observer_lon, observer_ele, datetime_list, name="SAT"):
    """Beregn Alt/Az fra TLE"""
    from skyfield.api import Topos, load, EarthSatellite
    ts = load.timescale()
    satellite = EarthSatellite(tle1, tle2, name)
    observer = Topos(latitude_degrees=observer_lat, longitude_degrees=observer_lon, elevation_m=observer_ele)
    alt_list, az_list = [], []
    for dt in datetime_list:
        t = ts.utc(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second + dt.microsecond/1e6)
        topocentric = (satellite - observer).at(t)
        alt, az, _ = topocentric.altaz()
        alt_list.append(alt.degrees)
        az_list.append(az.degrees)
    return alt_list, az_list

def update_leapfrog_table(self):
    """Opdater LeapFrog data tabel"""
    # Ryd tidligere data
    for item in self.leapfrog_tree.get_children():
        self.leapfrog_tree.delete(item)
    
    if self.df_leapfrog is not None:
        for _, row in self.df_leapfrog.iterrows():
            values = (
                row['DATE-OBS'],
                f"{row['Sat_DEC']:.4f}°",
                row['Sat_RA_Hr'],
                f"{row['Sat_Alt']:.2f}°",
                f"{row['Sat_Az']:.2f}°"
            )
            self.leapfrog_tree.insert('', 'end', values=values)

def show_leapfrog_plot(self):
    """Vis 3D plot af LeapFrog data"""
    import plotly.graph_objects as go
    import plotly.offline as pyo
    import numpy as np
    from tkinter import messagebox
    
    if not PLOTLY_AVAILABLE:
        messagebox.showerror("Fejl", "Plotly er ikke installeret")
        return
    
    if self.df_leapfrog is None:
        messagebox.showwarning("Ingen data", "Beregn først LeapFrog data")
        return
    
    try:
        # Jordens radius i km
        earth_radius = 6371
        
        # Opret en kugle for Jorden
        u, v = np.mgrid[0:2*np.pi:100j, 0:np.pi:50j]
        x = earth_radius * np.cos(u) * np.sin(v)
        y = earth_radius * np.sin(u) * np.sin(v)
        z = earth_radius * np.cos(v)
        
        # Opret figuren
        fig = go.Figure()
        
        # Plot satellitens bane
        fig.add_trace(go.Scatter3d(
            x=self.sat_positions[:, 0],
            y=self.sat_positions[:, 1],
            z=self.sat_positions[:, 2],
            mode='lines',
            name='Satellitbane',
            line=dict(color='blue', width=2)
        ))
        
        # Plot observationspunkter
        fig.add_trace(go.Scatter3d(
            x=self.obs_points[:, 0],
            y=self.obs_points[:, 1],
            z=self.obs_points[:, 2],
            mode='markers',
            name='Observationspunkt',
            marker=dict(size=1, color='red')
        ))
        
        # Plot Jorden som en kugle
        fig.add_trace(go.Surface(
            x=x, y=y, z=z,
            colorscale='Blues',
            opacity=0.5,
            showscale=False,
            name='Jorden'
        ))
        
        # Tilføj punkterne fra teleskop retning
        fig.add_trace(go.Scatter3d(
            x=self.df_leapfrog['xyz'].apply(lambda xyz: xyz[0]),
            y=self.df_leapfrog['xyz'].apply(lambda xyz: xyz[1]),
            z=self.df_leapfrog['xyz'].apply(lambda xyz: xyz[2]),
            mode='markers',
            name='Teleskop retning',
            marker=dict(size=3, color='green', opacity=0.6)
        ))
        
        # Tilføj akseetiketter og titel
        fig.update_layout(
            scene=dict(
                xaxis_title='X (km)',
                yaxis_title='Y (km)',
                zaxis_title='Z (km)',
            ),
            title='LeapFrog Satellitbane og observationspunkt i ECI-koordinatsystemet',
            showlegend=True
        )
        
        # Vis plottet
        pyo.plot(fig, filename='leapfrog_plot.html', auto_open=True)
        
        log_message(self, "3D plot genereret og åbnet i browser")
        
    except Exception as e:
        log_message(self, f"Fejl ved plotting: {str(e)}")
        messagebox.showerror("Fejl", f"Kunne ikke generere plot: {str(e)}")

def start_leapfrog_observation(self):
    """Start LeapFrog observation i separat tråd"""
    import threading
    from tkinter import messagebox
    
    # Tjek at satellit er valgt
    if not hasattr(self, 'selected_satellite') or self.selected_satellite is None:
        messagebox.showwarning("Ingen satellit", "Vælg først en satellit ved at trykke 'Hent Valgt Satelitt'")
        return
    
    # Beregn LeapFrog data først
    try:
        log_message(self, "Beregner LeapFrog data...")
        self.calculate_leapfrog_data()
    except Exception as e:
        messagebox.showerror("Beregningsfejl", f"Kunne ikke beregne LeapFrog data: {str(e)}")
        return
    
    # Tjek at data blev beregnet
    if self.df_leapfrog is None or len(self.df_leapfrog) == 0:
        messagebox.showerror("Ingen data", "LeapFrog data kunne ikke genereres")
        return
    
    if self.leapfrog_observation_running:
        messagebox.showwarning("Observation kører", "En observation kører allerede")
        return
        
    # Tjek kamera tilgængelighed først
    camera = self.get_camera_for_observation()
    if camera is None:
        messagebox.showerror("Kamera ikke tilgængelig", 
                           "Moravian kamera ikke tilsluttet eller ikke tilgængeligt.\n\n"
                           "Tilslut kameraet i kameraindstillinger først.\n"
                           "Sørg for at Moravian SDK er installeret og kameraet er forbundet.")
        return
    
    # Tjek PWI4 tilgængelighed for teleskop
    if not PWI4_AVAILABLE:
        messagebox.showerror("PWI4 bibliotek ikke tilgængelig", 
                           "PWI4 bibliotek ikke installeret.\n\n"
                           "Sørg for at pwi4_client.py er tilgængelig i samme mappe som GUI.py")
        return
    
    # Tjek om observation er startet for sent
    from datetime import datetime
    import pandas as pd
    
    current_time = datetime.now()
    utc_offset = getattr(self, 'utc_offset', 2)
    df_work = self.df_leapfrog.copy()
    
    # DATE-OBS er nu i lokal tid (efter konvertering i calculate_leapfrog_data)
    df_work['DATE-OBS'] = pd.to_datetime(df_work['DATE-OBS'])
    
    # Beregn hvor mange punkter der er brugbare (mindst 30s før observation)
    slew_time_required = 30
    available_points = 0
    for _, row in df_work.iterrows():
        planned_time_local = row['DATE-OBS']
        time_to_observation = (planned_time_local - current_time).total_seconds()
        if time_to_observation >= slew_time_required:
            available_points += 1
    
    if available_points == 0:
        messagebox.showerror("For sent", "Alle observationspunkter er allerede passeret eller ligger for tæt på (mindre end 30s til slew)!")
        return
    
    log_message(self, f"{available_points} af {len(df_work)} observationspunkter er tilgængelige")
    
    # Skift knap tilstande
    self.start_obs_btn.config(state='disabled')
    self.stop_obs_btn.config(state='normal')
    
    # Start observation i separat tråd
    self.stop_observation = False
    threading.Thread(target=run_leapfrog_observation, args=(self,), daemon=True).start()

def stop_leapfrog_observation(self):
    """Stop LeapFrog observation"""
    self.stop_observation = True
    log_message(self, "Stop signal sendt...")

def wait_until(self, target_time):
    """Vent til det ønskede tidspunkt - springer over hvis tiden allerede er passeret"""
    from datetime import datetime
    import time
    
    current_time = datetime.now()
    if target_time <= current_time:
        # Tiden er allerede passeret, venter ikke
        return
    
    while datetime.now() < target_time and not self.stop_observation:
        time.sleep(0.05)

def hms_to_hours(self, hms_str):
    """Konverter RA HH:MM:SS.sss til decimal timer."""
    h, m, s = map(float, hms_str.split(":"))
    return h + m/60 + s/3600

def run_leapfrog_observation(self):
    """Kør LeapFrog observation"""
    try:
        self.leapfrog_observation_running = True
        log_message(self, "Starter LeapFrog observation...")
        
        # Kør rigtig observation med PWI4
        if PWI4_AVAILABLE:
            _execute_leapfrog_observation(self)
        else:
            log_message(self, "FEJL: PWI4 bibliotek ikke tilgængeligt")
            log_message(self, "Installer pwi4_client.py i samme mappe som GUI.py")
            raise Exception("PWI4 bibliotek ikke installeret - kan ikke køre observation")
            
    except Exception as e:
        log_message(self, f"Fejl under observation: {str(e)}")
    finally:
        self.leapfrog_observation_running = False
        self.start_obs_btn.config(state='normal')
        self.stop_obs_btn.config(state='disabled')
        log_message(self, "Observation afsluttet")

def _execute_leapfrog_observation(self):
    """Kør rigtig observation med PWI4"""
    from astropy.io import fits
    import numpy as np
    import os
    import pandas as pd
    from datetime import datetime, timedelta
    import time
    from tkinter import messagebox
    
    try:
        # Hent parametre (binning fra kameraindstillinger)
        x_binning = self.camera_binning_x.get()
        y_binning = self.camera_binning_y.get()
        pw4_url = self.leapfrog_pw4_url_entry.get().strip()
        exposure_time = float(self.leapfrog_exposure_time_entry.get())
        interval_between_obs = float(self.leapfrog_interval_entry.get())
        
        # Fast kamera start før planlagt tid (0.8 sekunder)
        camera_start_before = 0.8
        
        # Valider parametre
        if x_binning < 1 or y_binning < 1 or x_binning > 16 or y_binning > 16:
            messagebox.showerror("Ugyldig binning", "Binning skal være mellem 1 og 16")
            return
        
        if exposure_time <= 0 or exposure_time > 60:
            messagebox.showerror("Ugyldig exposure time", "Exposure time skal være mellem 0.1 og 60 sekunder")
            return
            
        if interval_between_obs < 0 or interval_between_obs > 300:
            messagebox.showerror("Ugyldig interval", "Interval mellem observationer skal være mellem 0 og 300 sekunder")
            return
        
        # Opret mappe struktur
        sat_name = self.selected_satellite['SatName']
        norad_id = self.selected_satellite['NORAD']
        session_date = datetime.now().strftime("%m_%d")
        
        # Rens satellit navn for filsystem
        safe_sat_name = "".join(c for c in sat_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_sat_name = safe_sat_name.replace(' ', '_')
        
        session_dir = os.path.join(os.getcwd(), f"LeapFrog_{safe_sat_name}_{norad_id}_{session_date}")
        os.makedirs(session_dir, exist_ok=True)
        
        log_message(self, f"Satellit: {sat_name}")
        log_message(self, f"Binning: {x_binning}x{y_binning}")
        log_message(self, f"Session mappe: {session_dir}")
        
        # Tilslut teleskop og kamera
        log_message(self, "Tilslutter teleskop og kamera...")
        
        # PWI4 teleskop forbindelse
        if not PWI4_AVAILABLE:
            raise Exception("PWI4 bibliotek ikke tilgængeligt for teleskop kontrol")
        
        telescope = PWI4Telescope(host=pw4_url.replace("http://", "").split(":")[0], 
                                 port=int(pw4_url.split(":")[-1]) if ":" in pw4_url else 8220)
        
        if not telescope.test_connection():
            raise Exception(f"Kan ikke forbinde til PWI4 på {pw4_url}")
        
        telescope.connect()
        log_message(self, f"PWI4 teleskop tilsluttet succesfuldt")
        
        # Kamera forbindelse (nu via Moravian)
        camera = self.get_camera_for_observation()
        if camera is None:
            raise Exception("Moravian kamera ikke tilsluttet eller ikke tilgængeligt.\n\nTilslut kameraet i kameraindstillinger først.")
        
        # Sæt kamera parametre med binning
        camera.set_binning(x_binning, y_binning)
        
        # Professionel kamera konfiguration for Moravian kameraer
        info = camera.get_camera_info()
        camera_desc = info.get('description', 'Moravian Camera')
        ccd_width = info.get('width', 0)
        ccd_height = info.get('height', 0)
        
        log_message(self, f"Konfigurerer kamera: {camera_desc}")
        log_message(self, f"CCD størrelse: {ccd_width} x {ccd_height} pixels")
        log_message(self, f"Binning sat til: {x_binning}x{y_binning}")
        
        # Beregn korrekt billedstørrelse baseret på binning
        image_width = ccd_width // x_binning
        image_height = ccd_height // y_binning
        
        log_message(self, f"Beregnet billedstørrelse: {image_width}x{image_height} pixels")
        
        # Verificer binning
        max_binning_x = info.get('max_binning_x', 8)
        max_binning_y = info.get('max_binning_y', 8)
        
        if x_binning > max_binning_x or y_binning > max_binning_y:
            raise Exception(f"Binning {x_binning}x{y_binning} overstiger kamera max: {max_binning_x}x{max_binning_y}")
        
        log_message(self, f"Kamera konfiguration bekræftet:")
        log_message(self, f"  Binning: {camera.bin_x}x{camera.bin_y}")
        log_message(self, f"  Billedstørrelse: {image_width}x{image_height} pixels")
        
        # Temperatur info
        current_temp = info.get('temperature', None)
        if current_temp is not None:
            log_message(self, f"  Kamera temperatur: {current_temp:.1f}°C")
        
        # Konverter DATE-OBS til datetime
        df_work = self.df_leapfrog.copy()
        df_work['DATE-OBS'] = pd.to_datetime(df_work['DATE-OBS'])
        
        # Tjek om observation er startet for sent
        current_time = datetime.now()
        utc_offset = getattr(self, 'utc_offset', 2)
        slew_time_required = 30  # Sekunder nødvendigt for at slew til første punkt
        
        # Find det første punkt der er mindst 30 sekunder i fremtiden (til slew tid)
        start_index = 0
        for i, row in df_work.iterrows():
            planned_time_local = row['DATE-OBS']  # Dette er allerede i lokal tid
            time_to_observation = (planned_time_local - current_time).total_seconds()
            if time_to_observation >= slew_time_required:
                start_index = i
                break
        else:
            # Alle punkter er passeret eller ligger for tæt på
            log_message(self, "ADVARSEL: Alle observationspunkter er passeret eller ligger for tæt på (mindre end 30s til slew)! Observationen springer over.")
            return
        
        if start_index > 0:
            log_message(self, f"Springer over de første {start_index} punkter (allerede passeret)")
        
        # Gennemløb af alle punkter fra start_index
        for i, row in df_work.iloc[start_index:].iterrows():
            if self.stop_observation:
                log_message(self, "Observation stoppet af bruger")
                break
            
            ra_str = row['Sat_RA_Hr']
            dec = float(row['Sat_DEC'])
            planned_time = row['DATE-OBS']  # Dette er i lokal tid
            
            # Beregn tider i lokal tid
            camera_start_time = planned_time - timedelta(seconds=camera_start_before)
            camera_stop_time = planned_time + timedelta(seconds=exposure_time)
            
            # Konverter RA til decimal timer
            ra_hours = hms_to_hours(self, ra_str)
            
            log_message(self, f"Punkt {i+1}/{len(df_work)}: Planlægger slew til RA: {ra_str} ({ra_hours:.6f} timer), DEC: {dec:.6f} grader")
            
            # Slew til position ved hjælp af PWI4
            telescope.slew_to_coordinates(ra_hours, dec, coord_type="j2000")
            
            # Vent på slew færdig
            while telescope.is_slewing() and not self.stop_observation:
                time.sleep(0.1)
            
            if self.stop_observation:
                break
            
            log_message(self, f"Slew færdig. Venter til kamera starttid: {camera_start_time}")
            
            # Vent og start kamera
            wait_until(self, camera_start_time)
            if self.stop_observation:
                break
            
            log_message(self, "Starter eksponering")
            
            # Tag et billede ved det planlagte tidspunkt
            try:
                # *** OPTIMERET LEAPFROG EKSPONERING ***
                leapfrog_result = self.optimized_camera_exposure_with_timing(
                    camera=camera, 
                    exposure_time=exposure_time, 
                    pw4_client=telescope,
                    pw4_url=pw4_url,
                    obstype='LeapFrog'
                )
                
                if leapfrog_result is None:  # Afbrudt af bruger
                    if self.stop_observation:
                        log_message(self, "Observation stoppet af bruger")
                        break
                else:
                    # Udpak resultater fra optimeret timing
                    image_data = leapfrog_result['image_data']
                    exposure_start_time = leapfrog_result['exposure_start_time']
                    exposure_end_time = leapfrog_result['exposure_end_time']
                    pw4_status = leapfrog_result['pw4_status']
                    
                    log_message(self, f"LeapFrog timing nøjagtighed: {leapfrog_result['timing_accuracy']:.1f}ms")
                    
                    # Vis billede under loggen
                    display_leapfrog_image(self, image_data)
                    
                    # Hent filter information
                    filter_name = self.get_current_filter_name()
                    
                    # Opret FITS header med standard metode
                    header = self.create_standard_fits_header(
                        obstype='LeapFrog',
                        sat_name=sat_name,
                        exposure_start_time=exposure_start_time,
                        exposure_end_time=exposure_end_time,
                        exposure_time=exposure_time,
                        tle1=self.selected_satellite['TLE1'],
                        tle2=self.selected_satellite['TLE2'],
                        norad_id=self.selected_satellite['NORAD'],
                        camera=camera,
                        pw4_status=pw4_status,
                        ra_hours=ra_hours,
                        dec_degrees=dec,
                        alt_degrees=row.get('Sat_Alt', 0),
                        az_degrees=row.get('Sat_Az', 0),
                        image_width=image_data.shape[1],
                        image_height=image_data.shape[0],
                        filter_name=filter_name
                    )
                    
                    # Gem FITS fil med komplet header
                    timestamp = datetime.now().strftime("%H%M%S")
                    filename = f"LeapFrog_{safe_sat_name}_{norad_id}_{timestamp}_001.fits"
                    filepath = os.path.join(session_dir, filename)
                    
                    # Konverter til uint16 for FITS
                    image_data_uint16 = image_data.astype(np.uint16)
                    
                    hdu = fits.PrimaryHDU(data=image_data_uint16, header=header)
                    hdu.writeto(filepath, overwrite=True)
                    
                    log_message(self, f"Billede gemt: {filename}")
                    
            except Exception as e:
                log_message(self, f"Fejl ved tag af billede: {str(e)}")
        
        log_message(self, "LeapFrog observation færdig!")
        
    except Exception as e:
        log_message(self, f"Observation fejl: {str(e)}")
    finally:
        try:
            if 'telescope' in locals():
                telescope.park()
                log_message(self, "PWI4 teleskop afbrudt")
        except Exception as e:
            log_message(self, f"Fejl ved afbrydelse af teleskop: {str(e)}")
        
        log_message(self, "LeapFrog observation afsluttet")
