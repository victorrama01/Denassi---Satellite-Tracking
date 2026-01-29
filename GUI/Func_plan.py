import os
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import queue
import numpy as np
from PIL import Image, ImageTk

from Func_VejrData import hent_vejrdata

class obs_plan:
    def __init__(self):
        self.satellites = []
        self.occupied_time_slots = []
    
    def add_satellite(self, satellite_dict):
        """Tilføjer en satelit til observationsplanen med tidsoverlap-kontrol"""
        # Konverter til datetime for korrekt sammenligning
        start_str = satellite_dict['StartTime']
        end_str = satellite_dict['EndTime']
        
        try:
            start_time = datetime.strptime(start_str, '%H:%M:%S')
            end_time = datetime.strptime(end_str, '%H:%M:%S')
            
            # Hvis EndTime < StartTime, antag det er næste dag
            if end_time < start_time:
                end_time = end_time.replace(day=end_time.day + 1)
        except ValueError:
            raise ValueError(f"Ugyldigt tidsformat: {start_str} eller {end_str}. Forventet format: HH:MM:SS")
        
        occupied_slot = (start_time, end_time)
        
        # Tjek om tidsrummet er ledigt
        for slot in self.occupied_time_slots:
            if not (end_time <= slot[0] or start_time >= slot[1]):
                raise ValueError(
                    f"Tidsrummet {start_str}-{end_str} overlapper med eksisterende observation "
                    f"{slot[0].strftime('%H:%M:%S')}-{slot[1].strftime('%H:%M:%S')} "
                    f"for satelit '{self.satellites[self.occupied_time_slots.index(slot)]['SatName']}'"
                )
        
        self.occupied_time_slots.append(occupied_slot)
        self.satellites.append(satellite_dict)
    
    def remove_satellite(self, index):
        """Fjerner satelit fra planen ud fra indeksnummer"""
        if 0 <= index < len(self.satellites):
            self.satellites.pop(index)
            self.occupied_time_slots.pop(index)
            return True
        return False
    
    def remove_satellite_by_name(self, satellite_name):
        """Fjerner satelit fra planen ud fra navn"""
        for i, sat in enumerate(self.satellites):
            if sat['SatName'] == satellite_name:
                self.remove_satellite(i)
                return True
        return False
    
    def get_satellites_sorted(self):
        """Returnerer satelitter sorteret efter starttid"""
        paired = list(zip(self.satellites, self.occupied_time_slots))
        paired.sort(key=lambda x: x[1][0])  # Sortér efter starttid
        return [sat for sat, _ in paired]
    
    def get_plan_summary(self):
        """Returnerer samlet planinfo"""
        sorted_sats = self.get_satellites_sorted()
        summary = f"Observationsplan ({len(self.satellites)} satelitter):\n"
        for i, sat in enumerate(sorted_sats, 1):
            summary += f"{i}. {sat['SatName']} ({sat['NORAD']}) - {sat['StartTime']} til {sat['EndTime']}\n"
        return summary
    
    def plot_plan(self):
        """Plotter observationsplanen som Gantt chart"""
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        
        if not self.satellites:
            print("Ingen satelitter i planen - kan ikke plotte")
            return
        
        fig, ax = plt.subplots(figsize=(14, 6))
        
        # Sorter satellitter efter starttid
        sorted_sats = self.get_satellites_sorted()
        
        # Farver til hver satelit
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8', 
                  '#F7DC6F', '#BB8FCE', '#85C1E2', '#F8B88B', '#52C0A2']
        
        y_labels = []
        
        for i, sat in enumerate(sorted_sats):
            start = datetime.strptime(sat['StartTime'], '%H:%M:%S')
            end = datetime.strptime(sat['EndTime'], '%H:%M:%S')
            
            # Hvis EndTime < StartTime, næste dag
            if end < start:
                end = end.replace(day=end.day + 1)
            
            # Beregn varighed i timer
            duration = (end - start).total_seconds() / 3600
            
            # Plot som vandret bar
            color = colors[i % len(colors)]
            ax.barh(i, duration, left=start, height=0.6, 
                   label=sat['SatName'], color=color, alpha=0.85, edgecolor='black', linewidth=1.5)
            
            # Tilføj tekst midt i baren
            mid_time = start + (end - start) / 2
            ax.text(mid_time, i, f"{sat['SatName']}\n({sat['NORAD']})", 
                   ha='center', va='center', fontsize=9, fontweight='bold', color='white')
            
            y_labels.append(f"{sat['SatName']}")
        
        # Formatér X-aksen
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=5))
        
        # Opsætning
        ax.set_yticks(range(len(sorted_sats)))
        ax.set_yticklabels(y_labels, fontsize=10)
        ax.set_xlabel('Tid (HH:MM:SS)', fontsize=11, fontweight='bold')
        ax.set_ylabel('Satelitter', fontsize=11, fontweight='bold')
        ax.set_title('Observationsplan - Gantt Chart', fontsize=13, fontweight='bold', pad=20)
        
        # Roter X-aksen labels for bedre læsning
        plt.xticks(rotation=45, ha='right')
        
        # Grid for bedre læsning
        ax.grid(True, alpha=0.3, axis='x', linestyle='--')
        
        # Tilføj information
        info_text = f"Total satelitter: {len(self.satellites)}\n"
        info_text += f"Første observation: {sorted_sats[0]['StartTime']}\n"
        info_text += f"Sidste observation: {sorted_sats[-1]['EndTime']}"
        ax.text(0.02, 0.98, info_text, transform=ax.transAxes, 
               fontsize=9, verticalalignment='top',
               bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        plt.tight_layout()
        plt.show()
    
    def print_plan_timeline(self):
        """Printer plan som ASCII timeline"""
        if not self.satellites:
            print("Ingen satelitter i planen")
            return
        
        sorted_sats = self.get_satellites_sorted()
        
        print("\n" + "="*80)
        print("OBSERVATIONSPLAN TIMELINE".center(80))
        print("="*80)
        
        for idx, sat in enumerate(sorted_sats, 1):
            print(f"\n{idx}. {sat['SatName'].upper()}")
            print(f"   ⏰ START:    {sat['StartTime']}")
            print(f"   ⏰ SLUT:     {sat['EndTime']}")
            print(f"   🛰️  NORAD:    {sat['NORAD']}")
            if 'HiAlt' in sat:
                print(f"   📊 Maks Elev: {sat['HiAlt']}")
        
        print("\n" + "="*80 + "\n")
    
    def plot_plan_canvas(self, canvas):
        """Tegner observationsplanen som Gantt chart på Tkinter Canvas"""
        import tkinter as tk
        
        if not self.satellites:
            canvas.delete("all")
            canvas.create_text(400, 200, text="Ingen satelitter i planen", 
                             font=("Arial", 14), fill="gray")
            return
        
        # Ryd canvas
        canvas.delete("all")
        
        # Canvas dimensioner
        canvas_width = canvas.winfo_width()
        canvas_height = canvas.winfo_height()
        
        if canvas_width <= 1:
            canvas_width = 1000
        if canvas_height <= 1:
            canvas_height = 400
        
        # Layout
        left_margin = 150
        right_margin = 20
        top_margin = 50
        bottom_margin = 50
        bar_height = 25
        
        sorted_sats = self.get_satellites_sorted()
        
        # Beregn tid-range
        first_time = datetime.strptime(sorted_sats[0]['StartTime'], '%H:%M:%S')
        last_sat = sorted_sats[-1]
        last_time = datetime.strptime(last_sat['EndTime'], '%H:%M:%S')
        if last_time < first_time:
            last_time = last_time.replace(day=last_time.day + 1)
        
        time_range = (last_time - first_time).total_seconds()
        plot_width = canvas_width - left_margin - right_margin
        
        # Farver
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8', 
                  '#F7DC6F', '#BB8FCE', '#85C1E2', '#F8B88B', '#52C0A2']
        
        # Tegn X-akse (tider)
        num_ticks = 7
        for i in range(num_ticks):
            tick_time = first_time + (last_time - first_time) * i / (num_ticks - 1)
            x_pos = left_margin + (plot_width * i / (num_ticks - 1))
            time_str = tick_time.strftime('%H:%M:%S')
            canvas.create_line(x_pos, canvas_height - bottom_margin, 
                             x_pos, canvas_height - bottom_margin + 5, fill="black")
            canvas.create_text(x_pos, canvas_height - bottom_margin + 20, 
                             text=time_str, font=("Arial", 8))
        
        # Tegn satellitter
        for idx, sat in enumerate(sorted_sats):
            y_pos = top_margin + idx * (bar_height + 5)
            
            start = datetime.strptime(sat['StartTime'], '%H:%M:%S')
            end = datetime.strptime(sat['EndTime'], '%H:%M:%S')
            if end < start:
                end = end.replace(day=end.day + 1)
            
            # Beregn pixel-position
            start_offset = (start - first_time).total_seconds()
            end_offset = (end - first_time).total_seconds()
            
            x1 = left_margin + (start_offset / time_range) * plot_width
            x2 = left_margin + (end_offset / time_range) * plot_width
            y1 = y_pos
            y2 = y_pos + bar_height
            
            # Tegn bar
            color = colors[idx % len(colors)]
            canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="black", width=2)
            
            # Tegn tekst
            mid_x = (x1 + x2) / 2
            mid_y = (y1 + y2) / 2
            canvas.create_text(mid_x, mid_y, text=f"{sat['SatName']}\n({sat['NORAD']})", 
                             font=("Arial", 9, "bold"), fill="white")
            
            # Satelitnavn på venstre side
            canvas.create_text(left_margin - 10, mid_y, text=sat['SatName'][:15], 
                             font=("Arial", 9), anchor="e", fill="black")
        
        # Tegn titler
        canvas.create_text(canvas_width / 2, 20, text="Observationsplan - Gantt Chart", 
                         font=("Arial", 12, "bold"))
        canvas.create_text(left_margin - 10, top_margin - 20, text="Satelitter:", 
                         font=("Arial", 10, "bold"), anchor="e")
    
    def start_obsplan(self):
        """Starter observationsplanen"""
        pass


