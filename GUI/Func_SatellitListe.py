import tkinter as tk
from tkinter import ttk
from datetime import datetime

def create_satellite_tab(self, notebook):
    """Tab til at hente satelitlister"""
    satellite_frame = ttk.Frame(notebook)
    notebook.add(satellite_frame, text="Hent Satelitlister")
    
    # Hovedcontainer
    main_container = ttk.Frame(satellite_frame)
    main_container.pack(fill='both', expand=True, padx=10, pady=10)
    
    # Øvre sektion med to kolonner
    top_frame = ttk.Frame(main_container)
    top_frame.pack(fill='x', pady=(0, 10))
    
    # Øvre venstre: Input sektion 
    left_frame = ttk.Frame(top_frame)
    left_frame.pack(side='left', fill='both', expand=True, padx=(0, 5))
    
    # Øvre højre: Log sektion
    right_frame = ttk.Frame(top_frame) 
    right_frame.pack(side='right', fill='both', expand=False, padx=(5, 0))
    
    # Sæt en fast bredde på log området (1/3 af vinduet ≈ 400px)
    right_frame.configure(width=400)
    right_frame.pack_propagate(False)
    
    # Input sektion (øvre venstre)
    input_frame = ttk.LabelFrame(left_frame, text="Søgekriterier")
    input_frame.pack(fill='both', expand=True)
    
    # Lokation inputs
    ttk.Label(input_frame, text="Breddegrad:").grid(row=0, column=0, sticky='w', padx=5, pady=5)
    self.lat_entry = ttk.Entry(input_frame, width=15)
    self.lat_entry.grid(row=0, column=1, padx=5, pady=5)
    self.lat_entry.insert(0, "66.996007")
    
    ttk.Label(input_frame, text="Længdegrad:").grid(row=0, column=2, sticky='w', padx=5, pady=5)
    self.lng_entry = ttk.Entry(input_frame, width=15)
    self.lng_entry.grid(row=0, column=3, padx=5, pady=5)
    self.lng_entry.insert(0, "-50.621153")
    
    ttk.Label(input_frame, text="Højde (m):").grid(row=1, column=0, sticky='w', padx=5, pady=5)
    self.ele_entry = ttk.Entry(input_frame, width=15)
    self.ele_entry.grid(row=1, column=1, padx=5, pady=5)
    self.ele_entry.insert(0, "313")
    
    # Dato input
    ttk.Label(input_frame, text="Dato (YYYY-MM-DD):").grid(row=1, column=2, sticky='w', padx=5, pady=5)
    self.date_entry = ttk.Entry(input_frame, width=15)
    self.date_entry.grid(row=1, column=3, padx=5, pady=5)
    self.date_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))
    
    # UTC Offset input
    ttk.Label(input_frame, text="UTC Offset (timer):").grid(row=1, column=4, sticky='w', padx=5, pady=5)
    self.utc_offset_entry = ttk.Entry(input_frame, width=10)
    self.utc_offset_entry.grid(row=1, column=5, padx=5, pady=5)
    self.utc_offset_entry.insert(0, "-2")  # Standard dansk tid
    
    # Periode valg
    ttk.Label(input_frame, text="Periode:").grid(row=2, column=0, sticky='w', padx=5, pady=5)
    self.period_combo = ttk.Combobox(input_frame, values=['morning', 'evening'], state="readonly", width=12)
    self.period_combo.grid(row=2, column=1, padx=5, pady=5)
    self.period_combo.set('evening')
    
    # Space-Track login
    login_frame = ttk.LabelFrame(input_frame, text="Space-Track Login")
    login_frame.grid(row=3, column=0, columnspan=6, sticky='ew', padx=5, pady=5)
    
    ttk.Label(login_frame, text="Username:").grid(row=0, column=0, sticky='w', padx=5, pady=2)
    self.username_entry = ttk.Entry(login_frame, width=25)
    self.username_entry.grid(row=0, column=1, padx=5, pady=2)
    self.username_entry.insert(0, "Sophienlund37@gmail.com")  # Standard brugernavn
    
    ttk.Label(login_frame, text="Password:").grid(row=0, column=2, sticky='w', padx=5, pady=2)
    self.password_entry = ttk.Entry(login_frame, width=25, show="*")
    self.password_entry.grid(row=0, column=3, padx=5, pady=2)
    self.password_entry.insert(0, "Denassi2025ViggoVictor")  # Standard adgangskode
    
    button_frame = ttk.Frame(input_frame)
    button_frame.grid(row=4, column=0, columnspan=6, pady=10)

    ttk.Button(button_frame, text="Hent Fra Internet", command=self.fetch_satellites_threaded).pack(side='left', padx=5)
    ttk.Button(button_frame, text="Åbn CSV-fil", command=self.load_csv_file).pack(side='left', padx=5)
    ttk.Button(button_frame, text="Gem Liste", command=self.save_satellite_list).pack(side='left', padx=5)
    ttk.Button(button_frame, text="Ryd Liste", command=self.clear_satellite_list).pack(side='left', padx=5)

    # Progress bar
    self.progress_var = tk.DoubleVar()
    self.progress_bar = ttk.Progressbar(input_frame, variable=self.progress_var, maximum=100)
    self.progress_bar.grid(row=5, column=0, columnspan=6, sticky='ew', padx=5, pady=5)
    
    # Farvelegenda sektion
    legend_frame = ttk.LabelFrame(input_frame, text="Farvelegenda (opdateres automatisk)")
    legend_frame.grid(row=6, column=0, columnspan=6, sticky='ew', padx=5, pady=5)
    
    ttk.Label(legend_frame, text="🔴 Passeret (EndTime overskredet)", foreground='red').grid(row=0, column=0, sticky='w', padx=5, pady=2)
    ttk.Label(legend_frame, text="🟡 Starter snart (StartTime inden for 5 min)", foreground='orange').grid(row=0, column=1, sticky='w', padx=5, pady=2)
    ttk.Label(legend_frame, text="🟢 Aktiv nu (mellem StartTime og EndTime)", foreground='green').grid(row=0, column=2, sticky='w', padx=5, pady=2)
    
    # Satelit log sektion (øvre højre hjørne)
    satellite_log_frame = ttk.LabelFrame(right_frame, text="Satelit Hentning Log")
    satellite_log_frame.pack(fill='both', expand=True)
    
    # Log text widget med scrollbar
    satellite_log_container = ttk.Frame(satellite_log_frame)
    satellite_log_container.pack(fill='both', expand=True, padx=5, pady=5)
    
    self.satellite_log_text = tk.Text(satellite_log_container, height=8, wrap='word')
    satellite_log_scrollbar = ttk.Scrollbar(satellite_log_container, orient='vertical', command=self.satellite_log_text.yview)
    self.satellite_log_text.configure(yscrollcommand=satellite_log_scrollbar.set)
    
    satellite_log_scrollbar.pack(side='right', fill='y')
    self.satellite_log_text.pack(side='left', fill='both', expand=True)
    
    # Clear log button
    ttk.Button(satellite_log_frame, text="Ryd Log", 
              command=lambda: self.satellite_log_text.delete(1.0, tk.END)).pack(pady=2)
    
    # Tilføj en velkomst besked til satelit loggen
    self.satellite_log_text.insert(tk.END, "Satelit Log startet...\n")
    self.satellite_log_text.insert(tk.END, "Klar til at hente satelitdata.\n\n")
    
    # Resultat sektion (fuld bredde i bunden)
    result_frame = ttk.LabelFrame(main_container, text="Satelitliste (sorteret efter starttid)")
    result_frame.pack(fill='both', expand=True)
    
    # Treeview til at vise resultater
    columns = ('SatName', 'NORAD', 'StartTime', 'HiTime', 'EndTime', 'HiAlt', 'Magnitude', 'TLE1', 'TLE2')
    self.satellite_tree = ttk.Treeview(result_frame, columns=columns, show='headings', height=15)
    
    # Definer kolonner
    column_widths = {'SatName': 150, 'NORAD': 80, 'StartTime': 80, 'HiTime': 80, 
                    'EndTime': 80, 'HiAlt': 60, 'Magnitude': 80, 'TLE1': 200, 'TLE2': 200}
    
    for col in columns:
        self.satellite_tree.heading(col, text=col)
        self.satellite_tree.column(col, width=column_widths.get(col, 100))
    
    # Konfigurer farvetags for treeview
    self.satellite_tree.tag_configure('passed', background='#ffcccc')  # Lyserød for passeret
    self.satellite_tree.tag_configure('starting_soon', background='#ffffcc')  # Lysegul for starter snart
    self.satellite_tree.tag_configure('active', background='#ccffcc')  # Lysegrøn for aktiv
    self.satellite_tree.tag_configure('normal', background='white')  # Normal baggrund
    
    # Scrollbars for treeview
    tree_v_scrollbar = ttk.Scrollbar(result_frame, orient='vertical', command=self.satellite_tree.yview)
    tree_h_scrollbar = ttk.Scrollbar(result_frame, orient='horizontal', command=self.satellite_tree.xview)
    self.satellite_tree.configure(yscrollcommand=tree_v_scrollbar.set, xscrollcommand=tree_h_scrollbar.set)
    
    # Pack treeview og scrollbars
    tree_v_scrollbar.pack(side='right', fill='y')
    tree_h_scrollbar.pack(side='bottom', fill='x')
    self.satellite_tree.pack(side='left', fill='both', expand=True)
    
    # Status label (nederst ved satelitlisten)
    self.status_label = ttk.Label(main_container, text="Klar til at hente satelitdata...")
    self.status_label.pack(pady=5)
