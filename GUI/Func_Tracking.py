"""
Func_Tracking.py - Tracking Observation Tab Functions
Contains UI initialization for tracking observation features
"""

import tkinter as tk
from tkinter import ttk, messagebox
import os
import time
import requests
import threading
from datetime import datetime, timedelta

# Check for optional dependencies
try:
    from pwi4_client import PWI4Client
    PWI4_AVAILABLE = True
except ImportError:
    PWI4_AVAILABLE = False


def create_tracking_tab(self, notebook):
    """Tab til Tracking observation med PlaneWave4"""
    tracking_frame = ttk.Frame(notebook)
    notebook.add(tracking_frame, text="Tracking Observation")
    
    # Opret en canvas og scrollbar for at gøre indholdet scrollbart
    canvas = tk.Canvas(tracking_frame)
    v_scrollbar = ttk.Scrollbar(tracking_frame, orient="vertical", command=canvas.yview)
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
    
    # Satelit valg sektion (venstre side)
    selection_frame = ttk.LabelFrame(left_frame, text="Satelit Valg")
    selection_frame.pack(fill='x', pady=(0, 10))
    
    ttk.Label(selection_frame, text="Vælg en satelitt fra 'Hent Satelitlister' fanen for at starte tracking").pack(pady=5)
    
    button_frame = ttk.Frame(selection_frame)
    button_frame.pack(pady=5)
    
    ttk.Button(button_frame, text="Hent Valgt Satelitt", 
              command=self.get_selected_satellite_for_tracking).pack(side='left', padx=5)
    
    # Satelit info display
    info_frame = ttk.LabelFrame(selection_frame, text="Valgt Satelit Info")
    info_frame.pack(fill='x', pady=5)
    
    self.tracking_sat_info_text = tk.Text(info_frame, height=3, wrap='word')
    self.tracking_sat_info_text.pack(fill='x', padx=5, pady=5)
    
    # Tracking parametere sektion (venstre side)
    params_frame = ttk.LabelFrame(left_frame, text="Tracking Parametre")
    params_frame.pack(fill='x', pady=(0, 10))
    
    # Parameter inputs i grid layout
    ttk.Label(params_frame, text="Exposure Time (sek):").grid(row=0, column=0, sticky='w', padx=5, pady=5)
    self.exposure_time_entry = ttk.Entry(params_frame, width=10)
    self.exposure_time_entry.grid(row=0, column=1, padx=5, pady=5)
    self.exposure_time_entry.insert(0, "2.0")
    
    ttk.Label(params_frame, text="Interval mellem billeder (sek):").grid(row=0, column=2, sticky='w', padx=5, pady=5)
    self.tracking_interval_entry = ttk.Entry(params_frame, width=10)
    self.tracking_interval_entry.grid(row=0, column=3, padx=5, pady=5)
    self.tracking_interval_entry.insert(0, "5.0")
    
    ttk.Label(params_frame, text="Antal billeder:").grid(row=1, column=0, sticky='w', padx=5, pady=5)
    self.num_images_entry = ttk.Entry(params_frame, width=10)
    self.num_images_entry.grid(row=1, column=1, padx=5, pady=5)
    self.num_images_entry.insert(0, "10")
    
    ttk.Label(params_frame, text="PlaneWave4 URL:").grid(row=1, column=2, sticky='w', padx=5, pady=5)
    self.pw4_url_entry = ttk.Entry(params_frame, width=20)
    self.pw4_url_entry.grid(row=1, column=3, padx=5, pady=5)
    self.pw4_url_entry.insert(0, "http://localhost:8220")
    
    # Destinationsmappen
    ttk.Label(params_frame, text="Destinationsmapp:").grid(row=2, column=0, sticky='w', padx=5, pady=5)
    self.tracking_destination_entry = ttk.Entry(params_frame, width=20)
    self.tracking_destination_entry.grid(row=2, column=1, columnspan=1, padx=5, pady=5)
    self.tracking_destination_entry.insert(0, os.getcwd())
    
    ttk.Button(params_frame, text="Gennemse", 
              command=lambda: browse_tracking_destination(self)).grid(row=2, column=2, padx=5, pady=5)
    
    # Test forbindelse knap (binning styres nu fra kameraindstillinger)
    ttk.Button(params_frame, text="Test PlaneWave4 Forbindelse", 
              command=self.test_pw4_connection).grid(row=3, column=0, columnspan=2, pady=10, padx=5)
    
    # Status display
    self.pw4_status_label = ttk.Label(params_frame, text="Status: Ikke testet", foreground='gray')
    self.pw4_status_label.grid(row=4, column=2, columnspan=2, pady=10, padx=5, sticky='w')
    
    # Tracking control sektion (venstre side)
    control_frame = ttk.LabelFrame(left_frame, text="Tracking Control")
    control_frame.pack(fill='x', pady=(0, 10))
    
    control_button_frame = ttk.Frame(control_frame)
    control_button_frame.pack(pady=10)
    
    self.start_tracking_btn = ttk.Button(control_button_frame, text="Start Tracking", 
                                       command=self.start_tracking_observation)
    self.start_tracking_btn.pack(side='left', padx=5)
    
    self.stop_tracking_btn = ttk.Button(control_button_frame, text="Stop Tracking", 
                                      command=self.stop_tracking_observation, state='disabled')
    self.stop_tracking_btn.pack(side='left', padx=5)
    
    # Manual TLE input sektion (venstre side)
    manual_frame = ttk.LabelFrame(left_frame, text="Manuel TLE Input (valgfrit)")
    manual_frame.pack(fill='x', pady=(0, 10))
    
    ttk.Label(manual_frame, text="Satellit navn:").grid(row=0, column=0, sticky='w', padx=5, pady=2)
    self.manual_sat_name_entry = ttk.Entry(manual_frame, width=30)
    self.manual_sat_name_entry.grid(row=0, column=1, padx=5, pady=2, sticky='ew')
    
    ttk.Label(manual_frame, text="TLE Line 1:").grid(row=1, column=0, sticky='w', padx=5, pady=2)
    self.manual_tle1_entry = ttk.Entry(manual_frame, width=70)
    self.manual_tle1_entry.grid(row=1, column=1, padx=5, pady=2, sticky='ew')
    
    ttk.Label(manual_frame, text="TLE Line 2:").grid(row=2, column=0, sticky='w', padx=5, pady=2)
    self.manual_tle2_entry = ttk.Entry(manual_frame, width=70)
    self.manual_tle2_entry.grid(row=2, column=1, padx=5, pady=2, sticky='ew')
    
    manual_frame.grid_columnconfigure(1, weight=1)
    
    ttk.Button(manual_frame, text="Brug Manuel TLE", 
              command=self.use_manual_tle).grid(row=3, column=0, columnspan=2, pady=5)
    
    # Tracking log sektion (højre side)
    log_frame = ttk.LabelFrame(right_frame, text="Tracking Log")
    log_frame.pack(fill='both', expand=True)
    
    # Sæt en passende bredde på log området
    right_frame.configure(width=420)
    right_frame.pack_propagate(False)
    
    # Log text widget med scrollbar
    log_container = ttk.Frame(log_frame)
    log_container.pack(fill='both', expand=True, padx=5, pady=5)
    
    self.tracking_log_text = tk.Text(log_container, width=52, wrap='word')
    tracking_log_scrollbar = ttk.Scrollbar(log_container, orient='vertical', command=self.tracking_log_text.yview)
    self.tracking_log_text.configure(yscrollcommand=tracking_log_scrollbar.set)
    
    tracking_log_scrollbar.pack(side='right', fill='y')
    self.tracking_log_text.pack(side='left', fill='both', expand=True)
    
    # Clear log button
    ttk.Button(log_frame, text="Ryd Log", 
              command=lambda: self.tracking_log_text.delete(1.0, tk.END)).pack(pady=2)
    
    # Billedvisningssektion under loggen (højre side)
    tracking_image_frame = ttk.LabelFrame(right_frame, text="Seneste Billede")
    tracking_image_frame.pack(fill='x', pady=5)
    
    # Label til at vise billede
    self.tracking_image_label = ttk.Label(tracking_image_frame, text="Venter på billede...")
    self.tracking_image_label.pack(pady=10)


