"""
Func_BilledeAnalyse.py - Image Analysis Tab Functions
Contains UI initialization for image analysis features and analysis methods
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import subprocess
import threading
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from astropy.io import fits
import cv2
from scipy.ndimage import label, find_objects
from scipy.ndimage import zoom

# Check for optional dependencies
try:
    from skimage import io, filters, measure
    SKIMAGE_AVAILABLE = True
except ImportError:
    SKIMAGE_AVAILABLE = False

try:
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    plt = None


def create_image_analysis_tab(self, notebook):
    """Tab til Billede Analyse af LeapFrog og Tracking observationer"""
    analysis_frame = ttk.Frame(notebook)
    notebook.add(analysis_frame, text="Billede Analyse")
    
    # Opret en canvas og scrollbar for at gøre indholdet scrollbart
    canvas = tk.Canvas(analysis_frame)
    v_scrollbar = ttk.Scrollbar(analysis_frame, orient="vertical", command=canvas.yview)
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
    
    # Nu brug scrollable_frame som container
    main_container = ttk.Frame(scrollable_frame)
    main_container.pack(fill='both', expand=True, padx=10, pady=10)
    
    # Opret to kolonner: venstre for widgets, højre for log
    left_frame = ttk.Frame(main_container)
    left_frame.pack(side='left', fill='both', expand=True, padx=(0, 5))
    
    right_frame = ttk.Frame(main_container) 
    right_frame.pack(side='right', fill='both', expand=False, padx=(5, 0))
    
    # Input sektion (venstre side)
    input_frame = ttk.LabelFrame(left_frame, text="Analyse Indstillinger")
    input_frame.pack(fill='x', pady=(0, 10))
    
    # Mappe valg
    ttk.Label(input_frame, text="Billede mappe:").grid(row=0, column=0, sticky='w', padx=5, pady=5)
    self.analysis_dir_entry = ttk.Entry(input_frame, width=50)
    self.analysis_dir_entry.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
    ttk.Button(input_frame, text="Vælg Mappe", 
              command=self.select_analysis_directory).grid(row=0, column=2, padx=5, pady=5)
    
    # ASTAP sti
    ttk.Label(input_frame, text="ASTAP sti:").grid(row=1, column=0, sticky='w', padx=5, pady=5)
    self.astap_path_entry = ttk.Entry(input_frame, width=50)
    self.astap_path_entry.grid(row=1, column=1, padx=5, pady=5, sticky='ew')
    self.astap_path_entry.insert(0, r"C:\Program Files\astap\astap.exe")
    ttk.Button(input_frame, text="Vælg Fil", 
              command=self.select_astap_path).grid(row=1, column=2, padx=5, pady=5)
    
    # Pixelscale indstilling
    ttk.Label(input_frame, text="Pixelscale (grader/pixel, 1x1 binning):").grid(row=2, column=0, sticky='w', padx=5, pady=5)
    self.pixelscale_entry = ttk.Entry(input_frame, width=20)
    self.pixelscale_entry.grid(row=2, column=1, padx=5, pady=5, sticky='w')
    self.pixelscale_entry.insert(0, "6.2399e-05")  # 0.22463761903207005/3600
    
    # Radius af Pixelsum (Tracking)
    ttk.Label(input_frame, text="Radius af Pixelsum (Tracking):").grid(row=3, column=0, sticky='w', padx=5, pady=5)
    self.tracking_pixelsum_radius_entry = ttk.Spinbox(input_frame, from_=10, to=200, increment=5,
                                                     textvariable=self.tracking_pixelsum_radius, width=10)
    self.tracking_pixelsum_radius_entry.grid(row=3, column=1, padx=5, pady=5, sticky='w')
    ttk.Label(input_frame, text="pixels").grid(row=3, column=2, sticky='w', padx=5, pady=5)
    
    # Output indstillinger
    output_frame = ttk.LabelFrame(input_frame, text="Output Indstillinger")
    output_frame.grid(row=4, column=0, columnspan=3, sticky='ew', padx=5, pady=5)
    
    self.save_plots_var = tk.BooleanVar(value=True)  # Standard til True da vi altid vil vise plots i GUI
    ttk.Checkbutton(output_frame, text="Gem plots som billeder og vis i GUI", 
                   variable=self.save_plots_var).grid(row=0, column=0, sticky='w', padx=5, pady=2)
    
    # Gør kolonne 1 stretchable
    input_frame.grid_columnconfigure(1, weight=1)
    
    # Kontrol knapper (venstre side)
    control_frame = ttk.LabelFrame(left_frame, text="Analyse Kontrol")
    control_frame.pack(fill='x', pady=(0, 10))
    
    # Status display
    if SKIMAGE_AVAILABLE:
        status_text = "Billede analyse biblioteker tilgængelige"
        status_color = 'black'
    else:
        status_text = "FEJL: Manglende biblioteker (skimage, cv2, scipy)"
        status_color = 'red'
    
    status_label = ttk.Label(control_frame, text=f"Status: {status_text}")
    status_label.pack(pady=2)
    if not SKIMAGE_AVAILABLE:
        status_label.config(foreground='red')
    
    # Kontrol knapper
    button_frame = ttk.Frame(control_frame)
    button_frame.pack(pady=5)
    
    self.start_analysis_btn = ttk.Button(button_frame, text="Start Billede Analyse", 
                                       command=self.start_image_analysis)
    self.start_analysis_btn.pack(side='left', padx=5)
    
    self.stop_analysis_btn = ttk.Button(button_frame, text="Stop Analyse", 
                                      command=self.stop_image_analysis, state='disabled')
    self.stop_analysis_btn.pack(side='left', padx=5)
    
    self.show_plots_btn = ttk.Button(button_frame, text="Vis Plots", 
                                   command=self.show_plots_manual)
    self.show_plots_btn.pack(side='left', padx=5)
    
    # Progress bar
    self.analysis_progress_var = tk.DoubleVar()
    self.analysis_progress_bar = ttk.Progressbar(control_frame, variable=self.analysis_progress_var, maximum=100)
    self.analysis_progress_bar.pack(fill='x', padx=5, pady=5)
    
    # Plot område (venstre side)
    plot_frame = ttk.LabelFrame(left_frame, text="Plot Visning")
    plot_frame.pack(fill='both', expand=True, pady=(0, 10))
    
    # Plot canvas med scrollbar
    self.setup_plot_display(plot_frame)
    
    # Log sektion (højre side)
    log_frame = ttk.LabelFrame(right_frame, text="Analyse Log")
    log_frame.pack(fill='both', expand=True)
    
    # Sæt en passende bredde på log området
    right_frame.configure(width=420)
    right_frame.pack_propagate(False)
    
    # Log text widget med scrollbar
    log_container = ttk.Frame(log_frame)
    log_container.pack(fill='both', expand=True, padx=5, pady=5)
    
    self.analysis_log_text = tk.Text(log_container, width=52, wrap='word')
    analysis_log_scrollbar = ttk.Scrollbar(log_container, orient='vertical', command=self.analysis_log_text.yview)
    self.analysis_log_text.configure(yscrollcommand=analysis_log_scrollbar.set)
    
    analysis_log_scrollbar.pack(side='right', fill='y')
    self.analysis_log_text.pack(side='left', fill='both', expand=True)
    
    # Clear log button
    ttk.Button(log_frame, text="Ryd Log", 
              command=lambda: self.analysis_log_text.delete(1.0, tk.END)).pack(pady=2)


# =====================================================================
# IMAGE ANALYSIS FUNCTIONS - WRAPPED FOR USE WITH CLASS INSTANCE
# =====================================================================

def analysis_log_message(self, message):
    """Tilføj besked til analyse log"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    self.analysis_log_text.insert(tk.END, f"[{timestamp}] {message}\n")
    self.analysis_log_text.see(tk.END)
    self.root.update()

