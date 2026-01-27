"""
Func_Leapfrog.py - LeapFrog Observation Tab Functions
Contains UI initialization for LeapFrog observation features
"""

import tkinter as tk
from tkinter import ttk

# Check for optional dependencies
try:
    import plotly
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

try:
    from pwi4_client import PWI4Client
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
    ttk.Button(button_frame, text="Beregn LeapFrog Data", 
              command=self.calculate_leapfrog_data).pack(side='left', padx=5)
    
    # Satelit info display
    info_frame = ttk.LabelFrame(selection_frame, text="Valgt Satelit Info")
    info_frame.pack(fill='x', pady=5)
    
    self.sat_info_text = tk.Text(info_frame, height=3, wrap='word')
    self.sat_info_text.pack(fill='x', padx=5, pady=5)
    
    # Data tabel sektion (venstre side)
    table_frame = ttk.LabelFrame(left_frame, text="LeapFrog Observationsdata")
    table_frame.pack(fill='both', expand=True, pady=(0, 10))
    
    # Treeview til at vise leapfrog data
    leapfrog_columns = ('DATE-OBS', 'Sat_DEC', 'Sat_RA_Hr', 'Sat_Alt', 'Sat_Az')
    self.leapfrog_tree = ttk.Treeview(table_frame, columns=leapfrog_columns, show='headings', height=10)
    
    # Definer kolonner med optimerede bredder
    column_widths_leapfrog = {
        'DATE-OBS': 160,
        'Sat_DEC': 120,
        'Sat_RA_Hr': 120,
        'Sat_Alt': 100,
        'Sat_Az': 100
    }
    for col in leapfrog_columns:
        self.leapfrog_tree.heading(col, text=col)
        self.leapfrog_tree.column(col, width=column_widths_leapfrog.get(col, 100))
    
    # Scrollbars for leapfrog treeview
    leapfrog_v_scrollbar = ttk.Scrollbar(table_frame, orient='vertical', command=self.leapfrog_tree.yview)
    leapfrog_h_scrollbar = ttk.Scrollbar(table_frame, orient='horizontal', command=self.leapfrog_tree.xview)
    self.leapfrog_tree.configure(yscrollcommand=leapfrog_v_scrollbar.set, xscrollcommand=leapfrog_h_scrollbar.set)
    
    # Pack treeview og scrollbars
    leapfrog_v_scrollbar.pack(side='right', fill='y')
    leapfrog_h_scrollbar.pack(side='bottom', fill='x')
    self.leapfrog_tree.pack(side='left', fill='both', expand=True)
    
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
    self.leapfrog_interval_entry.insert(0, "15.0")
    
    # Kamera timing parametre
    ttk.Label(params_frame, text="Kamera start før (s):").grid(row=2, column=0, sticky='w', padx=5, pady=5)
    self.leapfrog_camera_start_entry = ttk.Entry(params_frame, width=10)
    self.leapfrog_camera_start_entry.grid(row=2, column=1, padx=5, pady=5)
    self.leapfrog_camera_start_entry.insert(0, "2.0")
    
    ttk.Label(params_frame, text="Kamera stop efter (s):").grid(row=2, column=2, sticky='w', padx=5, pady=5)
    self.leapfrog_camera_stop_entry = ttk.Entry(params_frame, width=10)
    self.leapfrog_camera_stop_entry.grid(row=2, column=3, padx=5, pady=5)
    self.leapfrog_camera_stop_entry.insert(0, "2.0")
    
    ttk.Label(params_frame, text="Slew delay (s):").grid(row=3, column=0, sticky='w', padx=5, pady=5)
    self.leapfrog_slew_delay_entry = ttk.Entry(params_frame, width=10)
    self.leapfrog_slew_delay_entry.grid(row=3, column=1, padx=5, pady=5)
    self.leapfrog_slew_delay_entry.insert(0, "0.5")
    
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
