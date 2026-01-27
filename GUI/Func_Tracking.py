"""
Func_Tracking.py - Tracking Observation Tab Functions
Contains UI initialization for tracking observation features
"""

import tkinter as tk
from tkinter import ttk

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
    
    # Test forbindelse knap (binning styres nu fra kameraindstillinger)
    ttk.Button(params_frame, text="Test PlaneWave4 Forbindelse", 
              command=self.test_pw4_connection).grid(row=2, column=0, columnspan=2, pady=10, padx=5)
    
    # Status display
    self.pw4_status_label = ttk.Label(params_frame, text="Status: Ikke testet", foreground='gray')
    self.pw4_status_label.grid(row=3, column=2, columnspan=2, pady=10, padx=5, sticky='w')
    
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
