import tkinter as tk
from tkinter import ttk

def create_kameraindstillinger_tab(self, notebook):
    """Tab til kameraindstillinger"""
    kameraindstillinger_frame = ttk.Frame(notebook)
    notebook.add(kameraindstillinger_frame, text="Kameraindstillinger")
    
    # Opret to kolonner: venstre for widgets, højre for log
    main_container = ttk.Frame(kameraindstillinger_frame)
    main_container.pack(fill='both', expand=True, padx=10, pady=10)
    
    left_frame = ttk.Frame(main_container)
    left_frame.pack(side='left', fill='both', expand=True, padx=(0, 5))
    
    right_frame = ttk.Frame(main_container) 
    right_frame.pack(side='right', fill='both', expand=False, padx=(5, 0))
    
    # Kamera kontrol sektion (venstre side)
    camera_frame = ttk.LabelFrame(left_frame, text="Kamera Kontrol (Moravian)")
    camera_frame.pack(fill='x', pady=(0, 10))
    
    # Kamera status og forbindelse
    camera_status_frame = ttk.Frame(camera_frame)
    camera_status_frame.pack(fill='x', padx=5, pady=5)
    
    ttk.Label(camera_status_frame, text="Status:", font=('Arial', 10, 'bold')).pack(side='left')
    self.camera_status_label = ttk.Label(camera_status_frame, text="Ikke tilsluttet", foreground='red')
    self.camera_status_label.pack(side='left', padx=(5, 0))
    
    # Connection knapper
    conn_frame = ttk.Frame(camera_frame)
    conn_frame.pack(fill='x', padx=5, pady=5)
    
    ttk.Button(conn_frame, text="Tilslut Kamera", 
              command=self.connect_camera).pack(side='left', padx=5)
    ttk.Button(conn_frame, text="Afbryd Kamera", 
              command=self.disconnect_camera).pack(side='left', padx=5)
    ttk.Button(conn_frame, text="Opdater Info", 
              command=self.update_camera_info).pack(side='left', padx=5)
    ttk.Button(conn_frame, text="Tag Testbillede", 
              command=self.take_test_image).pack(side='left', padx=5)
    
    # Temperatur visning (kun læsning - ikke styring)
    temp_frame = ttk.LabelFrame(camera_frame, text="Temperatur Visning")
    temp_frame.pack(fill='x', padx=5, pady=5)
    
    temp_display_frame = ttk.Frame(temp_frame)
    temp_display_frame.pack(fill='x', padx=5, pady=5)
    
    ttk.Label(temp_display_frame, text="Nuværende temperatur:").grid(row=0, column=0, sticky='w', padx=5)
    self.current_temp_label = ttk.Label(temp_display_frame, text="N/A", foreground='blue', font=('Arial', 10, 'bold'))
    self.current_temp_label.grid(row=0, column=1, sticky='w', padx=10)
    
    # Info label om ekstern temperaturstyring
    ttk.Label(temp_display_frame, text="Temperaturstyring håndteres af ekstern software", 
             foreground='gray', font=('Arial', 8)).grid(row=1, column=0, columnspan=2, sticky='w', padx=5, pady=(5, 0))
    
    # Gain kontrol
    gain_frame = ttk.LabelFrame(camera_frame, text="Gain Kontrol")
    gain_frame.pack(fill='x', padx=5, pady=5)
    
    gain_control_frame = ttk.Frame(gain_frame)
    gain_control_frame.pack(fill='x', padx=5, pady=5)
    
    ttk.Label(gain_control_frame, text="Gain:").grid(row=0, column=0, sticky='w', padx=5)
    
    # Gain slider
    self.gain_scale = ttk.Scale(gain_control_frame, from_=0, to=100, 
                               variable=self.camera_gain, orient='horizontal', length=200)
    self.gain_scale.grid(row=0, column=1, sticky='ew', padx=5)
    
    # Gain value labels
    self.gain_value_label = ttk.Label(gain_control_frame, text="0")
    self.gain_value_label.grid(row=0, column=2, padx=5)
    
    # Manual gain entry
    ttk.Label(gain_control_frame, text="Manual:").grid(row=0, column=3, sticky='w', padx=(20, 5))
    self.manual_gain_entry = ttk.Entry(gain_control_frame, width=8)
    self.manual_gain_entry.grid(row=0, column=4, padx=5)
    
    ttk.Button(gain_control_frame, text="Sæt Gain", 
              command=self.set_camera_gain).grid(row=0, column=5, padx=10)
    
    gain_control_frame.grid_columnconfigure(1, weight=1)
    
    # Bind slider til label opdatering
    self.gain_scale.configure(command=self.update_gain_label)
    
    # Initialiser gain label med standardværdi
    self.update_gain_label(self.camera_gain.get())
    
    # Binning kontrol
    binning_frame = ttk.LabelFrame(camera_frame, text="Binning Kontrol")
    binning_frame.pack(fill='x', padx=5, pady=5)
    
    binning_control_frame = ttk.Frame(binning_frame)
    binning_control_frame.pack(fill='x', padx=5, pady=5)
    
    ttk.Label(binning_control_frame, text="X-Binning:").grid(row=0, column=0, sticky='w', padx=5)
    x_binning_spinbox = ttk.Spinbox(binning_control_frame, from_=1, to=8, 
                                   textvariable=self.camera_binning_x, width=5)
    x_binning_spinbox.grid(row=0, column=1, padx=5)
    
    ttk.Label(binning_control_frame, text="Y-Binning:").grid(row=0, column=2, sticky='w', padx=(20, 5))
    y_binning_spinbox = ttk.Spinbox(binning_control_frame, from_=1, to=8, 
                                   textvariable=self.camera_binning_y, width=5)
    y_binning_spinbox.grid(row=0, column=3, padx=5)
    
    ttk.Button(binning_control_frame, text="Sæt Binning", 
              command=self.set_camera_binning).grid(row=0, column=4, padx=10)
    
    # Filter kontrol
    filter_frame = ttk.LabelFrame(camera_frame, text="Filter Kontrol")
    filter_frame.pack(fill='x', padx=5, pady=5)
    
    filter_control_frame = ttk.Frame(filter_frame)
    filter_control_frame.pack(fill='x', padx=5, pady=5)
    
    ttk.Label(filter_control_frame, text="Filter:").grid(row=0, column=0, sticky='w', padx=5)
    self.filter_combo = ttk.Combobox(filter_control_frame, textvariable=self.selected_filter, 
                                    state='readonly', width=25)
    self.filter_combo.grid(row=0, column=1, sticky='ew', padx=5)
    
    ttk.Button(filter_control_frame, text="Sæt Filter", 
              command=self.set_camera_filter).grid(row=0, column=2, padx=10)
    
    filter_control_frame.grid_columnconfigure(1, weight=1)
    
    # Kamera log sektion (højre side)
    camera_log_frame = ttk.LabelFrame(right_frame, text="Kamera Log")
    camera_log_frame.pack(fill='both', expand=True)
    
    # Sæt en passende bredde på log området
    right_frame.configure(width=420)
    right_frame.pack_propagate(False)
    
    # Log text widget med scrollbar
    camera_log_container = ttk.Frame(camera_log_frame)
    camera_log_container.pack(fill='both', expand=True, padx=5, pady=5)
    
    self.camera_log_text = tk.Text(camera_log_container, width=52, wrap='word')
    camera_log_scrollbar = ttk.Scrollbar(camera_log_container, orient='vertical', command=self.camera_log_text.yview)
    self.camera_log_text.configure(yscrollcommand=camera_log_scrollbar.set)
    
    camera_log_scrollbar.pack(side='right', fill='y')
    self.camera_log_text.pack(side='left', fill='both', expand=True)
    
    # Clear log button
    ttk.Button(camera_log_frame, text="Ryd Log", 
              command=lambda: self.camera_log_text.delete(1.0, tk.END)).pack(pady=2)
    
    # Tilføj en velkomst besked til kamera loggen
    self.camera_log_text.insert(tk.END, "Kamera Log startet...\n")
    self.camera_log_text.insert(tk.END, "Klar til kamera operationer.\n\n")