def setup_plot_display(self, parent_frame):
    """Opsæt plot visning område med scrollbar"""
    # Canvas med scrollbar
    from tkinter import Canvas
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
    
    threading.Thread(target=run_image_analysis, args=(self,), daemon=True).start()

def stop_image_analysis(self):
    """Stop billede analyse"""
    self.stop_image_analysis = True
    analysis_log_message(self, "Stop signal sendt...")

def run_image_analysis(self):
    """Kør billede analyse"""
    try:
        self.image_analysis_running = True
        analysis_log_message(self, "Starter billede analyse...")
        
        directory = self.analysis_dir_entry.get().strip()
        astap_path = self.astap_path_entry.get().strip()
        pixelscale = float(self.pixelscale_entry.get())
        save_plots = self.save_plots_var.get()
        
        # Find FITS filer
        fits_files = sorted([f for f in os.listdir(directory) if f.lower().endswith('.fits')])
        analysis_log_message(self, f"Fundet {len(fits_files)} FITS filer")
        
        # Analyser første fil for at bestemme observation type
        first_file = os.path.join(directory, fits_files[0])
        with fits.open(first_file) as hdul:
            header = hdul[0].header
        
        obstype = header.get('OBSTYPE', 'Unknown')
        sat_name = header.get('OBJECT', 'Unknown')
        norad_id = header.get('NORAD_ID', 'Unknown')
        
        analysis_log_message(self, f"Observation type: {obstype}")
        analysis_log_message(self, f"Satellit: {sat_name} (NORAD: {norad_id})")
        
        # Opret output CSV navn
        output_filename = f"data_{sat_name}_{norad_id}.csv"
        output_path = os.path.join(directory, output_filename)
        
        if obstype == 'LeapFrog':
            result_df = analyze_leapfrog_images(self, directory, fits_files, astap_path, pixelscale, save_plots)
        elif obstype == 'Tracking' or obstype == 'stjernehimmel':
            result_df = analyze_tracking_images(self, directory, fits_files, astap_path, pixelscale, save_plots)
        else:
            raise ValueError(f"Ukendt observation type: {obstype}")
        
        # Gem resultater
        result_df.to_csv(output_path, index=False)
        analysis_log_message(self, f"Resultater gemt i: {output_filename}")
        
        if not self.stop_image_analysis:
            analysis_log_message(self, "Billede analyse fuldført!")
            
            # Vis plots efter analysen hvis ønsket
            if save_plots:
                self.root.after(100, lambda: display_plots_in_gui(self, directory))
        
    except Exception as e:
        analysis_log_message(self, f"Fejl under analyse: {str(e)}")
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
                analysis_log_message(self, f"ASTAP fejlede for {filename}: {result.stderr}")
                continue
            else:
                analysis_log_message(self, f"ASTAP gennemført for {filename}")

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
    analysis_log_message(self, "Starter LeapFrog analyse...")
    
    if not SKIMAGE_AVAILABLE:
        raise ImportError("Manglende biblioteker: skimage, cv2, scipy")
    
    from Func_fagprojekt import pixel_to_radec, compute_cd
    
    results = []
    total_files = len(fits_files)
    
    # Kør ASTAP på alle billeder først
    analysis_log_message(self, "Kører ASTAP plate solving på alle billeder...")
    try:
        df_astap = run_astap_on_directory(self, directory, astap_path)
        analysis_log_message(self, f"ASTAP gennemført på {len(df_astap)} billeder")
    except Exception as e:
        analysis_log_message(self, f"ADVARSEL: ASTAP fejlede: {str(e)}")
        df_astap = None
    
    for i, filename in enumerate(fits_files):
        if self.stop_image_analysis:
            break
        
        analysis_log_message(self, f"Behandler LeapFrog fil {i+1}/{total_files}: {filename}")
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
                analysis_log_message(self, f"  Advarsel: Kunne ikke beregne ECI position: {str(e)}")
                file_data['X_obs'] = np.nan
                file_data['Y_obs'] = np.nan
                file_data['Z_obs'] = np.nan
            
            # Find satellitlinje med billedbehandling
            sat_coords = find_satellite_line_leapfrog(self, image_data, header, save_plots, filepath, i)
            file_data.update(sat_coords)
            
            # Opdater observationstid hvis vi har en korrigeret tid
            if sat_coords.get('corrected_obs_time'):
                diff = (pd.to_datetime(sat_coords['corrected_obs_time']) - pd.to_datetime(file_data['DATE-OBS'])).total_seconds()
                analysis_log_message(self, f"ændrede DATE-OBS med {diff} s")
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
                        analysis_log_message(self, f"Satellit RA/DEC: {ra_sat:.6f}°, {dec_sat:.6f}°\n =============================")

                        
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
                        analysis_log_message(self, f"  Fejl ved RA/DEC konvertering: {str(e)}")
            
            results.append(file_data)
            
        except Exception as e:
            analysis_log_message(self, f"Fejl i fil {filename}: {str(e)}")
            # Tilføj tom række for at bevare rækkefølge
            error_data = {'filename': filename, 'error': str(e)}
            results.append(error_data)
    
    self.analysis_progress_var.set(100)
    return pd.DataFrame(results)