def tracking_log_message(self, message):
    """Tilføj besked til tracking log"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    self.tracking_log_text.insert(tk.END, f"[{timestamp}] {message}\n")
    self.tracking_log_text.see(tk.END)
    self.root.update()

def browse_tracking_destination(self):
    """Vælg destinationsmappe for Tracking observationsfiler"""
    from tkinter.filedialog import askdirectory
    
    directory = askdirectory(title="Vælg destinationsmappe for Tracking filer")
    if directory:
        self.tracking_destination_entry.delete(0, tk.END)
        self.tracking_destination_entry.insert(0, directory)
        tracking_log_message(self, f"Destinationsmapp sat til: {directory}")

def display_tracking_image(self, image_data):
    """Vis downscaled version af billedet under tracking loggen"""
    try:
        import numpy as np
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
        self.tracking_image_label.config(image=photo_image, text="")
        self.tracking_image_label.image = photo_image  # Bevar reference
        self.root.update()
        
    except Exception as e:
        tracking_log_message(self, f"Fejl ved visning af billede: {str(e)}")


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
                    tracking_log_message(self, f"PlaneWave4 forbindelse OK (testet {endpoint})")
                    return
            except:
                continue
        
        # Hvis ingen endpoints svarede positivt
        self.pw4_status_label.config(text="Status: Ingen gyldige endpoints", foreground='red')
        tracking_log_message(self, "PlaneWave4: Ingen kendte endpoints svarede")
            
    except requests.exceptions.Timeout:
        self.pw4_status_label.config(text="Status: Timeout", foreground='red')
        tracking_log_message(self, "PlaneWave4 forbindelse timeout")
    except requests.exceptions.ConnectionError:
        self.pw4_status_label.config(text="Status: Kan ikke forbinde", foreground='red')
        tracking_log_message(self, "Kan ikke forbinde til PlaneWave4")
    except Exception as e:
        self.pw4_status_label.config(text="Status: Fejl", foreground='red')
        tracking_log_message(self, f"Fejl ved test af PlaneWave4: {str(e)}")


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
        
        tracking_log_message(self, f"Valgt satellit til tracking: {self.selected_tracking_satellite['SatName']}")
        
    except Exception as e:
        messagebox.showerror("Fejl", f"Kunne ikke hente satellit information: {str(e)}")
        tracking_log_message(self, f"Fejl ved valg af satellit: {str(e)}")


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
        
        tracking_log_message(self, f"Manuel TLE data anvendt for: {sat_name}")
        
    except Exception as e:
        messagebox.showerror("Fejl", f"Kunne ikke anvende manuel TLE: {str(e)}")
        tracking_log_message(self, f"Fejl ved manuel TLE: {str(e)}")


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
    if not validate_tracking_parameters(self):
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
    threading.Thread(target=run_tracking_observation, args=(self,), daemon=True).start()


def stop_tracking_observation(self):
    """Stop tracking observation"""
    self.stop_tracking = True
    tracking_log_message(self, "Stop signal sendt til tracking...")


def run_tracking_observation(self):
    """Kør tracking observation med PlaneWave4"""
    import numpy as np
    from astropy.io import fits
    from Func_KameraInstillinger import optimized_camera_exposure_with_timing
    
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
            from pwi4_client import PWI4Telescope
            # Opret PWI4 klient
            pw4_host = pw4_url.replace("http://", "").split(":")[0]
            pw4_port = int(pw4_url.split(":")[-1]) if ":" in pw4_url else 8220
            
            pwi4 = PWI4Telescope(host=pw4_host, port=pw4_port)
            
            if not pwi4.test_connection():
                raise Exception(f"Kan ikke forbinde til PWI4 på {pw4_url}")
            
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
                
                # Hent destinationsmappe fra UI eller brug standard
                base_dir = self.tracking_destination_entry.get().strip()
                if not base_dir or not os.path.isdir(base_dir):
                    base_dir = os.getcwd()
                
                output_dir = os.path.join(base_dir, f"Tracking_{safe_sat_name}_{norad_id}_{session_date}")
                
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
                    star_result = optimized_camera_exposure_with_timing(
                        self,
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
                    
                    # Vis billede under tracking loggen
                    display_tracking_image(self, star_img_data)
                    
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
                satellite_result = optimized_camera_exposure_with_timing(
                    self,
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
                
                # Vis billede under tracking loggen
                display_tracking_image(self, img_data)
                
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
