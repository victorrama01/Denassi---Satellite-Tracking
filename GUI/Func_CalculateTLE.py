"""Module for TLE calculation tab functionality"""
import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Optional dependencies
try:
    import orbdtools
    ORBDTOOLS_AVAILABLE = True
except ImportError:
    ORBDTOOLS_AVAILABLE = False


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