def analyze_tracking_images(self, directory, fits_files, astap_path, pixelscale, save_plots):
    """Analyser Tracking billeder"""
    analysis_log_message(self, "Starter Tracking analyse...")
    
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
        analysis_log_message(self, f"Fundet stjernehimmel reference: {starfield_ref}")
        # Analyser reference billede med ASTAP
        ref_offset = analyze_starfield_reference(self, directory, starfield_ref, astap_path)
    else:
        analysis_log_message(self, "Ingen stjernehimmel reference fundet - bruger standard offset")
        ref_offset = {'ra_offset': 0, 'dec_offset': 0, 'rotation_offset': 0}
    
    for i, filename in enumerate(fits_files):
        if self.stop_image_analysis:
            break
        
        analysis_log_message(self, f"Behandler Tracking fil {i+1}/{total_files}: {filename}")
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
                analysis_log_message(self, f"  Advarsel: Kunne ikke beregne ECI position: {str(e)}")
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
                
                analysis_log_message(self, f"CROTA2 fra header: {crota2_header:.3f}°, offset: {ref_offset.get('rotation_offset', 0):.3f}°, bruger: {crota2:.3f}°")
                
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
                analysis_log_message(self, f"  Fejl ved CD matrix beregning: {str(e)}")
            
            # Find satellitposition
            if 'starfield_ref' not in filename.lower():  # Skip reference billede
                sat_coords = find_satellite_position_tracking(
                    self, image_data, header, pixelscale, save_plots, filepath, i)
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
                        analysis_log_message(self, f"Satellit RA/DEC: {ra_sat:.6f}°, {dec_sat:.6f}°\n =============================")
                    except Exception as e:
                        analysis_log_message(self, f"Fejl ved RA/DEC konvertering: {str(e)}")
            
            results.append(file_data)
            
        except Exception as e:
            analysis_log_message(self, f"Fejl i fil {filename}: {str(e)}")
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
            analysis_log_message(self, f"Antal linjer fundet: {len(lines)}")
        else:
            analysis_log_message(self, "❌ Ingen linjer fundet af Hough transform")
        
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
            
            analysis_log_message(self, f"Linje punkter:({x1:.0f},{y1:.0f})({x2:.0f},{y2:.0f})")
            analysis_log_message(self, f"Kant: Punkt1={is_edge1}, Punkt2={is_edge2}")
            
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
                    
                    analysis_log_message(self, f"Satellit bevæger sig mod {'øst' if east_velocity > 0 else 'vest'}")
                    
                    # Beregn skillelinje baseret på rotation
                    theta_rad = np.radians(-rotation_angle)  # MINUS som i original
                    x_c = (width - 1) / 2
                    y_c = (height - 1) / 2
                    nx = np.sin(theta_rad)
                    ny = np.cos(theta_rad)
                    
                    # Intelligent positionsbestemmelse baseret på kantdetektering
                    if is_edge1 or is_edge2:
                        analysis_log_message(self, "Satellit linje rammer billedkant")
                        
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
                                analysis_log_message(self, "Kantpunkt i vest, satellit mod øst → slutpunkt, brug DATE-END")
                                corrected_obs_time = obs_time_slut
                            else:
                                analysis_log_message(self, "Kantpunkt i vest, satellit mod vest → startpunkt, brug DATE-BEG")
                                corrected_obs_time = obs_time_start
                        else:  # Kantpunkt i øst
                            if east_velocity > 0:
                                analysis_log_message(self, "Kantpunkt i øst, satellit mod øst → startpunkt, brug DATE-BEG")
                                corrected_obs_time = obs_time_start
                            else:
                                analysis_log_message(self, "Kantpunkt i øst, satellit mod vest → slutpunkt, brug DATE-END")
                                corrected_obs_time = obs_time_slut
                    else:
                        # Ingen kant - brug midtpunkt og halv exposure tid
                        mid_x = (x1 + x2) // 2
                        mid_y = (y1 + y2) // 2
                        corrected_obs_time = obs_time_start + pd.Timedelta(seconds=delta_obs_time.total_seconds()/2)
                        analysis_log_message(self, f"Ingen kant - midtpunkt, +{delta_obs_time.total_seconds()/2:.2f} sek")
                        
                except Exception as e:
                    analysis_log_message(self, f"Advarsel: Tidskorrektion fejlede: {str(e)}")
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
                plot_leapfrog_result(self, image_data, result, filepath, save_plots, csv_index)
        else:
            analysis_log_message(self, "Ingen satellitlinje fundet - returnerer tomt resultat")
        

        return result
        
    except Exception as e:
        analysis_log_message(self, f"Fejl ved linjefinding: {str(e)}")
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
                plot_tracking_result(self, image_data, result, filepath, save_plots, radius_pixelsum, csv_index)
        
        return result
        
    except Exception as e:
        analysis_log_message(self, f"Fejl ved positionsfinding: {str(e)}")
        return {'x_sat': np.nan, 'y_sat': np.nan, 'pixel_sum': np.nan, 'error': str(e)}

