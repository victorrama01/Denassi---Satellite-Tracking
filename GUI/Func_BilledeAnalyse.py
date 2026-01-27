"""
Func_BilledeAnalyse.py - Image Analysis Tab Functions
Contains UI initialization for image analysis features
"""

import tkinter as tk
from tkinter import ttk

# Check for optional dependencies
try:
    from skimage import io, filters, measure
    SKIMAGE_AVAILABLE = True
except ImportError:
    SKIMAGE_AVAILABLE = False


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