class ObservationMonitor:
    """Klasse til at monitorere live observation data"""
    def __init__(self):
        self.data_queue = queue.Queue()
        self.window = None
        self.image_label = None
        self.is_running = False
    
    def create_monitor_window(self):
        """Opretter monitoring popup vinduet"""
        self.window = tk.Toplevel()
        self.window.title("Live Observation Monitor")
        self.window.geometry("1000x700")
        self.window.resizable(True, True)
        
        # Hovedcontainer
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Øverst: Satelit info
        sat_frame = ttk.LabelFrame(main_frame, text="Satelit Info")
        sat_frame.pack(fill='x', pady=(0, 10))
        
        self.sat_info_label = ttk.Label(sat_frame, text="", font=("Arial", 11, "bold"))
        self.sat_info_label.pack(pady=5)
        
        # Middle row: Billede + Status
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill='both', expand=True, pady=(0, 10))
        content_frame.columnconfigure(0, weight=1)
        content_frame.columnconfigure(1, weight=1)
        
        # Venstre: Billede
        image_frame = ttk.LabelFrame(content_frame, text="Live Image")
        image_frame.grid(row=0, column=0, sticky='nsew', padx=(0, 5))
        
        self.image_label = ttk.Label(image_frame, text="Venter på billede...", font=("Arial", 10))
        self.image_label.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Højre: Status info
        status_frame = ttk.LabelFrame(content_frame, text="System Status")
        status_frame.grid(row=0, column=1, sticky='nsew', padx=(5, 0))
        
        # Working on
        working_frame = ttk.LabelFrame(status_frame, text="Aktuel Operation")
        working_frame.pack(fill='x', pady=(0, 10))
        self.working_label = ttk.Label(working_frame, text="", wraplength=300, justify='left')
        self.working_label.pack(padx=5, pady=5)
        
        # Mount status
        mount_frame = ttk.LabelFrame(status_frame, text="Mount Status")
        mount_frame.pack(fill='x', pady=(0, 10))
        self.mount_connected_label = self.create_status_label(mount_frame, "Connected: ")
        self.mount_slewing_label = self.create_status_label(mount_frame, "Slewing: ")
        self.mount_tracking_label = self.create_status_label(mount_frame, "Tracking: ")
        
        # Camera status
        camera_frame = ttk.LabelFrame(status_frame, text="Camera Status")
        camera_frame.pack(fill='x', pady=(0, 10))
        self.camera_connected_label = self.create_status_label(camera_frame, "Connected: ")
        
        # Weather data
        weather_frame = ttk.LabelFrame(status_frame, text="Weather Data")
        weather_frame.pack(fill='x')
        self.clouds_label = self.create_status_label(weather_frame, "Clouds: ")
        self.temp_label = self.create_status_label(weather_frame, "Temp: ")
        self.wind_label = self.create_status_label(weather_frame, "Wind: ")
        self.light_label = self.create_status_label(weather_frame, "Light: ")
        self.hum_label = self.create_status_label(weather_frame, "Humidity: ")
        
        self.is_running = True
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def create_status_label(self, parent, text):
        """Hjælpefunktion til at lave statuslabels"""
        frame = ttk.Frame(parent)
        frame.pack(fill='x', padx=5, pady=2)
        label = ttk.Label(frame, text=text + "---", font=("Arial", 9))
        label.pack(side='left')
        return label
    
    def update_monitor(self, image_data=None, sat_name=None, sat_time=None, working_on=None,
                      vejrdata=None, mount_status=None, camera_connected=None):
        """Opdaterer monitoring vinduet med nye data"""
        if not self.is_running or not self.window:
            return
        
        try:
            # Opdater satelit info
            if sat_name and sat_time:
                self.sat_info_label.config(text=f"🛰️ {sat_name} | ⏰ {sat_time}")
            
            # Opdater billede
            if image_data is not None:
                self.update_image_display(image_data)
            
            # Opdater working on
            if working_on:
                self.working_label.config(text=working_on)
            
            # Opdater weather data
            if vejrdata:
                self.update_weather_display(vejrdata)
            
            # Opdater mount status
            if mount_status:
                self.update_mount_display(mount_status)
            
            # Opdater camera status
            if camera_connected is not None:
                color = "green" if camera_connected else "red"
                status_text = "✓" if camera_connected else "✗"
                self.camera_connected_label.config(
                    text=f"Connected: {status_text}",
                    foreground=color
                )
            
            self.window.update_idletasks()
        except Exception as e:
            print(f"Monitor update error: {e}")
    
    def update_image_display(self, image_data):
        """Viser downscalet billede"""
        try:
            if image_data is None or image_data.size == 0:
                return
            
            # Konverter numpy array til PIL Image
            if isinstance(image_data, np.ndarray):
                # Handle 2D grayscale
                if len(image_data.shape) == 2:
                    # Normalize to 0-255
                    img_min = image_data.min()
                    img_max = image_data.max()
                    if img_max > img_min:
                        image_data = ((image_data - img_min) / (img_max - img_min) * 255).astype(np.uint8)
                    else:
                        image_data = image_data.astype(np.uint8)
                    img = Image.fromarray(image_data, mode='L')
                else:
                    img = Image.fromarray(image_data.astype(np.uint8))
            else:
                img = image_data
            
            # Downscale 4x
            new_size = (img.width // 4, img.height // 4)
            img = img.resize(new_size, Image.LANCZOS)
            
            # Konverter til PhotoImage
            photo = ImageTk.PhotoImage(img)
            self.image_label.config(image=photo, text="")
            self.image_label.image = photo  # Keep a reference!
        except Exception as e:
            print(f"Image display error: {e}")
    
    def update_weather_display(self, vejrdata):
        """Opdaterer vejrdata display med farver"""
        try:
            clouds = vejrdata.get('clouds', 0)
            clouds_safe = vejrdata.get('cloudsSafe', 0)
            self.clouds_label.config(
                text=f"Clouds: {clouds:.1f}°C",
                foreground=self.get_safe_color(clouds_safe)
            )
            
            temp = vejrdata.get('temp', 0)
            self.temp_label.config(text=f"Temp: {temp:.1f}°C")
            
            wind = vejrdata.get('wind', 0)
            wind_safe = vejrdata.get('windSafe', 0)
            self.wind_label.config(
                text=f"Wind: {wind:.1f} m/s",
                foreground=self.get_safe_color(wind_safe)
            )
            
            light = vejrdata.get('lightmpsas', 0)
            light_safe = vejrdata.get('lightSafe', 0)
            self.light_label.config(
                text=f"Light: {light:.2f} mag/arcsec²",
                foreground=self.get_safe_color(light_safe)
            )
            
            hum = vejrdata.get('hum', 0)
            hum_safe = vejrdata.get('humSafe', 0)
            self.hum_label.config(
                text=f"Humidity: {hum:.0f}%",
                foreground=self.get_safe_color(hum_safe)
            )
        except Exception as e:
            print(f"Weather display error: {e}")
    
    def update_mount_display(self, mount_status):
        """Opdaterer mount status display"""
        try:
            is_connected = mount_status.mount.is_connected
            is_slewing = mount_status.mount.is_slewing
            is_tracking = mount_status.mount.is_tracking
            
            self.mount_connected_label.config(
                text=f"Connected: {'✓' if is_connected else '✗'}",
                foreground="green" if is_connected else "red"
            )
            
            self.mount_slewing_label.config(
                text=f"Slewing: {'✓' if is_slewing else '✗'}",
                foreground="green" if is_slewing else "red"
            )
            
            self.mount_tracking_label.config(
                text=f"Tracking: {'✓' if is_tracking else '✗'}",
                foreground="green" if is_tracking else "red"
            )
        except Exception as e:
            print(f"Mount display error: {e}")
    
    def get_safe_color(self, safe_value):
        """Returnerer farve baseret på Safe værdi (1=grøn, 2=rød)"""
        if safe_value == 1:
            return "green"
        elif safe_value == 2:
            return "red"
        else:
            return "gray"
    
    def on_closing(self):
        """Lukker monitoring vinduet"""
        self.is_running = False
        if self.window:
            self.window.destroy()
            self.window = None


def create_plan_observations_tab(self, notebook):
    """Opretter Plan Observations fanen"""
    plan_frame = ttk.Frame(notebook)
    notebook.add(plan_frame, text="Plan Observations")
    
    # Opret obs_plan instans hvis den ikke allerede findes
    if not hasattr(self, 'observation_plan'):
        self.observation_plan = obs_plan()
    
    # Hovedcontainer
    main_container = ttk.Frame(plan_frame)
    main_container.pack(fill='both', expand=True, padx=10, pady=10)
    
    # Øvre sektion med kontrol-knapper
    control_frame = ttk.LabelFrame(main_container, text="Kontrolpanel")
    control_frame.pack(fill='x', pady=(0, 10))
    
    button_frame = ttk.Frame(control_frame)
    button_frame.pack(pady=5)
    
    ttk.Button(button_frame, text="Hent Satellit", 
              command=lambda: hent_satellit_til_plan(self)).pack(side='left', padx=5)
    
    self.start_plan_btn = ttk.Button(button_frame, text="Start Plan", 
                                     command=lambda: start_observation_plan(self))
    self.start_plan_btn.pack(side='left', padx=5)
    
    self.stop_plan_btn = ttk.Button(button_frame, text="Stop Plan", 
                                    command=lambda: stop_observation_plan(self), 
                                    state='disabled')
    self.stop_plan_btn.pack(side='left', padx=5)
    
    # Destinationsmappen sektion
    dest_frame = ttk.LabelFrame(main_container, text="Destinationsmappe")
    dest_frame.pack(fill='x', pady=(0, 10))
    
    dest_button_frame = ttk.Frame(dest_frame)
    dest_button_frame.pack(pady=5, padx=5)
    
    self.plan_destination_entry = ttk.Entry(dest_button_frame, width=50)
    self.plan_destination_entry.pack(side='left', padx=5)
    self.plan_destination_entry.insert(0, os.getcwd())
    
    ttk.Button(dest_button_frame, text="Gennemse", 
              command=lambda: browse_plan_destination(self)).pack(side='left', padx=5)
    
    # Canvas til Gantt chart
    canvas_frame = ttk.LabelFrame(main_container, text="Observationsplan - Gantt Chart")
    canvas_frame.pack(fill='both', expand=True, pady=(0, 10))
    
    self.plan_canvas = tk.Canvas(canvas_frame, bg='white', height=300)
    scrollbar = ttk.Scrollbar(canvas_frame, orient='vertical', command=self.plan_canvas.yview)
    self.plan_canvas.configure(yscrollcommand=scrollbar.set)
    
    scrollbar.pack(side='right', fill='y')
    self.plan_canvas.pack(side='left', fill='both', expand=True)
    
    # Log-sektion
    log_frame = ttk.LabelFrame(main_container, text="Status Log")
    log_frame.pack(fill='x')
    
    self.plan_log_text = tk.Text(log_frame, height=5, wrap='word')
    log_scrollbar = ttk.Scrollbar(log_frame, orient='vertical', command=self.plan_log_text.yview)
    self.plan_log_text.configure(yscrollcommand=log_scrollbar.set)
    
    log_scrollbar.pack(side='right', fill='y')
    self.plan_log_text.pack(side='left', fill='both', expand=True, padx=5, pady=5)
    
    self.plan_log_text.insert(tk.END, "Plan Observations log started...\n")
    
    # Flag for at stoppe planen
    self.stop_plan_flag = False
    
    # Monitoring vindue
    if not hasattr(self, 'observation_monitor'):
        self.observation_monitor = ObservationMonitor()


def browse_plan_destination(self):
    """Vælger destinationsmappe for planen"""
    import tkinter.filedialog as filedialog
    directory = filedialog.askdirectory(title="Vælg destinationsmappe for observationsfiler")
    if directory:
        self.plan_destination_entry.delete(0, tk.END)
        self.plan_destination_entry.insert(0, directory)
        log_msg = f"Destinationsmapp ændret til: {directory}\n"
        self.plan_log_text.insert(tk.END, log_msg)
        self.plan_log_text.see(tk.END)


def hent_satellit_til_plan(self):
    """Henter den valgte satellit fra satelitlisten til planen"""
    try:
        # Tjek om satellite_tree findes
        if not hasattr(self, 'satellite_tree'):
            messagebox.showwarning("Fejl", "Gå til 'Hent Satelitlister' fanen først og få satellitlisten")
            return
        
        selection = self.satellite_tree.selection()
        if not selection:
            messagebox.showwarning("Ingen valg", "Vælg venligst en satelit fra 'Hent Satelitlister' fanen")
            return
        
        item = selection[0]
        values = self.satellite_tree.item(item, 'values')
        
        # Udtræk satellit information - samme struktur som Tracking
        sat = {
            'SatName': values[0],
            'NORAD': values[1],
            'StartTime': values[2],
            'EndTime': values[4],
            'TLE1': self.get_full_tle_from_selection(item)[0],
            'TLE2': self.get_full_tle_from_selection(item)[1]
        }
        
        # Åbn dialog med satellitoplysninger
        add_satellite_to_plan_dialog(self, sat)
        
    except Exception as e:
        messagebox.showerror("Fejl", f"Kunne ikke hente satellit: {str(e)}")


def add_satellite_to_plan_dialog(self, sat):
    """Åbner dialog til at tilføje satelit til planen"""
    
    # Opret popup vindue
    popup = tk.Toplevel(self.root)
    popup.title("Tilføj Satelit til Plan")
    popup.geometry("500x350")
    popup.resizable(False, False)
    popup.grab_set()  # Modal dialog
    
    # Satelit info
    info_label = ttk.Label(popup, text=f"Satelit: {sat['SatName']} (NORAD: {sat['NORAD']})", 
                          font=("Arial", 10, "bold"))
    info_label.pack(pady=10)
    
    # Parameter grid
    params_frame = ttk.Frame(popup)
    params_frame.pack(fill='both', expand=True, padx=10, pady=10)
    
    # Binning
    ttk.Label(params_frame, text="Binning:").grid(row=0, column=0, sticky='w', pady=5)
    binning_var = tk.IntVar(value=4)
    ttk.Spinbox(params_frame, from_=1, to=16, textvariable=binning_var, width=10).grid(row=0, column=1, sticky='w')
    
    # Gain
    ttk.Label(params_frame, text="Gain:").grid(row=1, column=0, sticky='w', pady=5)
    gain_var = tk.IntVar(value=1)
    ttk.Spinbox(params_frame, from_=0, to=1000, textvariable=gain_var, width=10).grid(row=1, column=1, sticky='w')
    
    # Exposure Time
    ttk.Label(params_frame, text="Exposure Time (sek):").grid(row=2, column=0, sticky='w', pady=5)
    exp_var = tk.DoubleVar(value=1.0)
    ttk.Entry(params_frame, textvariable=exp_var, width=10).grid(row=2, column=1, sticky='w')
    
    # Start Time
    ttk.Label(params_frame, text="Start Tid (HH:MM:SS):").grid(row=3, column=0, sticky='w', pady=5)
    start_var = tk.StringVar(value=sat['StartTime'])
    ttk.Entry(params_frame, textvariable=start_var, width=10).grid(row=3, column=1, sticky='w')
    
    # End Time
    ttk.Label(params_frame, text="Slut Tid (HH:MM:SS):").grid(row=4, column=0, sticky='w', pady=5)
    end_var = tk.StringVar(value=sat['EndTime'])
    ttk.Entry(params_frame, textvariable=end_var, width=10).grid(row=4, column=1, sticky='w')
    
    # Buttons
    button_frame = ttk.Frame(popup)
    button_frame.pack(pady=10)
    
    def accept():
        try:
            # Opret opdateret satelit dict
            updated_sat = sat.copy()
            updated_sat['StartTime'] = start_var.get()
            updated_sat['EndTime'] = end_var.get()
            updated_sat['Binning'] = binning_var.get()
            updated_sat['Gain'] = gain_var.get()
            updated_sat['ExposureTime'] = exp_var.get()
            
            # Tilføj til plan
            self.observation_plan.add_satellite(updated_sat)
            
            # Opdater canvas
            self.observation_plan.plot_plan_canvas(self.plan_canvas)
            
            # Log
            log_message = f"✓ {updated_sat['SatName']} tilføjet til plan\n"
            self.plan_log_text.insert(tk.END, log_message)
            self.plan_log_text.see(tk.END)
            
            messagebox.showinfo("Tilføjet", f"{updated_sat['SatName']} tilføjet til observationsplanen")
            popup.destroy()
        except ValueError as e:
            messagebox.showerror("Fejl", str(e))
    
    def cancel():
        popup.destroy()
    
    ttk.Button(button_frame, text="Accept", command=accept).pack(side='left', padx=5)
    ttk.Button(button_frame, text="Cancel", command=cancel).pack(side='left', padx=5)


def start_observation_plan(self):
    """Starter observation planen"""
    if not self.observation_plan.satellites:
        messagebox.showwarning("Tom plan", "Tilføj satellitter til planen først")
        return
    
    # Aktiver Stop-knap, deaktiver Start-knap
    self.start_plan_btn.config(state='disabled')
    self.stop_plan_btn.config(state='normal')
    self.stop_plan_flag = False
    
    # Åbn monitoring vindue
    self.observation_monitor.create_monitor_window()
    
    # Kørt i separat tråd
    threading.Thread(target=run_observation_plan, args=(self,), daemon=True).start()


def stop_observation_plan(self):
    """Stopper observation planen"""
    self.stop_plan_flag = True
    log_msg = "⊗ Stop signal sendt til planen...\n"
    self.plan_log_text.insert(tk.END, log_msg)
    self.plan_log_text.see(tk.END)


def run_observation_plan(self):
    """Kører observation planen sekventielt"""
    import time
    
    try:
        sorted_sats = self.observation_plan.get_satellites_sorted()
        total = len(sorted_sats)
        
        log_msg = f"\n{'='*60}\n▶ STARTER OBSERVATIONSPLAN ({total} satellitter)\n{'='*60}\n"
        self.plan_log_text.insert(tk.END, log_msg)
        self.plan_log_text.see(tk.END)
        self.root.update()
        
        for idx, sat in enumerate(sorted_sats, 1):
            if self.stop_plan_flag:
                log_msg = "⊗ Plan stoppet af bruger\n"
                self.plan_log_text.insert(tk.END, log_msg)
                self.plan_log_text.see(tk.END)
                break
            
            try:
                log_msg = f"\n[{idx}/{total}] Starter: {sat['SatName']} ({sat['NORAD']})\n"
                log_msg += f"  Tid: {sat['StartTime']} - {sat['EndTime']}\n"
                log_msg += f"  Binning: {sat.get('Binning', 4)}, Gain: {sat.get('Gain', 100)}\n"
                self.plan_log_text.insert(tk.END, log_msg)
                self.plan_log_text.see(tk.END)
                self.root.update()
                
                # Konverter tider til Unix timestamps
                from datetime import datetime, timedelta
                now = datetime.now()
                start_time_obj = datetime.strptime(sat['StartTime'], '%H:%M:%S').replace(
                    year=now.year, month=now.month, day=now.day)
                end_time_obj = datetime.strptime(sat['EndTime'], '%H:%M:%S').replace(
                    year=now.year, month=now.month, day=now.day)
                
                # Hvis end < start, næste dag
                if end_time_obj < start_time_obj:
                    end_time_obj += timedelta(days=1)
                
                start_timestamp = start_time_obj.timestamp()
                end_timestamp = end_time_obj.timestamp()
                
                # Hent parametre
                binning = sat.get('Binning', 4)
                gain = sat.get('Gain', 100)
                exposure = sat.get('ExposureTime', 2.0)
                dir_folder = self.plan_destination_entry.get()
                
                # Kald Tracking_obs_plan
                Tracking_obs_plan(
                    binning=binning,
                    gain=gain,
                    TLE=[sat['SatName'], sat['TLE1'], sat['TLE2']],
                    start_time=start_timestamp,
                    end_time=end_timestamp,
                    dir_to_headfolder=dir_folder,
                    NORADID=sat['NORAD'],
                    exposure_time=exposure,
                    monitor=self.observation_monitor,
                    sat_name=sat['SatName'],
                    sat_time=f"{sat['StartTime']} - {sat['EndTime']}"
                )
                
                log_msg = f"  ✓ {sat['SatName']} completed\n"
                self.plan_log_text.insert(tk.END, log_msg)
                self.plan_log_text.see(tk.END)
                self.root.update()
                
            except Exception as e:
                log_msg = f"  ✗ Fejl: {str(e)}\n  → Springer til næste satelit...\n"
                self.plan_log_text.insert(tk.END, log_msg)
                self.plan_log_text.see(tk.END)
                self.root.update()
                continue
        
        # Plan færdig
        log_msg = f"\n{'='*60}\n✓ OBSERVATIONSPLAN FÆRDIG\n{'='*60}\n"
        self.plan_log_text.insert(tk.END, log_msg)
        self.plan_log_text.see(tk.END)
        
    except Exception as e:
        log_msg = f"\n✗ PLAN-FEJL: {str(e)}\n"
        self.plan_log_text.insert(tk.END, log_msg)
        self.plan_log_text.see(tk.END)
    
    finally:
        # Genaktiver knapper
        self.start_plan_btn.config(state='normal')
        self.stop_plan_btn.config(state='disabled')
        self.root.update()


camera_connected = False

def Tracking_obs_plan(binning, gain, TLE, start_time, end_time, dir_to_headfolder, NORADID, exposure_time, 
                     monitor=None, sat_name=None, sat_time=None):
    #vent til start time
    import time
    current_time = time.time()
    wait_seconds = start_time - current_time
    working_on = "Waiting for start time - " + TLE[0]
    if monitor:
        monitor.update_monitor(working_on=working_on)
    if wait_seconds > 0:
        time.sleep(wait_seconds)
    

    #Lav destination for filer
    dir_to_subfolder = os.path.join(dir_to_headfolder, NORADID + TLE[0]) + os.sep
    #Connect Camera
    working_on = "connecting camera - " + TLE[0]
    from moravian_camera_official import MoravianCameraOfficial
    global camera_connected
    try:
        camera = MoravianCameraOfficial()
        camera.connect()
        camera_connected = True
    except Exception as e:
        print(f"Fejl ved kamera-forbindelse: {e}")
        raise

    #Set Kamera binning
    camera.set_binning(binning,binning)

    #set Gain
    camera.set_gain(gain)

    #Find antallet af filtrer
    n_filters = camera.get_filter_count()

    #Connect Mount
    working_on = "connecting mount - " + TLE[0]
    try:
        from Official_PWI4_client import PWI4
    except ImportError as e:
        print(f"Fejl ved PWI4 import: {e}")
        raise
    
    try:
        mount = PWI4()
        mount.mount_connect()
    except Exception as e:
        print(f"Fejl ved mount-forbindelse: {e}")
        raise

    #Enable axis 0 and 1 og disable rotator
    mount.mount_enable(0)
    mount.mount_enable(1)
    mount.rotator_disable()

    #Henter vejrdata
    vejrdata = hent_vejrdata()
    working_on = "starting observation - " + TLE[0]
    #Start Mount Tracking
    mount.mount_follow_tle(TLE[0], TLE[1], TLE[2])
    working_on = "sleewing to satellite track - " + TLE[0]
    #Vent til Slew er færdigt
    wait_for_slew(mount)
    working_on = "taking starfield picture - " + TLE[0]
    if monitor:
        monitor.update_monitor(working_on=working_on)
    #start Tracking af stjerner og tag stjernebillede
    mount.mount_tracking_on()
    take_picture_with_header(
        camera=camera,
        mount=mount,
        exp_time=1.0,
        obstype="stjernehimmel",
        satname=TLE[0],
        tle1=TLE[1],
        tle2=TLE[2],
        norad_id="",
        filename="stjernehimmel" + TLE[0],
        output_dir=dir_to_subfolder,
        vejrdata=vejrdata,
        monitor=monitor,
        sat_name=sat_name,
        sat_time=sat_time
    )


    #Start Tracking igen
    working_on = "starting tracking again - " + TLE[0]
    mount.mount_follow_tle(TLE[0], TLE[1], TLE[2])
    #Vent til Slew er færdigt
    working_on = "waiting for slew to finish - " + TLE[0]
    wait_for_slew(mount)
    
    #henter liste med filtrers navne
    filter_info_list = camera.enumerate_filters()
    # Extract just the filter names for easy access
    filter_names = [f['name'] for f in filter_info_list]
    obs_n = 0
    i_filter = 0

    focus_changed = False
    start_focus = mount.status().focuser.position
    #loop indtil observation er færdig
    while time.time() < end_time:

        #sæt fokus til start fokus + 1300 hvis filter går fra 0->1
        if i_filter == 1:
            mount.focuser_goto(start_focus + 1300)
            focus_changed = True
        elif i_filter == 0:
            mount.focuser_goto(start_focus)
            focus_changed = True
         # skift mellem filtrer efter hver eksponering
        working_on = f"changing to filter {filter_names[i_filter]} - " + TLE[0]
        camera.set_filter(i_filter)
         # Tag Billede og dem header
        
        #hvis vi har ændret fokus, vent på at mount.status().focuser.is_moving er falsk
        if focus_changed:
            working_on = "waiting for focuser to finish moving - " + TLE[0]
            while mount.status().focuser.is_moving:
                time.sleep(0.2)
            focus_changed = False

         #hent vejrdata hver 5 billede

        working_on = f"taking picture {obs_n:03d} with filter {filter_names[i_filter]} - " + TLE[0]
        take_picture_with_header(
            camera=camera,
            mount=mount,
            exp_time=exposure_time,
            obstype="satellite",
            satname=TLE[0],
            tle1=TLE[1],
            tle2=TLE[2],
            norad_id=NORADID,
            filename=f"{obs_n:03d}_" + TLE[0] +"_"+ NORADID + "_" + filter_names[i_filter],
            output_dir=dir_to_subfolder,
            vejrdata=vejrdata,
            monitor=monitor,
            sat_name=sat_name,
            sat_time=sat_time,
            working_on=working_on
        )
        obs_n += 1
        i_filter = (i_filter + 1) % n_filters

    #Home mount
    mount.mount_find_home()

    #disconnect Mount
    mount.mount_disconnect()
    
    #disconnect Camera
    camera.disconnect()
    camera_connected = False

def wait_for_slew(mount):
    import time
    while mount.status().mount.is_slewing:
        time.sleep(0.5)

def take_picture_with_header(camera, mount, exp_time, obstype, satname, tle1, tle2, norad_id, filename, output_dir, vejrdata=None, monitor=None, sat_name=None, sat_time=None, working_on=None):
    import time
    from astropy.io import fits
    from FitsHeader import add_pwi4_data_to_header
    #Noter startstidspunkt
    start_time = time.time()

    camera.start_exposure(exp_time)
    time.sleep(exp_time/2)
    obs_time = time.time()
    mount_status_raw = mount.status().raw
    camera_status = camera.get_camera_info()
    camera.wait_for_image()
    end_time = time.time()
    image_data = camera.read_image()

    # Laver FITS header
    header = fits.Header()
    header['OBSTYPE'] = obstype
    header['SATNAME'] = satname
    header['TLE1'] = tle1
    header['TLE2'] = tle2
    header['NORAD_ID'] = norad_id
    header['DATE-STA'] = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(start_time))
    header['DATE-OBS'] = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(obs_time))
    header['DATE-END'] = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(end_time))

    if vejrdata is not None:
        header['cloud_te'] = vejrdata.get('clouds', float('nan'))
        header['humidity'] = vejrdata.get('hum', float('nan'))
        header['temp'] = vejrdata.get('temp', float('nan'))
        header['Mag_sky'] = vejrdata.get('lightmpsas', float('nan'))
        header['pressure'] = vejrdata.get('abspress', float('nan'))
    
    # Tilføj alle PWI4 data med korrekte key-navne
    header = add_pwi4_data_to_header(header, mount_status_raw)
    
    # Tilføj kamera data
    for key, value in camera_status.items():
        # Undgå at overskrive eksisterende felter og skip komplekse objekter
        if key not in header and not isinstance(value, (list, dict)):
            try:
                header[key] = value
            except (TypeError, ValueError):
                # Skip values that can't be added to FITS header
                pass

    # Save FITS file
    hdu = fits.PrimaryHDU(image_data, header=header)
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, filename + ".fits")
    hdu.writeto(filepath, overwrite=True)
    
    # Opdater monitor med billede og data
    if monitor:
        try:
            camera_connected = True
            monitor.update_monitor(
                image_data=image_data,
                sat_name=sat_name,
                sat_time=sat_time,
                working_on=working_on,
                vejrdata=vejrdata,
                mount_status=mount.status() if hasattr(mount, 'status') else None,
                camera_connected=camera_connected
            )
        except Exception as e:
            print(f"Monitor update error in take_picture: {e}")