def analyze_starfield_reference(self, directory, starfield_file, astap_path):
    """Analyser stjernehimmel reference med ASTAP"""
    try:
        analysis_log_message(self, f"Analyserer stjernehimmel reference med ASTAP...")
        
        filepath = os.path.join(directory, starfield_file)
        wcsfile = os.path.join(directory, starfield_file.replace(".fits", ".wcs"))
        
        # Kør ASTAP
        result = subprocess.run(
            [astap_path, "-f", filepath, "-wcs", wcsfile],
            capture_output=True, text=True
        )
        
        if result.returncode != 0:
            analysis_log_message(self, f"ASTAP fejlede: {result.stderr}")
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
            
            analysis_log_message(self, f"ASTAP offset: RA={ra_offset:.6f}°, DEC={dec_offset:.6f}°, ROT={rotation_offset:.3f}°")
            
            # Ryd op
            os.remove(wcsfile)
            
            return {
                'ra_offset': ra_offset,
                'dec_offset': dec_offset, 
                'rotation_offset': rotation_offset
            }
        else:
            analysis_log_message(self, "ASTAP producerede ingen WCS fil")
            return {'ra_offset': 0, 'dec_offset': 0, 'rotation_offset': 0}
            
    except Exception as e:
        analysis_log_message(self, f"Fejl ved ASTAP analyse: {str(e)}")
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
            
            analysis_log_message(self, f"Plot gemt")
            
    except Exception as e:
        analysis_log_message(self, f"Fejl ved plotting: {str(e)}")

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
            from matplotlib.patches import Circle
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
            
            analysis_log_message(self, f"Plot gemt: {os.path.basename(plot_path)}")
            
    except Exception as e:
        analysis_log_message(self, f"Fejl ved plotting: {str(e)}")

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
        
        analysis_log_message(self, f"Viser {len(plot_files)} plots i GUI...")
        
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
        
        analysis_log_message(self, f"Plots vist i GUI - scroll for at se alle")
            
    except Exception as e:
        analysis_log_message(self, f"Fejl ved visning af plots i GUI: {str(e)}")

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
            
    display_plots_in_gui(self, directory)

def show_analysis_plots(self, directory):
    """Vis alle gemte analyse plots efter analysen er færdig"""
    try:
        import matplotlib
        matplotlib.use('TkAgg')  # Skift tilbage til GUI backend for visning
        
        # Find alle gemte plot filer
        plot_files = [f for f in os.listdir(directory) if f.endswith('_plot.png')]
        
        if not plot_files:
            analysis_log_message(self, "Ingen plot filer fundet til visning")
            return
        
        analysis_log_message(self, f"Viser {len(plot_files)} gemte plots...")
        
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
        analysis_log_message(self, f"Fejl ved visning af plots: {str(e)}")

