"""Module for TLE calculation tab functionality"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import os
import pandas as pd
import numpy as np
import re
from datetime import datetime
import plotly.graph_objects as go
import plotly.offline as pyo

# Optional dependencies
try:
    import orbdtools
    from orbdtools import ArcObs, Body, KeprvTrans
    ORBDTOOLS_AVAILABLE = True
except ImportError:
    ORBDTOOLS_AVAILABLE = False

try:
    from skyfield.api import load, EarthSatellite
    SKYFIELD_AVAILABLE = True
except ImportError:
    SKYFIELD_AVAILABLE = False

try:
    import plotly.graph_objects as go
    import plotly.offline as pyo
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False


def create_calculate_tle_tab(self, notebook):
    """Tab til at beregne TLE fra observationer"""
    tle_frame = ttk.Frame(notebook)
    notebook.add(tle_frame, text="Beregn TLE")
    
    # Opret en canvas og scrollbar for at gøre indholdet scrollbart
    canvas = tk.Canvas(tle_frame)
    v_scrollbar = ttk.Scrollbar(tle_frame, orient="vertical", command=canvas.yview)
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
    
    # Hovedcontainer (nu inde i scrollable_frame)
    main_container = ttk.Frame(scrollable_frame)
    main_container.pack(fill='both', expand=True, padx=10, pady=10)
    
    # Opret to kolonner: venstre for kontrol, højre for log
    left_frame = ttk.Frame(main_container)
    left_frame.pack(side='left', fill='both', expand=True, padx=(0, 5))
    
    right_frame = ttk.Frame(main_container)
    right_frame.pack(side='right', fill='y', expand=False, padx=(5, 0))
    
    # Sæt en passende bredde på log området
    right_frame.configure(width=420)
    right_frame.pack_propagate(False)
    
    # ===== PLOT SEKTION (øverst i venstre side) =====
    
    # Plot frame for TLE afvigelser
    plot_frame = ttk.LabelFrame(left_frame, text="TLE Afvigelsesplot")
    plot_frame.pack(fill='both', expand=False, pady=(0, 10))
    
    # Opret matplotlib figure med 2 subplots (bredde reduceret med 1/4)
    self.tle_plot_figure, self.tle_plot_axes = plt.subplots(2, 1, figsize=(7, 6))
    self.tle_plot_figure.suptitle('TLE Afvigelser: Observeret vs. TLE Forudsigelse', 
                                   fontsize=12, fontweight='bold')
    
    # Tilføj grid og legend til begge subplots
    for ax in self.tle_plot_axes:
        ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
        ax.legend(loc='best', framealpha=0.9)
    
    # Sæt labels for akserne
    self.tle_plot_axes[0].set_ylabel('Afvigelse (grader)', fontsize=10)
    self.tle_plot_axes[0].set_title('ΔRA: Observeret - TLE', fontsize=10, fontweight='bold')
    
    self.tle_plot_axes[1].set_xlabel('Sekunder efter første observation', fontsize=10)
    self.tle_plot_axes[1].set_ylabel('Afvigelse (grader)', fontsize=10)
    self.tle_plot_axes[1].set_title('ΔDEC: Observeret - TLE', fontsize=10, fontweight='bold')
    
    # Juster layout
    self.tle_plot_figure.tight_layout(rect=[0, 0.03, 1, 0.95])
    
    # Embed matplotlib figure i tkinter
    self.tle_canvas = FigureCanvasTkAgg(self.tle_plot_figure, master=plot_frame)
    self.tle_canvas.draw()
    self.tle_canvas.get_tk_widget().pack(fill='both', expand=True)
    
    # ===== KONTROL SEKTION (under plot) =====
    
    # Data indlæsning sektion
    load_frame = ttk.LabelFrame(left_frame, text="Data Indlæsning")
    load_frame.pack(fill='x', pady=(0, 10))
    
    # Mappe valg
    ttk.Label(load_frame, text="CSV fil (data*.csv):").grid(row=0, column=0, sticky='w', padx=5, pady=5)
    self.tle_dir_entry = ttk.Entry(load_frame, width=50)
    self.tle_dir_entry.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
    ttk.Button(load_frame, text="Vælg Mappe", 
              command=self.select_tle_directory).grid(row=0, column=2, padx=5, pady=5)
    
    # Status label
    self.tle_status_label = ttk.Label(load_frame, text="Ingen data indlæst", foreground='gray')
    self.tle_status_label.grid(row=1, column=0, columnspan=3, sticky='w', padx=5, pady=5)
    
    load_frame.grid_columnconfigure(1, weight=1)
    
    # TLE beregnings parametre sektion
    params_frame = ttk.LabelFrame(left_frame, text="TLE Beregnings Parametre")
    params_frame.pack(fill='x', pady=(0, 10))
    
    # Metode valg
    ttk.Label(params_frame, text="IOD Metode:").grid(row=0, column=0, sticky='w', padx=5, pady=5)
    self.tle_method_combo = ttk.Combobox(params_frame, 
                                        values=['gauss', 'laplace', 'gooding', 'double_R', 'multilaplace', 'circular'],
                                        state='readonly', width=20)
    self.tle_method_combo.grid(row=0, column=1, padx=5, pady=5, sticky='w')
    self.tle_method_combo.set('gauss')  # Default metode
    
    # Index valg
    ttk.Label(params_frame, text="Index 1:").grid(row=1, column=0, sticky='w', padx=5, pady=5)
    self.index1_combo = ttk.Combobox(params_frame, state='readonly', width=15)
    self.index1_combo.grid(row=1, column=1, padx=5, pady=5, sticky='w')
    
    ttk.Label(params_frame, text="Index 2:").grid(row=2, column=0, sticky='w', padx=5, pady=5)
    self.index2_combo = ttk.Combobox(params_frame, state='readonly', width=15)
    self.index2_combo.grid(row=2, column=1, padx=5, pady=5, sticky='w')
    
    ttk.Label(params_frame, text="Index 3:").grid(row=3, column=0, sticky='w', padx=5, pady=5)
    self.index3_combo = ttk.Combobox(params_frame, state='readonly', width=15)
    self.index3_combo.grid(row=3, column=1, padx=5, pady=5, sticky='w')
    
    # Info tekst om index valg
    info_label = ttk.Label(params_frame, 
                          text="Vælg 3 observationspunkter til TLE beregning",
                          foreground='blue', font=('Arial', 9, 'italic'))
    info_label.grid(row=4, column=0, columnspan=2, sticky='w', padx=5, pady=2)
    
    # Beregn knap
    ttk.Button(params_frame, text="🚀 Beregn TLE", 
              command=self.calculate_tle_from_observations,
              style='Accent.TButton').grid(row=5, column=0, columnspan=2, pady=10, padx=5)
    
    # Resultat visning sektion
    result_frame = ttk.LabelFrame(left_frame, text="Beregnede Resultater")
    result_frame.pack(fill='both', expand=True, pady=(0, 10))
    
    # TLE linjer display
    tle_display_frame = ttk.Frame(result_frame)
    tle_display_frame.pack(fill='x', padx=5, pady=5)
    
    ttk.Label(tle_display_frame, text="Genereret TLE:", font=('Arial', 10, 'bold')).pack(anchor='w')
    
    self.tle_line1_text = tk.Text(tle_display_frame, height=1, wrap='none', font=('Courier', 9))
    self.tle_line1_text.pack(fill='x', pady=2)
    
    self.tle_line2_text = tk.Text(tle_display_frame, height=1, wrap='none', font=('Courier', 9))
    self.tle_line2_text.pack(fill='x', pady=2)
    
    # Orbital elements display
    orbital_display_frame = ttk.Frame(result_frame)
    orbital_display_frame.pack(fill='x', padx=5, pady=5)
    
    ttk.Label(orbital_display_frame, text="Orbital Elementer:", font=('Arial', 10, 'bold')).pack(anchor='w')
    
    self.orbital_elements_text = tk.Text(orbital_display_frame, height=8, wrap='word', font=('Courier', 9))
    self.orbital_elements_text.pack(fill='both', expand=True, pady=2)
    
    # Knapper for plot og gem
    button_frame = ttk.Frame(result_frame)
    button_frame.pack(fill='x', padx=5, pady=5)
    
    ttk.Button(button_frame, text="Vis 3D Plot", 
              command=self.show_tle_3d_plot).pack(side='left', padx=5)
    
    ttk.Button(button_frame, text="Gem Resultater til CSV", 
              command=self.save_tle_results).pack(side='left', padx=5)
    
    # ===== LOG SEKTION (højre side) =====
    log_frame = ttk.LabelFrame(right_frame, text="TLE Beregnings Log")
    log_frame.pack(fill='both', expand=True)
    
    # Log text widget med scrollbar
    log_container = ttk.Frame(log_frame)
    log_container.pack(fill='both', expand=True, padx=5, pady=5)
    
    self.tle_log_text = tk.Text(log_container, width=52, wrap='word')
    tle_log_scrollbar = ttk.Scrollbar(log_container, orient='vertical', command=self.tle_log_text.yview)
    self.tle_log_text.configure(yscrollcommand=tle_log_scrollbar.set)
    
    tle_log_scrollbar.pack(side='right', fill='y')
    self.tle_log_text.pack(side='left', fill='both', expand=True)
    
    # Clear log button
    ttk.Button(log_frame, text="Ryd Log", 
              command=lambda: self.tle_log_text.delete(1.0, tk.END)).pack(pady=2)
    
    # Tilføj velkomst besked til log
    self.log_tle_message("TLE Beregnings Log startet...")
    if ORBDTOOLS_AVAILABLE:
        self.log_tle_message("✅ orbdtools tilgængelig - klar til beregninger")
    else:
        self.log_tle_message("❌ ADVARSEL: orbdtools ikke tilgængelig!")
        self.log_tle_message("    Installer med: pip install orbdtools")
    self.log_tle_message("\nVælg en mappe med CSV-fil der starter med 'data'.\n")


# =====================================================================
# TLE CALCULATION FUNCTIONS - WRAPPED FOR USE WITH CLASS INSTANCE
# =====================================================================

def log_tle_message(self, message):
    """Tilføj besked til TLE loggen med tidsstempel"""
    try:
        if hasattr(self, 'tle_log_text'):
            timestamp = datetime.now().strftime('%H:%M:%S')
            log_entry = f"[{timestamp}] {message}\n"
            self.tle_log_text.insert(tk.END, log_entry)
            self.tle_log_text.see(tk.END)
            self.root.update_idletasks()
    except Exception as e:
        print(f"Log fejl: {e}")

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
        load_tle_csv_data(self, directory)

def load_tle_csv_data(self, directory):
    """Load CSV file from folder for TLE calculation"""
    try:
        log_tle_message(self, f"Searching for CSV file in: {directory}")
        
        # Find CSV files starting with 'data'
        csv_files = [f for f in os.listdir(directory) if f.lower().startswith('data') and f.lower().endswith('.csv')]
        
        if not csv_files:
            log_tle_message(self, "❌ No CSV files found starting with 'data'")
            self.tle_status_label.config(text="No data CSV file found in folder", foreground='red')
            messagebox.showerror("Error", "No CSV files found starting with 'data' in the selected folder")
            return
        
        # Use first file
        csv_file = csv_files[0]
        csv_path = os.path.join(directory, csv_file)
        log_tle_message(self, f"Found CSV file: {csv_file}")
        
        # Load CSV file
        df = pd.read_csv(csv_path)
        log_tle_message(self, f"✅ Loaded {len(df)} observations")

        # Filter out rows with OBSTYPE = 'stjernehimmel'
        if 'OBSTYPE' in df.columns:
            before_filter = len(df)
            df = df[df['OBSTYPE'] != 'stjernehimmel']
            after_filter = len(df)
            if before_filter != after_filter:
                filtered_count = before_filter - after_filter
                log_tle_message(self, f"Filtered out {filtered_count} starfield observations")
                log_tle_message(self, f"✅ {after_filter} observations remaining after filtering")
        
        # Filter out rows where Sat_RA_Behandlet has no value
        if 'Sat_RA_Behandlet' in df.columns:
            before_filter = len(df)
            df = df[df['Sat_RA_Behandlet'].notna()]
            after_filter = len(df)
            if before_filter != after_filter:
                filtered_count = before_filter - after_filter
                log_tle_message(self, f"Filtered out {filtered_count} observations without processed data")
                log_tle_message(self, f"✅ {after_filter} observations remaining after filtering")
        
        # Check that required columns exist for TLE calculation
        required_columns = ['Sat_RA_Behandlet', 'Sat_DEC_Behandlet', 'X_obs', 'Y_obs', 'Z_obs', 'DATE-OBS']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            log_tle_message(self, f"❌ Missing columns: {', '.join(missing_columns)}")
            messagebox.showerror("Error", f"CSV file is missing the following columns:\n{', '.join(missing_columns)}")
            return
        
        # Store data
        self.tle_csv_data = df
        
        # Update index dropdown menus
        log_tle_message(self, "Updating index options...")
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
            log_tle_message(self, f"✅ Default indices set: 0, {middle_idx}, {len(df)-1}")
        else:
            log_tle_message(self, "WARNING: Less than 3 observations in CSV!")
            messagebox.showwarning("Warning", "CSV file contains less than 3 observations.\nAt least 3 observations are required for TLE calculation.")
        
        # Update status
        self.tle_status_label.config(text=f"✅ Data loaded: {csv_file} ({len(df)} obs.)", foreground='green')
        log_tle_message(self, f"✅ CSV data ready for TLE calculation")
        log_tle_message(self, f"   Columns: {', '.join(df.columns.tolist()[:10])}{'...' if len(df.columns) > 10 else ''}")
        
        # Check if TLE columns exist and calculate deviations if yes
        if 'TLE1' in df.columns and 'TLE2' in df.columns:
            log_tle_message(self, "TLE columns found - calculating deviations...")
            calculate_tle_deviations(self, df)
        else:
            log_tle_message(self, "TLE1 and TLE2 columns not found - cannot calculate deviations yet")
        
    except Exception as e:
        error_msg = f"Error loading CSV: {str(e)}"
        log_tle_message(self, f"❌ {error_msg}")
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
        ra_rad += 2*np.pi

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
            log_tle_message(self, "❌ TLE1 and/or TLE2 columns not found in data")
            return
            
        tle_line1, tle_line2 = results_df['TLE1'].iloc[0], results_df['TLE2'].iloc[0]
        
        log_tle_message(self, "Calculating satellite positions from TLE...")
        
        # Check required columns for calculate_satellite_data
        required_cols = ['DATE-OBS', 'LONG-OBS', 'ELEV-OBS']
        missing_cols = [col for col in required_cols if col not in results_df.columns]
        
        # Check LAT column (can have two different names)
        has_lat = 'LAT-OBS' in results_df.columns or 'LAT--OBS' in results_df.columns
        if not has_lat:
            missing_cols.append('LAT-OBS or LAT--OBS')
        
        if missing_cols:
            log_tle_message(self, f"❌ Missing columns for satellite calculation: {missing_cols}")
            log_tle_message(self, f"Available columns: {list(results_df.columns)}")
            return
        
        # Check if Func_fagprojekt functions are available
        try:
            from Func_fagprojekt import calculate_satellite_data
            # Reset DataFrame index to ensure sequential integer indices (0,1,2...)
            df_for_calc = results_df.reset_index(drop=True)
            log_tle_message(self, f"Reset DataFrame index for calculation")
            
            # Calculate satellite data
            afstand, vinkel, sat_pos, earth_pos, obs_points = calculate_satellite_data(
                df_for_calc, tle_line1, tle_line2
            )
        except Exception as func_error:
            log_tle_message(self, f"❌ Error in calculate_satellite_data: {str(func_error)}")
            log_tle_message(self, f"Error type: {type(func_error).__name__}")
            log_tle_message(self, "Check that Func_fagprojekt.py is available and compatible")
            log_tle_message(self, f"DataFrame columns: {list(results_df.columns)}")
            log_tle_message(self, f"DataFrame shape: {results_df.shape}")
            log_tle_message(self, f"DataFrame index: {results_df.index.tolist()}")
            if len(results_df) > 0:
                sample_row = results_df.iloc[0]
                log_tle_message(self, f"First row example: DATE-OBS={sample_row.get('DATE-OBS', 'MISSING')}")
                log_tle_message(self, f"LAT-OBS/LAT--OBS: {sample_row.get('LAT-OBS', sample_row.get('LAT--OBS', 'MISSING'))}")
            import traceback
            log_tle_message(self, f"Detailed error:\n{traceback.format_exc()}")
            return
        
        satellite_positions = np.array(sat_pos)
        observation_points = np.array(obs_points)
        
        # Calculate relative positions
        x_list = satellite_positions[:, 0] - observation_points[:, 0]
        y_list = satellite_positions[:, 1] - observation_points[:, 1]
        z_list = satellite_positions[:, 2] - observation_points[:, 2]
        
        # Convert to RA/DEC
        log_tle_message(self, "Converting to RA/DEC coordinates...")
        ra_tle = []
        dec_tle = []
        for i in range(len(x_list)):
            ra, dec = xyz_to_radec(self, x_list[i], y_list[i], z_list[i])
            ra_tle.append(ra)
            dec_tle.append(dec)
        
        ra_tle = np.array(ra_tle)
        dec_tle = np.array(dec_tle)
        
        # Get observed positions
        try:
            sat_ra_behandlet = results_df['Sat_RA_Behandlet'].values
            sat_dec_behandlet = results_df['Sat_DEC_Behandlet'].values
            sat_ra_teleskop = results_df['RA_J2000'].values * 15
            sat_dec_teleskop = results_df['DEC'].values
        except KeyError as e:
            log_tle_message(self, f"❌ Missing column: {str(e)}")
            log_tle_message(self, "Check that CSV file contains all necessary columns")
            return
        
        # Calculate deviations
        log_tle_message(self, "Calculating deviations...")
        delta_ra_teleskop = angle_diff_deg(self, sat_ra_teleskop, ra_tle)
        delta_dec_teleskop = angle_diff_deg(self, sat_dec_teleskop, dec_tle)
        delta_ra_behandlet = angle_diff_deg(self, sat_ra_behandlet, ra_tle)
        delta_dec_behandlet = angle_diff_deg(self, sat_dec_behandlet, dec_tle)
        
        # Calculate time in seconds after first measurement
        if 'JD' in results_df.columns:
            jd_first = results_df["JD"].iloc[0]
            seconds_after_first_measurement = (results_df["JD"] - jd_first) * 86400
        else:
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
        
        log_tle_message(self, f"✅ Calculated deviations for {len(delta_ra_behandlet)} data points")
        
        # Update plot
        log_tle_message(self, "Updating plot...")
        update_tle_plot(self)
        
    except Exception as e:
        error_msg = f"Error calculating TLE deviations: {str(e)}"
        log_tle_message(self, f"❌ {error_msg}")
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
        
        log_tle_message(self, "✅ Plot updated successfully")
        
    except Exception as e:
        error_msg = f"Error updating plot: {str(e)}"
        log_tle_message(self, f"❌ {error_msg}")
        print(error_msg)
        import traceback
        print(traceback.format_exc())

def double_R(self, times, meas, positions, satid=99999):
    """Double-R IOD metode"""
    arc_optical = ArcObs({'t': times, 'radec': meas, 'xyz_site': positions})
    arc_optical.lowess_smooth()
    
    earth = Body.from_name('Earth')
    arc_iod = arc_optical.iod(earth)
    arc_iod.doubleR(ellipse_only=False)
    log_tle_message(self, f"Double-R resultater:\n{arc_iod.df.to_string()}")
    
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
    log_tle_message(self, f"Multi-Laplace resultater:\n{arc_iod.df.to_string()}")
    
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
    log_tle_message(self, f"Laplace resultater:\n{arc_iod.df.to_string()}")
    
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
    log_tle_message(self, f"Gauss resultater:\n{arc_iod.df.to_string()}")
    
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
    log_tle_message(self, f"Circular resultater:\n{arc_iod.df.to_string()}")
    
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
    log_tle_message(self, f"Gooding resultater:\n{arc_iod.df.to_string()}")
    
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
    """Konverter float til TLE kompakt notation som '34500-3' eller '-4500-5'"""
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
    
    return f"{sign_prefix}{mantissa_int:05d}{sign_exp}{exp_abs}"

def format_first_derivative(self, value):
    """Formatter mean motion dot til TLE: fx .00000186 eller -.0000186"""
    s = f"{value:.8f}"
    if s.startswith("0"):
        s = s[1:]
    elif s.startswith("-0"):
        s = "-" + s[2:]
    return s

def format_tle(self, ta0, ele0, params, a):
    """Konverter orbdtools TLE data til standard TLE format (2 linjer)"""
    satid, reff, bstar, nddot, classification, intldesg, elnum, revnum = params
    n, ecc, inc, raan, argp, M = ele0

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

    GM = 3.986004415e5
    a_km = a
    n_rad = np.sqrt(GM / a_km**3)
    n_revperday = (n_rad / (2 * np.pi)) * 86400.0

    df = getattr(self, "tle_csv_data", None)
    if df is not None and 'TLE1' in df.columns:
        original_tle1 = str(df['TLE1'].iloc[0])

        intldesg = original_tle1[9:17].strip()

        orig_elnum_str = original_tle1[64:68].strip()
        if orig_elnum_str.isdigit():
            orig_elnum = int(orig_elnum_str)
            elnum = orig_elnum + 1 if orig_elnum != 999 else 999
        else:
            elnum = int(elnum)

        try:
            first_deriv_str = original_tle1[33:43]
            mean_motion_dot = float(first_deriv_str.strip())
        except:
            mean_motion_dot = 0.0

        try:
            ddot_field = original_tle1[44:52]
            nddot = parse_compact_tle_notation(self, ddot_field)
        except:
            nddot = 0.0

        try:
            bstar_field = original_tle1[53:61]
            bstar = parse_compact_tle_notation(self, bstar_field)
        except:
            bstar = 0.0

    mean_motion_dot_str = format_first_derivative(self, mean_motion_dot)
    mean_motion_dot_str = f"{mean_motion_dot_str:>10s}"

    ddot_str = _compact_tle_notation(self, nddot)
    bstar_str = _compact_tle_notation(self, bstar)

    line1_data = (
        f"1 {satid:5d}{classification}"
        f" {intldesg:8s} "
        f"{epoch_str:14s} "
        f"{mean_motion_dot_str} "
        f"{ddot_str:>8s} "
        f"{bstar_str:>8s}"
        f" 0 {int(elnum):>4d}"
    )
    checksum1 = calculate_tle_checksum(self, line1_data)
    line1 = line1_data[:68] + str(checksum1)

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
    checksum2 = calculate_tle_checksum(self, line2_data)
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
        log_tle_message(self, "❌ FEJL: orbdtools ikke tilgængelig!")
        messagebox.showerror("Fejl", "orbdtools biblioteket er ikke installeret.\n\nInstaller med: pip install orbdtools")
        return None
    
    metode_funktioner = {
        'double_R': double_R,
        'multilaplace': multilaplace,
        'laplace': laplace,
        'gauss': gauss,
        'circular': circular,
        'gooding': gooding
    }
    
    if metode not in metode_funktioner:
        raise ValueError(f"Ukendt metode '{metode}'. Tilgængelige metoder: {list(metode_funktioner.keys())}")
    
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
    
    if metode == 'gooding':
        log_tle_message(self, f"Bruger metode: {metode} (alle {len(DATE_OBS)} datapunkter)")
        
        if isinstance(DATE_OBS, pd.Series):
            tider_pandas = DATE_OBS.values
        else:
            tider_pandas = np.array(DATE_OBS)
        
        from astropy.time import Time
        tider = Time(tider_pandas)
        r_ = positions
        angles_ = angles
    else:
        if len(index_list) != 3:
            raise ValueError(f"index_list skal indeholde præcis 3 indices, fik {len(index_list)}")
        
        idx = index_list
        log_tle_message(self, f"Bruger metode: {metode} (indices: {idx})")
        
        if isinstance(DATE_OBS, pd.Series):
            tider_pandas = np.array([DATE_OBS.iloc[idx[0]], DATE_OBS.iloc[idx[1]], DATE_OBS.iloc[idx[2]]])
        else:
            tider_pandas = np.array([DATE_OBS[idx[0]], DATE_OBS[idx[1]], DATE_OBS[idx[2]]])
        
        from astropy.time import Time
        tider = Time(tider_pandas)
        r_ = np.array([positions[idx[0]], positions[idx[1]], positions[idx[2]]])
        angles_ = np.array([angles[idx[0]], angles[idx[1]], angles[idx[2]]])
    
    metode_funktion = metode_funktioner[metode]
    R, v, coe, tle_data = metode_funktion(self, tider, angles_, r_, satid=NoradID)
    
    ta0, ele0, params = tle_data
    line1, line2 = format_tle(self, ta0, ele0, params, coe[0])
    
    return {
        'r': R,
        'v': v, 
        'coe': coe,
        'tle': tle_data,
        'tle_lines': (line1, line2),
        'method': metode
    }

def calculate_tle_from_observations(self):
    """Beregner TLE baseret på valgte parametre"""
    try:
        if self.tle_csv_data is None:
            messagebox.showwarning("Ingen data", "Indlæs først en CSV-fil med observationsdata")
            log_tle_message(self, "❌ Ingen data indlæst")
            return
        
        try:
            idx1 = int(self.index1_combo.get())
            idx2 = int(self.index2_combo.get())
            idx3 = int(self.index3_combo.get())
            index_list = [idx1, idx2, idx3]
        except:
            messagebox.showerror("Fejl", "Vælg 3 gyldige indices")
            log_tle_message(self, "❌ Ugyldige indices valgt")
            return
        
        if len(set(index_list)) != 3:
            messagebox.showerror("Fejl", "Vælg 3 forskellige indices")
            log_tle_message(self, "❌ Indices skal være forskellige")
            return
        
        metode = self.tle_method_combo.get()
        
        log_tle_message(self, f"Starter TLE beregning...")
        log_tle_message(self, f"Metode: {metode}")
        log_tle_message(self, f"Indices: {index_list}")
        
        df = self.tle_csv_data
        
        Sat_RA = df['Sat_RA_Behandlet'].values
        Sat_DEC = df['Sat_DEC_Behandlet'].values
        X_obs = df['X_obs'].values
        Y_obs = df['Y_obs'].values
        Z_obs = df['Z_obs'].values
        DATE_OBS = pd.to_datetime(df['DATE-OBS'])
        NoradID = int(df['NORAD_ID'].iloc[0]) if 'NORAD_ID' in df.columns else 99999
        
        log_tle_message(self, f"NORAD ID: {NoradID}")
        
        result = beregn_TLE_fra_observationer(
            self,
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
            log_tle_message(self, "❌ TLE beregning fejlede")
            return
        
        self.tle_result = result

        save_tle_results(self)
        
        line1, line2 = result['tle_lines']
        self.tle_line1_text.delete(1.0, tk.END)
        self.tle_line1_text.insert(1.0, line1)
        self.tle_line2_text.delete(1.0, tk.END)
        self.tle_line2_text.insert(1.0, line2)
        
        log_tle_message(self, "✅ TLE genereret:")
        log_tle_message(self, f"{line1}")
        log_tle_message(self, f"{line2}")
        
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
        
        log_tle_message(self, f"✅ Orbital elementer beregnet")
        
        if self.tle_csv_data is not None:
            log_tle_message(self, "Tilføjer TLE linjer til data og beregner afvigelser...")
            df_updated = self.tle_csv_data.copy()
            df_updated['TLE1_beregnet'] = line1
            df_updated['TLE2_beregnet'] = line2
            self.tle_csv_data = df_updated
            calculate_tle_deviations(self, df_updated)
        
        messagebox.showinfo("Succes", f"TLE beregnet succesfuldt med {metode} metoden!")
        
    except Exception as e:
        error_msg = f"Fejl ved TLE beregning: {str(e)}"
        log_tle_message(self, f"❌ {error_msg}")
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
        
        log_tle_message(self, "Generating 3D plot...")
        
        earth_radius = 6371
        u, v = np.mgrid[0:2*np.pi:100j, 0:np.pi:50j]
        x = earth_radius * np.cos(u) * np.sin(v)
        y = earth_radius * np.sin(u) * np.sin(v)
        z = earth_radius * np.cos(v)
        
        fig = go.Figure()
        
        fig.add_trace(go.Surface(
            x=x, y=y, z=z,
            colorscale='Blues',
            opacity=0.5,
            showscale=False,
            name='Earth'
        ))
        
        satellite = None
        ts_times = None

        df = self.tle_csv_data
        
        if SKYFIELD_AVAILABLE:
            ts = load.timescale()
            
            if 'Calculated_TLE_Line1' in df.columns and 'Calculated_TLE_Line2' in df.columns:
                line1 = df['Calculated_TLE_Line1'].iloc[0]
                line2 = df['Calculated_TLE_Line2'].iloc[0]
                
                log_tle_message(self, f"TLE Lines from DataFrame:\n{line1}\n{line2}")
                
            else:
                log_tle_message(self, "Calculated_TLE_Line1/Calculated_TLE_Line2 columns not found in CSV")
                if self.tle_result and 'tle_lines' in self.tle_result:
                    line1, line2 = self.tle_result['tle_lines']
                    log_tle_message(self, f"Fallback to TLE from tle_result:\n{line1}\n{line2}")
                else:
                    line1, line2 = None, None
                    log_tle_message(self, "❌ No TLE data available")
            
            if line1 and line2:
                log_tle_message(self, "Creating satellite from calculated TLE...")
                
                try:
                    satellite = EarthSatellite(line1, line2, 'Calculated TLE', ts)
                    log_tle_message(self, "✅ Calculated TLE satellite created successfully")
                except Exception as e:
                    log_tle_message(self, f"❌ Could not create satellite from calculated TLE: {str(e)}")
                    satellite = None
            else:
                log_tle_message(self, "❌ Calculated TLE data missing or empty")
                satellite = None
            
            if satellite is not None:
                times = pd.to_datetime(df['DATE-OBS'])
                t_center = times.iloc[len(times)//2]
                
                time_range = [t_center + pd.Timedelta(seconds=delta) for delta in np.arange(-45*60, 45*60 + 5, 5)]
                
                years = [t.year for t in time_range]
                months = [t.month for t in time_range]
                days = [t.day for t in time_range]
                hours = [t.hour for t in time_range]
                minutes = [t.minute for t in time_range]
                seconds = [t.second + t.microsecond/1e6 for t in time_range]
                
                ts_times = ts.utc(years, months, days, hours, minutes, seconds)
                
                tle_positions = satellite.at(ts_times).position.km.T
                
                fig.add_trace(go.Scatter3d(
                    x=tle_positions[:, 0],
                    y=tle_positions[:, 1],
                    z=tle_positions[:, 2],
                    mode='lines',
                    name=f'Calculated TLE ({self.tle_result["method"]})',
                    line=dict(width=3, color='red')
                ))
            
                if 'TLE1' in df.columns and 'TLE2' in df.columns and 'ts_times' in locals():
                    original_tle1 = df['TLE1'].iloc[0]
                    original_tle2 = df['TLE2'].iloc[0]
                    
                    if pd.notna(original_tle1) and pd.notna(original_tle2) and original_tle1.strip() and original_tle2.strip():
                        log_tle_message(self, "Plotting original TLE...")
                        
                        try:
                            original_satellite = EarthSatellite(original_tle1, original_tle2, 'Original TLE', ts)
                            
                            original_tle_positions = original_satellite.at(ts_times).position.km.T
                        
                            
                            fig.add_trace(go.Scatter3d(
                                x=original_tle_positions[:, 0],
                                y=original_tle_positions[:, 1],
                                z=original_tle_positions[:, 2],
                                mode='lines',
                                name='Original TLE',
                                line=dict(width=3, color='blue', dash='dot')
                            ))
                            
                            log_tle_message(self, "✅ Original TLE added to plot")
                            
                        except Exception as e:
                            log_tle_message(self, f"⚠️ Could not plot original TLE: {str(e)}")
                    else:
                        log_tle_message(self, "⚠️ Original TLE data missing or empty")
                else:
                    log_tle_message(self, "⚠️ TLE1/TLE2 columns not found in CSV or no time interval")
            else:
                log_tle_message(self, "⚠️ Could not create calculated TLE satellite")
            
        else:
            log_tle_message(self, "⚠️ Skyfield not available, cannot show calculated orbit from TLE")
        
        if satellite is not None and 'Sat_RA_Behandlet' in df.columns and 'Sat_DEC_Behandlet' in df.columns:
            log_tle_message(self, "Calculating satellite positions from RA/DEC and TLE distance...")
            
            sat_ra_behandlet = df['Sat_RA_Behandlet'].values
            sat_dec_behandlet = df['Sat_DEC_Behandlet'].values
            obs_times = pd.to_datetime(df['DATE-OBS'])
            
            obs_years = [t.year for t in obs_times]
            obs_months = [t.month for t in obs_times]
            obs_days = [t.day for t in obs_times]
            obs_hours = [t.hour for t in obs_times]
            obs_minutes = [t.minute for t in obs_times]
            obs_seconds = [t.second + t.microsecond/1e6 for t in obs_times]
            
            ts_obs_times = ts.utc(obs_years, obs_months, obs_days, obs_hours, obs_minutes, obs_seconds)
            log_tle_message(self, f"Times for satellite {ts_obs_times}")
            tle_sat_positions = satellite.at(ts_obs_times).position.km
            
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
                log_tle_message(self, "❌ Calculated distances contain NaN values")
            
            
            log_tle_message(self, "Converting RA/DEC/Distance to ECI xyz...")
            sat_xyz_from_radec = []
            
            for i in range(len(sat_ra_behandlet)):
                ra_rad = np.radians(sat_ra_behandlet[i])
                dec_rad = np.radians(sat_dec_behandlet[i])
                dist = distances[i]
                
                x_rel = dist * np.cos(dec_rad) * np.cos(ra_rad)
                y_rel = dist * np.cos(dec_rad) * np.sin(ra_rad)
                z_rel = dist * np.sin(dec_rad)
                
                x_abs = x_rel + obs_positions[i][0]
                y_abs = y_rel + obs_positions[i][1]
                z_abs = z_rel + obs_positions[i][2]
                
                sat_xyz_from_radec.append([x_abs, y_abs, z_abs])
            
            sat_xyz_from_radec = np.array(sat_xyz_from_radec)
            
            fig.add_trace(go.Scatter3d(
                x=sat_xyz_from_radec[:, 0],
                y=sat_xyz_from_radec[:, 1],
                z=sat_xyz_from_radec[:, 2],
                mode='markers',
                name='Satellite pos. obs (RA/DEC + TLE dist.)',
                marker=dict(size=5, color='red', symbol='diamond')
            ))
            
            log_tle_message(self, f"✅ Added {len(sat_xyz_from_radec)} satellite positions from RA/DEC")

            fig.add_trace(go.Scatter3d(
                x=self.tle_calculation_data['sat_pos_tle_original'][:, 0],
                y=self.tle_calculation_data['sat_pos_tle_original'][:, 1],
                z=self.tle_calculation_data['sat_pos_tle_original'][:, 2],
                mode='markers',
                name='Satellite pos. TLE',
                marker=dict(size=5, color='blue', symbol='diamond')
            ))
        
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
        
        pyo.plot(fig, filename='tle_3d_plot.html', auto_open=True)
        
        log_tle_message(self, "✅ 3D plot shown in browser")
        
    except Exception as e:
        error_msg = f"Error plotting: {str(e)}"
        log_tle_message(self, f"❌ {error_msg}")
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
        
        log_tle_message(self, "Saving results to CSV...")
        
        csv_files = [f for f in os.listdir(self.tle_csv_directory) if f.startswith('data') and f.endswith('.csv')]
        
        if not csv_files:
            messagebox.showerror("Error", "Could not find CSV file in folder")
            return
        
        csv_path = os.path.join(self.tle_csv_directory, csv_files[0])
        
        df = pd.read_csv(csv_path)
        
        line1, line2 = self.tle_result['tle_lines']
        df['Calculated_TLE_Line1'] = line1
        df['Calculated_TLE_Line2'] = line2
        df['TLE_Method'] = self.tle_result['method']
        
        coe = self.tle_result['coe']
        df['TLE_a_km'] = coe[0]
        df['TLE_ecc'] = coe[1]
        df['TLE_inc_deg'] = coe[2]
        df['TLE_raan_deg'] = coe[3]
        df['TLE_argp_deg'] = coe[4]
        df['TLE_nu_deg'] = coe[5]
        
        r = self.tle_result['r']
        v = self.tle_result['v']
        df['TLE_r_x_km'] = r[0]
        df['TLE_r_y_km'] = r[1]
        df['TLE_r_z_km'] = r[2]
        df['TLE_v_x_kms'] = v[0]
        df['TLE_v_y_kms'] = v[1]
        df['TLE_v_z_kms'] = v[2]
        
        df.to_csv(csv_path, index=False)
        
        log_tle_message(self, f"✅ Results saved to: {csv_files[0]}")
        log_tle_message(self, f"Added columns:")
        log_tle_message(self, f"- Calculated_TLE_Line1, Calculated_TLE_Line2")
        log_tle_message(self, f"- TLE_Method, orbital elements (a,e,i,Ω,ω,ν)")
        log_tle_message(self, f"- Position (r_x,r_y,r_z) and velocity (v_x,v_y,v_z)")
        
        
    except Exception as e:
        error_msg = f"Error saving: {str(e)}"
        log_tle_message(self, f"❌ {error_msg}")
        messagebox.showerror("Error", error_msg)

