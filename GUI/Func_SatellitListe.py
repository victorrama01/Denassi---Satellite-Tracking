import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime, timedelta
import os
import requests
import pandas as pd
import re
import time
import threading
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# Optional dependencies
try:
    from selenium import webdriver
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

try:
    from webdriver_manager.chrome import ChromeDriverManager
    WEBDRIVER_MANAGER_AVAILABLE = True
except ImportError:
    WEBDRIVER_MANAGER_AVAILABLE = False

# Cache for satcat data (loaded once per session for performance)
_SATCAT_CACHE = None

def get_satcat_filepath():
    """Find satcat.csv relativt fra repo-root"""
    # Start fra denne fil's placering
    current_file = Path(__file__).resolve()
    
    # Gå op til GUI-mappen, så til repo-root
    gui_dir = current_file.parent
    repo_root = gui_dir.parent  # En mappe op fra GUI
    
    satcat_path = repo_root / "Sat_lister" / "satcat.csv"
    
    if not satcat_path.exists():
        raise FileNotFoundError(f"satcat.csv ikke fundet på: {satcat_path}")
    
    return satcat_path

def load_satcat_cache():
    """Hent satcat-data og cache det (kun én gang per session)"""
    global _SATCAT_CACHE
    
    if _SATCAT_CACHE is not None:
        return _SATCAT_CACHE
    
    try:
        satcat_path = get_satcat_filepath()
        # Læs kun de kolonner vi skal bruge for bedre performance
        _SATCAT_CACHE = pd.read_csv(
            satcat_path,
            usecols=['NORAD_CAT_ID', 'OBJECT_TYPE', 'OWNER'],
            dtype={'NORAD_CAT_ID': 'int64', 'OBJECT_TYPE': 'object', 'OWNER': 'object'}
        )
        # Konverter NORAD_CAT_ID til int64 (sikrer matching)
        _SATCAT_CACHE['NORAD_CAT_ID'] = pd.to_numeric(_SATCAT_CACHE['NORAD_CAT_ID'], errors='coerce').astype('Int64')
        
        return _SATCAT_CACHE
    except Exception as e:
        print(f"Advarsel: Kunne ikke loade satcat.csv: {e}")
        return None

def merge_with_satcat(df):
    """Merge satelit-dataframe med satcat data optimeret"""
    if df is None or len(df) == 0:
        return df
    
    try:
        satcat_df = load_satcat_cache()
        
        if satcat_df is None or len(satcat_df) == 0:
            # Hvis satcat ikke kunne loades, tilføj tomme kolonner
            df['OBJECT_TYPE'] = None
            df['OWNER'] = None
            return df
        
        # Merge på NORAD (fra satelit-liste) og NORAD_CAT_ID (fra satcat)
        # Brug left join for at bevare alle satellitter
        norad_col = 'NORAD' if 'NORAD' in df.columns else None
        
        if norad_col:
            df_merged = df.merge(
                satcat_df,
                left_on=norad_col,
                right_on='NORAD_CAT_ID',
                how='left'
            )
            # Drop den duplikerede NORAD_CAT_ID kolonne
            if 'NORAD_CAT_ID' in df_merged.columns:
                df_merged = df_merged.drop(columns=['NORAD_CAT_ID'])
            
            return df_merged
        else:
            # Hvis NORAD ikke findes, tilføj bare tomme kolonner
            df['OBJECT_TYPE'] = None
            df['OWNER'] = None
            return df
            
    except Exception as e:
        print(f"Fejl ved merge med satcat: {e}")
        # Hvis merge fejler, tilføj tomme kolonner
        df['OBJECT_TYPE'] = None
        df['OWNER'] = None
        return df

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
    
    # Dato input
    ttk.Label(input_frame, text="Dato (YYYY-MM-DD):").grid(row=1, column=0, sticky='w', padx=5, pady=5)
    self.date_entry = ttk.Entry(input_frame, width=15)
    self.date_entry.grid(row=1, column=1, padx=5, pady=5)
    self.date_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))
    
    # UTC Offset input
    ttk.Label(input_frame, text="UTC Offset (timer):").grid(row=1, column=2, sticky='w', padx=5, pady=5)
    self.utc_offset_entry = ttk.Entry(input_frame, width=10)
    self.utc_offset_entry.grid(row=1, column=3, padx=5, pady=5)
    self.utc_offset_entry.insert(0, "-2")  # Standard dansk tid
    
    # Space-Track login
    login_frame = ttk.LabelFrame(input_frame, text="Space-Track Login")
    login_frame.grid(row=2, column=0, columnspan=6, sticky='ew', padx=5, pady=5)
    
    ttk.Label(login_frame, text="Username:").grid(row=0, column=0, sticky='w', padx=5, pady=2)
    self.username_entry = ttk.Entry(login_frame, width=25)
    self.username_entry.grid(row=0, column=1, padx=5, pady=2)
    self.username_entry.insert(0, "Sophienlund37@gmail.com")  # Standard brugernavn
    
    ttk.Label(login_frame, text="Password:").grid(row=0, column=2, sticky='w', padx=5, pady=2)
    self.password_entry = ttk.Entry(login_frame, width=25, show="*")
    self.password_entry.grid(row=0, column=3, padx=5, pady=2)
    self.password_entry.insert(0, "Denassi2025ViggoVictor")  # Standard adgangskode
    
    button_frame = ttk.Frame(input_frame)
    button_frame.grid(row=3, column=0, columnspan=6, pady=10)

    ttk.Button(button_frame, text="Hent Fra Internet", command=self.fetch_satellites_threaded).pack(side='left', padx=5)
    ttk.Button(button_frame, text="Åbn CSV-fil", command=self.load_csv_file).pack(side='left', padx=5)
    ttk.Button(button_frame, text="Gem Liste", command=self.save_satellite_list).pack(side='left', padx=5)
    ttk.Button(button_frame, text="Ryd Liste", command=self.clear_satellite_list).pack(side='left', padx=5)
    ttk.Button(button_frame, text="Filter", command=self.open_filter_dialog).pack(side='left', padx=5)

    # Progress bar
    self.progress_var = tk.DoubleVar()
    self.progress_bar = ttk.Progressbar(input_frame, variable=self.progress_var, maximum=100)
    self.progress_bar.grid(row=4, column=0, columnspan=6, sticky='ew', padx=5, pady=5)
    
    # Farvelegenda sektion
    legend_frame = ttk.LabelFrame(input_frame, text="Farvelegenda (opdateres automatisk)")
    legend_frame.grid(row=5, column=0, columnspan=6, sticky='ew', padx=5, pady=5)
    
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
    result_frame = ttk.LabelFrame(main_container, text="")
    result_frame.pack(fill='both', expand=True)
    
    # Warning label over treeviewet
    self.satellite_list_warning = ttk.Label(result_frame, text="", foreground='red', font=('TkDefaultFont', 10, 'bold'))
    self.satellite_list_warning.pack(pady=5)
    
    # Container for treeview og scrollbars (fylder mest af resultatet)
    tree_container = ttk.Frame(result_frame)
    tree_container.pack(fill='both', expand=True, pady=(5, 0))
    
    # Treeview til at vise resultater
    columns = ('SatName', 'NORAD', 'StartTime', 'StartAlt', 'StartAz', 'HiTime', 'HiAlt', 'HiAz', 
               'EndTime', 'EndAlt', 'EndAz', 'Mag_Rise', 'Mag_High', 'Mag_Set', 'ObjType', 'Owner')
    self.satellite_tree = ttk.Treeview(tree_container, columns=columns, show='headings', height=15)
    
    # Definer kolonner
    column_widths = {'SatName': 140, 'NORAD': 70, 'StartTime': 75, 'StartAlt': 60, 'StartAz': 50,
                    'HiTime': 75, 'HiAlt': 60, 'HiAz': 50, 'EndTime': 75, 'EndAlt': 60, 'EndAz': 50,
                    'Mag_Rise': 50, 'Mag_High': 50, 'Mag_Set': 50, 'ObjType': 60, 'Owner': 60}
    
    # Initialisér sortering state
    self.sort_column = None
    self.sort_reverse = False
    
    for col in columns:
        self.satellite_tree.heading(col, text=col, command=lambda c=col: self.sort_treeview_by_column(c))
        self.satellite_tree.column(col, width=column_widths.get(col, 100))
    
    # Konfigurer farvetags for treeview
    self.satellite_tree.tag_configure('passed', background='#ffcccc')  # Lyserød for passeret
    self.satellite_tree.tag_configure('starting_soon', background='#ffffcc')  # Lysegul for starter snart
    self.satellite_tree.tag_configure('active', background='#ccffcc')  # Lysegrøn for aktiv
    self.satellite_tree.tag_configure('normal', background='white')  # Normal baggrund
    
    # Scrollbars for treeview
    tree_v_scrollbar = ttk.Scrollbar(tree_container, orient='vertical', command=self.satellite_tree.yview)
    tree_h_scrollbar = ttk.Scrollbar(tree_container, orient='horizontal', command=self.satellite_tree.xview)
    self.satellite_tree.configure(yscrollcommand=tree_v_scrollbar.set, xscrollcommand=tree_h_scrollbar.set)
    
    # Pack treeview og scrollbars
    tree_v_scrollbar.pack(side='right', fill='y')
    tree_h_scrollbar.pack(side='bottom', fill='x')
    self.satellite_tree.pack(side='left', fill='both', expand=True)
    
    # Tilføj pagination knapper under treeviewet
    setup_pagination_buttons(self, result_frame)

def fetch_satellites_threaded(self):
    """Starter satelit-hentning i separat tråd"""
    self.log_satellite_message("Starter satelit hentning...")
    threading.Thread(target=self.fetch_satellites, daemon=True).start()

def get_satellite_status(self, start_time_str, end_time_str, selected_date_obj, current_time):
    """Beregn status for en satellit (passed/active/starting_soon/normal)"""
    try:
        start_time = datetime.strptime(start_time_str, '%H:%M:%S').time()
        end_time = datetime.strptime(end_time_str, '%H:%M:%S').time()
        
        # Kombiner dato og tid
        start_datetime = datetime.combine(selected_date_obj, start_time)
        end_datetime = datetime.combine(selected_date_obj, end_time)
        
        # Håndter midnight crossing (hvis end_time < start_time)
        if end_time < start_time:
            end_datetime = end_datetime + timedelta(days=1)
        
        # Beregn status
        if current_time > end_datetime:
            return 'passed'
        elif current_time >= start_datetime:
            return 'active'
        elif (start_datetime - current_time).total_seconds() <= 300:
            return 'starting_soon'
        else:
            return 'normal'
    except:
        return 'normal'

def fetch_satellites(self):
    """Hent satelitlister fra Heavens Above og Space-Track"""
    try:
        # Tjek at Selenium er tilgængeligt
        if not SELENIUM_AVAILABLE:
            self.log_satellite_message("❌ Selenium ikke tilgængelig")
            messagebox.showerror("Fejl", "Selenium er ikke installeret. Installer med: pip install selenium beautifulsoup4")
            return
            
        # Hent input værdier
        date_str = self.date_entry.get()
        lat = float(self.lat_entry.get())
        lng = float(self.lng_entry.get())
        username = self.username_entry.get()
        password = self.password_entry.get()
        utc_offset = float(self.utc_offset_entry.get())
        
        if not username or not password:
            self.log_satellite_message("❌ Manglende Space-Track login oplysninger")
            messagebox.showerror("Fejl", "Indtast Space-Track login oplysninger")
            return
        
        self.log_satellite_message(f"Henter data for {date_str}")
        self.log_satellite_message(f"Lokation: {lat:.4f}, {lng:.4f}")
        self.progress_var.set(20)
        
        # Kald dine funktioner
        self.df_merged, self.df_heavens = self.fetch_satellite_data_with_tle(
            date_str, username, password, lat, lng, utc_offset
        )

        self.log_satellite_message("Sorterer data efter starttid...")
        # Sorter data efter StartTime
        self.df_merged = self.sort_dataframe_by_starttime(self.df_merged)
        
        self.progress_var.set(90)
        
        # Opdater treeview i hovedtråd for optimal ydeevne
        self.log_satellite_message("Opdaterer satelitliste...")
        self.root.after(0, self.update_satellite_tree)
        
        self.progress_var.set(100)
        success_msg = f"Hentet {len(self.df_merged)} satellitter med TLE data (sorteret efter starttid)"
        
    except Exception as e:
        error_msg = f"Fejl ved hentning: {str(e)}"
        self.log_satellite_message(f"❌ {error_msg}")
        messagebox.showerror("Fejl", error_msg)
    finally:
        self.progress_var.set(0)

def update_satellite_tree(self):
    """Opdater treeview med satelitdata og farvekodning"""
    # Resets current page when fresh data is loaded
    self.current_page = 0
    self.is_filtered = False
    self.df_filtered = None
    
    # Brug update_page_display for pagination
    self.update_page_display()

def save_satellite_list(self):
    """Gem satelitlisten til fil (denne version bruges ikke længere - se ned i filen)"""
    pass

def clear_satellite_list(self):
    """Ryd satelitlisten"""
    self.log_satellite_message("Rydder satelitliste...")
    for item in self.satellite_tree.get_children():
        self.satellite_tree.delete(item)
    self.df_merged = None
    self.df_heavens = None
    self.log_satellite_message("✅ Satelitliste ryddet")

def load_csv_file(self):
    """Åbner og indlæser en CSV-fil med satelitdata"""
    self.log_satellite_message("Åbner fil dialog for CSV...")
    try:
        filename = filedialog.askopenfilename(
            title="Åbn satelitdata CSV-fil",
            filetypes=[
                ("CSV files", "*.csv"),
                ("Semicolon separated", "*.csv"),
                ("All files", "*.*")
            ]
        )
        
        if not filename:
            self.log_satellite_message("❌ Ingen fil valgt")
            return
        
        self.log_satellite_message(f"Indlæser CSV-fil: {filename}")
        self.progress_var.set(20)
        
        # Prøv at læse metadata først
        skip_rows = 0
        with open(filename, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
            if first_line.startswith('#LIST_START:') and '#LIST_END:' in first_line:
                skip_rows = 1
        
        # Prøv forskellige separatorer
        separators = [';', ',', '\t']
        df_loaded = None
        
        for sep in separators:
            try:
                df_test = pd.read_csv(filename, sep=sep, nrows=5, skiprows=skip_rows)
                # Tjek om vi har de forventede kolonner
                expected_cols = ['SatName', 'NORAD', 'StartTime', 'HiTime', 'EndTime']
                if any(col in df_test.columns for col in expected_cols):
                    df_loaded = pd.read_csv(filename, sep=sep, skiprows=skip_rows)
                    break
            except:
                continue
        
        if df_loaded is None:
            # Hvis automatisk detektion fejler, prøv standard CSV
            df_loaded = pd.read_csv(filename, skiprows=skip_rows)
        
        self.progress_var.set(60)
        
        # Valider og rens data
        df_loaded = self.validate_csv_data(df_loaded)
        
        # Sorter data efter StartTime
        df_loaded = self.sort_dataframe_by_starttime(df_loaded)
        
        self.progress_var.set(80)
        
        # Opdater variabler
        self.df_merged = df_loaded
        
        # Opdater display
        self.log_satellite_message("Opdaterer satelitliste fra CSV...")
        self.update_satellite_tree()
        
        self.progress_var.set(100)
        success_msg = f"✅ CSV-fil indlæst: {len(df_loaded)} satellitter (sorteret efter starttid)"
        self.log_satellite_message(success_msg)
        
        # Prøv at læse metadata fra CSV
        self.extract_metadata_from_csv(filename)
        
        # Opdater warning label
        self.update_satellite_list_warning()
        # Start timer for at opdatere warning hver 5. minut
        self.schedule_warning_update()
        
        messagebox.showinfo("Succes", f"CSV-fil indlæst med {len(df_loaded)} satellitter")
        
    except Exception as e:
        error_msg = f"Kunne ikke indlæse CSV-fil: {str(e)}"
        self.log_satellite_message(f"❌ {error_msg}")
        messagebox.showerror("Fejl", error_msg)
    finally:
        self.progress_var.set(0)

def validate_csv_data(self, df):
    """Validerer og renser CSV-data for at sikre kompatibilitet (optimeret)"""
    try:
        # Standardiser kolonnenavne (case-insensitive mapping)
        column_mapping = {
            'satname': 'SatName', 'satellite': 'SatName', 'name': 'SatName',
            'norad': 'NORAD', 'norad_id': 'NORAD',
            'starttime': 'StartTime', 'start_time': 'StartTime',
            'hitime': 'HiTime', 'hi_time': 'HiTime',
            'endtime': 'EndTime', 'end_time': 'EndTime',
            'hialt': 'HiAlt', 'hi_alt': 'HiAlt', 'altitude': 'HiAlt',
            'magnitude': 'Magnitude_High', 'mag': 'Magnitude_High',
            'magnitude_rise': 'Magnitude_Rise', 'mag_rise': 'Magnitude_Rise',
            'magnitude_high': 'Magnitude_High', 'mag_high': 'Magnitude_High',
            'magnitude_set': 'Magnitude_Set', 'mag_set': 'Magnitude_Set',
            'tle1': 'TLE1', 'tle_1': 'TLE1', 'tle2': 'TLE2', 'tle_2': 'TLE2',
            'object_type': 'OBJECT_TYPE', 'owner': 'OWNER'
        }
        
        # Omdøb kolonner med dict-mapping (hurtigere end loop)
        df_renamed = df.rename(columns={old: column_mapping[old.lower()] 
                                        for old in df.columns 
                                        if old.lower() in column_mapping})
        
        # Sikr at vi har magnitude kolonne(r) - alleen hvis Magnitude_High eksisterer
        if 'Magnitude_High' in df_renamed.columns:
            if 'Magnitude_Rise' not in df_renamed.columns:
                df_renamed['Magnitude_Rise'] = df_renamed['Magnitude_High']
            if 'Magnitude_Set' not in df_renamed.columns:
                df_renamed['Magnitude_Set'] = df_renamed['Magnitude_High']
        
        # Sikr at vi har minimumskolonner
        if 'SatName' not in df_renamed.columns:
            df_renamed['SatName'] = [f"Satellite_{i}" for i in range(len(df_renamed))]
        if 'NORAD' not in df_renamed.columns:
            df_renamed['NORAD'] = range(1, len(df_renamed) + 1)
        
        # Sikr at OBJECT_TYPE og OWNER eksisterer
        if 'OBJECT_TYPE' not in df_renamed.columns:
            df_renamed['OBJECT_TYPE'] = None
        if 'OWNER' not in df_renamed.columns:
            df_renamed['OWNER'] = None
        
        # Sikr at Day kolonne eksisterer (for backward compatibility med gamle CSV-filer)
        if 'Day' not in df_renamed.columns:
            df_renamed['Day'] = 1  # Default til dag 1 for gamle filer
        
        # Sikr at NORAD er numerisk + fjern NaN samtidigt
        df_renamed['NORAD'] = pd.to_numeric(df_renamed['NORAD'], errors='coerce')
        
        # Fjern rækker med tomme satelitnavne
        df_renamed = df_renamed.dropna(subset=['SatName'])
        
        return df_renamed.reset_index(drop=True)
        
    except Exception as e:
        print(f"Validering fejlede: {e}")
        return df

def fetch_active_tles(self, username, password):
    """Henter alle aktive TLE'er fra Space-Track"""
    LOGIN_URL = "https://www.space-track.org/ajaxauth/login"
    
    # Prøv flere forskellige API endpoints i prioriteret rækkefølge
    TLE_URLS = [
        # GP (General Perturbations) data - ofte mere stabilt
        "https://www.space-track.org/basicspacedata/query/class/gp/EPOCH/>now-14/orderby/NORAD_CAT_ID/format/json",
        # TLE Latest uden filter
        "https://www.space-track.org/basicspacedata/query/class/tle_latest/ORDINAL/1/format/json",
        # TLE Latest med limit
        "https://www.space-track.org/basicspacedata/query/class/tle_latest/ORDINAL/1/limit/50000/format/json",
        # 3LE format (alternativ)
        "https://www.space-track.org/basicspacedata/query/class/tle_latest/ORDINAL/1/format/3le"
    ]
    
    try:
        with requests.Session() as session:
            # Login med credentials
            login_data = {"identity": username, "password": password}
            self.log_satellite_message(f"Logger ind på Space-Track som {username}...")
            
            resp = session.post(LOGIN_URL, data=login_data, timeout=30)
            
            if resp.status_code != 200:
                raise Exception(f"Login fejlede med HTTP {resp.status_code}")
            
            # Tjek om login faktisk lykkedes ved at kigge på response
            if "error" in resp.text.lower() or "invalid" in resp.text.lower():
                raise Exception("Login fejlede - check brugernavn og password")
            
            # Tjek om vi har en session cookie
            if not session.cookies:
                self.log_satellite_message("⚠️ Ingen session cookies - login kan have fejlet")
            else:
                self.log_satellite_message(f"✅ Login succesfuldt (cookies: {len(session.cookies)})")
            
            # Prøv hver URL i rækkefølge
            tle_resp = None
            successful_url = None
            
            for i, url in enumerate(TLE_URLS):
                try:
                    self.log_satellite_message(f"Prøver API endpoint {i+1}/{len(TLE_URLS)}...")
                    tle_resp = session.get(url, timeout=90)
                    
                    if tle_resp.status_code == 200 and tle_resp.text and tle_resp.text.strip():
                        successful_url = url
                        self.log_satellite_message(f"✅ Succesfuld forbindelse til endpoint {i+1}")
                        break
                    else:
                        self.log_satellite_message(f"❌ Endpoint {i+1} fejlede (HTTP {tle_resp.status_code})")
                except Exception as url_err:
                    self.log_satellite_message(f"❌ Endpoint {i+1} fejl: {str(url_err)[:50]}")
                    continue
            
            # Hvis ingen URL'er virkede
            if not successful_url or not tle_resp or tle_resp.status_code != 200:
                raise Exception(
                    "Alle Space-Track API endpoints fejlede. "
                    "Mulige årsager: 1) Forkert login 2) Space-Track nede 3) Rate limit nået. "
                    "Prøv igen om få minutter eller check https://www.space-track.org"
                )
            
            # Parse response baseret på format
            if not tle_resp.text or tle_resp.text.strip() == "":
                raise Exception("Tom response fra Space-Track")
            
            tle_data = []
            
            # Tjek om det er JSON eller 3LE format
            if "format/json" in successful_url:
                # JSON format
                try:
                    tle_json = tle_resp.json()
                except Exception as json_err:
                    raise Exception(f"Kunne ikke parse JSON: {json_err}")
                
                if not tle_json or len(tle_json) == 0:
                    raise Exception("Tom JSON array modtaget")
                
                self.log_satellite_message(f"Modtaget {len(tle_json)} objekter fra Space-Track")
                
                # Parse JSON entries
                for entry in tle_json:
                    try:
                        norad_id = str(entry.get('NORAD_CAT_ID', '')).strip()
                        object_name = entry.get('OBJECT_NAME', f"NORAD-{norad_id}")
                        tle_line1 = entry.get('TLE_LINE1', '').strip()
                        tle_line2 = entry.get('TLE_LINE2', '').strip()
                        
                        # Valider TLE linjer
                        if (tle_line1.startswith('1 ') and tle_line2.startswith('2 ') and 
                            norad_id and len(tle_line1) >= 69 and len(tle_line2) >= 69):
                            
                            tle_data.append({
                                'Name': object_name,
                                'NORAD_ID': norad_id,
                                'TLE1': tle_line1,
                                'TLE2': tle_line2
                            })
                    except Exception:
                        continue
            
            else:
                # 3LE format (3 linjer: navn, line1, line2)
                lines = [line.strip() for line in tle_resp.text.splitlines() if line.strip()]
                self.log_satellite_message(f"Modtaget {len(lines)} linjer i 3LE format")
                
                i = 0
                while i < len(lines) - 2:
                    name = lines[i]
                    line1 = lines[i + 1]
                    line2 = lines[i + 2]
                    
                    if line1.startswith('1 ') and line2.startswith('2 '):
                        norad_id = line1[2:7].strip()
                        tle_data.append({
                            'Name': name,
                            'NORAD_ID': norad_id,
                            'TLE1': line1,
                            'TLE2': line2
                        })
                        i += 3
                    else:
                        i += 1
            
            if len(tle_data) == 0:
                raise Exception("Ingen gyldige TLE'er kunne parses fra Space-Track data")
            
            self.log_satellite_message(f"✅ Parsede {len(tle_data)} gyldige TLE'er")
            return pd.DataFrame(tle_data)
            
    except requests.exceptions.Timeout:
        raise Exception("Timeout - Space-Track.org svarer ikke (prøv igen senere)")
    except requests.exceptions.ConnectionError:
        raise Exception("Ingen internet forbindelse til Space-Track.org")
    except Exception as e:
        raise Exception(f"Space-Track fejl: {str(e)}")

def fetch_satellites_inthesky(date_str, lat, lng, utc_offset=0):
    """
    Fetch satellite passage data from in-the-sky.org
    
    Parameters:
    -----------
    date_str : str
        Date in format 'YYYY-MM-DD' or 'DD-MM-YYYY'
    lat : float
        Latitude (positive for North, negative for South)
    lng : float
        Longitude (positive for East, negative for West)
    utc_offset : float
        UTC offset in hours (default: 0 for UTC). Example: -2 for CEST, +1 for CET
    
    Returns:
    --------
    pd.DataFrame
        DataFrame with columns: SatName, NORAD, RiseTime, RiseDirection, RiseAltitude, RiseMagnitude,
                                HighTime, HighDirection, HighAltitude, HighMagnitude,
                                SetTime, SetDirection, SetAltitude, SetMagnitude
        Times are converted to local time based on utc_offset
    
    Example:
    --------
    df = fetch_satellites_inthesky('2026-01-30', 66.996007, -50.621153, utc_offset=-2)
    """
    
    # Parse date
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    except:
        date_obj = datetime.strptime(date_str, '%d-%m-%Y')
    
    day, month, year = date_obj.day, date_obj.month, date_obj.year
    
    # Create headless browser
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        wait = WebDriverWait(driver, 20)
    except Exception as e:
        raise Exception(f"Chrome WebDriver fejl: {e}")
    
    try:
        # Step 1: Set location via location.php form (always use UTC in browser, will convert locally)
        driver.get("https://in-the-sky.org/location.php")
        
        tz_str = "+00:00"  # Always fetch in UTC, convert locally
        driver.execute_script(f"""
            document.querySelector('input[name="latitude"]').value = '{lat}';
            document.querySelector('input[name="longitude"]').value = '{lng}';
            document.querySelector('input[name="timezone"]').value = '{tz_str}';
        """)
        
        driver.execute_script("""
            document.querySelectorAll('input[type="submit"]')
                .forEach(btn => btn.value.includes('custom') && btn.click());
        """)
        
        # Step 2: Fetch satpasses data
        url = f"https://in-the-sky.org/satpasses.php?day={day}&month={month}&year={year}&mag=500&anysat=v0&group=1&s="
        driver.get(url)
        
        # Step 2b: Check "Include daylight passes" checkbox and update table
        try:
            # Find the "include daylight passes" checkbox (name="dl")
            daylight_checkbox = driver.find_element(By.NAME, "dl")
            
            # Scroll to make sure it's visible
            driver.execute_script("arguments[0].scrollIntoView(true);", daylight_checkbox)
            
            # Always click it to ensure it's checked
            driver.execute_script("arguments[0].click();", daylight_checkbox)
            
            # Find and click the "Update Table" button
            try:
                # Try to find the update table button by various selectors
                update_btn = None
                
                # Try finding by value containing "update"
                buttons = driver.find_elements(By.TAG_NAME, "input")
                for btn in buttons:
                    if btn.get_attribute("type") == "submit":
                        btn_value = btn.get_attribute("value") or ""
                        if "update" in btn_value.lower():
                            update_btn = btn
                            break
                
                if update_btn:
                    driver.execute_script("arguments[0].scrollIntoView(true);", update_btn)
                    driver.execute_script("arguments[0].click();", update_btn)
                    wait.until(EC.staleness_of(update_btn))
                else:
                    # Fallback: click any submit button
                    submit_buttons = driver.find_elements(By.CSS_SELECTOR, "input[type='submit']")
                    if submit_buttons:
                        driver.execute_script("arguments[0].click();", submit_buttons[0])
                        wait.until(EC.staleness_of(submit_buttons[0]))
                        
            except Exception as e:
                print(f"Could not click update button: {e}")
                pass
                
        except Exception as e:
            print(f"Could not handle daylight checkbox: {e}")
            pass
        
        # Step 3: Parse HTML
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        tables = soup.find_all('table')
        
        if len(tables) < 2:
            return None
        
        # Step 4: Extract data
        satellites = []
        for row in tables[1].find_all('tr')[2:]:
            cols = row.find_all('td')
            
            if len(cols) < 15:
                continue
            
            # Extract satellite name and NORAD ID
            sat_cell = cols[0]
            sat_name = sat_cell.get_text().strip()
            norad_id = None
            
            if link := sat_cell.find('a'):
                sat_name = link.get_text().strip()
                if match := re.search(r'id=(\d+)', link.get('href', '')):
                    norad_id = int(match.group(1))
            
            # Extract times and data
            col_texts = [col.get_text().strip() for col in cols]
            
            # Parse times and apply UTC offset
            rise_time_str = col_texts[2]
            high_time_str = col_texts[6]
            set_time_str = col_texts[10]
            
            # Convert times from UTC to local time using utc_offset
            rise_time = pd.to_datetime(rise_time_str, format='%H:%M:%S', errors='coerce')
            high_time = pd.to_datetime(high_time_str, format='%H:%M:%S', errors='coerce')
            set_time = pd.to_datetime(set_time_str, format='%H:%M:%S', errors='coerce')
            
            if pd.notna(rise_time):
                rise_time = rise_time + pd.Timedelta(hours=utc_offset)
            if pd.notna(high_time):
                high_time = high_time + pd.Timedelta(hours=utc_offset)
            if pd.notna(set_time):
                set_time = set_time + pd.Timedelta(hours=utc_offset)
            
            # Format back to time strings
            rise_time_str = rise_time.strftime('%H:%M:%S') if pd.notna(rise_time) else col_texts[2]
            high_time_str = high_time.strftime('%H:%M:%S') if pd.notna(high_time) else col_texts[6]
            set_time_str = set_time.strftime('%H:%M:%S') if pd.notna(set_time) else col_texts[10]
            
            satellites.append({
                'SatName': sat_name,
                'NORAD': norad_id,
                'RiseTime': rise_time_str,
                'RiseDirection': col_texts[3],
                'RiseAltitude': col_texts[4].replace('°', '').replace('?', ''),
                'RiseMagnitude': col_texts[5].replace('°', '').replace('?', ''),
                'HighTime': high_time_str,
                'HighDirection': col_texts[7],
                'HighAltitude': col_texts[8].replace('°', '').replace('?', ''),
                'HighMagnitude': col_texts[9].replace('°', '').replace('?', ''),
                'SetTime': set_time_str,
                'SetDirection': col_texts[11],
                'SetAltitude': col_texts[12].replace('°', '').replace('?', ''),
                'SetMagnitude': col_texts[13].replace('°', '').replace('?', ''),
            })
        
        return pd.DataFrame(satellites) if satellites else None
    
    finally:
        driver.quit()

def fetch_satellite_data_with_tle(self, date, username, password, lat=55.781553, lng=12.514595, utc_offset=2):
    """Hovedfunktion der kombinerer in-the-sky.org, Space-Track og satcat data
    
    Henter satellitter fra 12:00 middag på den angivet dag til 12:00 middag dagen efter.
    """
    self.progress_var.set(30)
    self.log_satellite_message("Henter aktive TLE'er fra Space-Track...")
    df_TLE = self.fetch_active_tles(username, password)
    self.log_satellite_message(f"Hentede {len(df_TLE)} aktive TLE'er fra Space-Track")

    df_TLE['NORAD_ID'] = pd.to_numeric(df_TLE['NORAD_ID'], errors='coerce')
    
    self.progress_var.set(40)

    # Hent data for dag 1 (angivet dato)
    self.log_satellite_message(f"[DAG 1] Henter satellitdata fra in-the-sky.org (UTC offset: {utc_offset})...")
    df_day1 = fetch_satellites_inthesky(date, lat, lng, utc_offset=utc_offset)
    
    # Konverter til Heavens-Above format
    if df_day1 is None or len(df_day1) == 0:
        raise Exception("Ingen satellitdata hentet fra in-the-sky.org for dag 1")
    
    df_day1 = pd.DataFrame({
        'SatName': df_day1['SatName'],
        'Magnitude_Rise': df_day1['RiseMagnitude'],
        'Magnitude_High': df_day1['HighMagnitude'],
        'Magnitude_Set': df_day1['SetMagnitude'],
        'StartTime': df_day1['RiseTime'],
        'StartAlt': df_day1['RiseAltitude'],
        'StartAz': df_day1['RiseDirection'],
        'HiTime': df_day1['HighTime'],
        'HiAlt': df_day1['HighAltitude'],
        'HiAz': df_day1['HighDirection'],
        'EndTime': df_day1['SetTime'],
        'EndAlt': df_day1['SetAltitude'],
        'EndAz': df_day1['SetDirection'],
        'NORAD': df_day1['NORAD']
    })
    
    # Filtrer dag 1: behold kun satellitter med StartTime >= 12:00:00
    df_day1['StartTime_dt'] = pd.to_datetime(df_day1['StartTime'], format='%H:%M:%S', errors='coerce')
    cutoff_time = pd.to_datetime('12:00:00', format='%H:%M:%S')
    df_day1 = df_day1[df_day1['StartTime_dt'] >= cutoff_time]
    df_day1 = df_day1.drop(columns=['StartTime_dt'])
    df_day1['Day'] = 1
    self.log_satellite_message(f"[DAG 1] Efter filtrering (≥ 12:00): {len(df_day1)} satellitter")
    
    self.progress_var.set(50)

    # Beregn næste dag
    date_obj = datetime.strptime(date, '%Y-%m-%d')
    next_date = (date_obj + timedelta(days=1)).strftime('%Y-%m-%d')
    
    # Hent data for dag 2 (næste dag)
    self.log_satellite_message(f"[DAG 2] Henter satellitdata fra in-the-sky.org (UTC offset: {utc_offset})...")
    df_day2 = fetch_satellites_inthesky(next_date, lat, lng, utc_offset=utc_offset)
    
    # Konverter til Heavens-Above format
    if df_day2 is None or len(df_day2) == 0:
        raise Exception("Ingen satellitdata hentet fra in-the-sky.org for dag 2")
    
    df_day2 = pd.DataFrame({
        'SatName': df_day2['SatName'],
        'Magnitude_Rise': df_day2['RiseMagnitude'],
        'Magnitude_High': df_day2['HighMagnitude'],
        'Magnitude_Set': df_day2['SetMagnitude'],
        'StartTime': df_day2['RiseTime'],
        'StartAlt': df_day2['RiseAltitude'],
        'StartAz': df_day2['RiseDirection'],
        'HiTime': df_day2['HighTime'],
        'HiAlt': df_day2['HighAltitude'],
        'HiAz': df_day2['HighDirection'],
        'EndTime': df_day2['SetTime'],
        'EndAlt': df_day2['SetAltitude'],
        'EndAz': df_day2['SetDirection'],
        'NORAD': df_day2['NORAD']
    })
    
    # Filtrer dag 2: behold kun satellitter med StartTime < 12:00:00
    df_day2['StartTime_dt'] = pd.to_datetime(df_day2['StartTime'], format='%H:%M:%S', errors='coerce')
    df_day2 = df_day2[df_day2['StartTime_dt'] < cutoff_time]
    df_day2 = df_day2.drop(columns=['StartTime_dt'])
    df_day2['Day'] = 2
    self.log_satellite_message(f"[DAG 2] Efter filtrering (< 12:00): {len(df_day2)} satellitter")
    
    self.progress_var.set(70)

    # Kombiner begge lister
    df_heavens = pd.concat([df_day1, df_day2], ignore_index=True)
    self.log_satellite_message(f"✅ Kombineret total: {len(df_heavens)} satellitter fra begge dage")
    
    self.progress_var.set(80)
    self.log_satellite_message("Sammenfletter in-the-sky.org data med TLE'er...")
    df_merged = df_heavens.merge(df_TLE, left_on='NORAD', right_on='NORAD_ID', how='left')
    df_merged = df_merged.drop(columns=['NORAD_ID', 'Name'])
    df_merged = df_merged.reset_index(drop=True)
    df_merged = df_merged.dropna(subset=['TLE1'])
    
    # Merge med satcat for OBJECT_TYPE og OWNER
    self.log_satellite_message("Sammenfletter med satcat data...")
    df_merged = merge_with_satcat(df_merged)
    self.log_satellite_message(f"✅ Tilføjet OBJECT_TYPE og OWNER fra satcat")
    
    # Beregn start og end tider for satelitlisten
    # Start: angivet dato kl 12:00
    start_datetime = datetime.strptime(date, '%Y-%m-%d').replace(hour=12, minute=0, second=0)
    # End: næste dag kl 12:00
    end_datetime = (datetime.strptime(date, '%Y-%m-%d') + timedelta(days=1)).replace(hour=12, minute=0, second=0)
    
    # Gem i self for senere brug
    self.list_start_datetime = start_datetime
    self.list_end_datetime = end_datetime
    
    # Opdater warning label
    self.root.after(0, self.update_satellite_list_warning)
    # Start timer for at opdatere warning hver 5. minut
    self.schedule_warning_update()
    
    return df_merged, df_heavens

def load_csv_file_direct(self, filename):
    """Hjælpemetode til at indlæse CSV direkte fra filnavn"""
    try:
        # Prøv forskellige separatorer
        separators = [';', ',', '\t']
        df_loaded = None
        
        for sep in separators:
            try:
                df_test = pd.read_csv(filename, sep=sep, nrows=5)
                expected_cols = ['SatName', 'NORAD', 'StartTime', 'HiTime', 'EndTime']
                if any(col in df_test.columns for col in expected_cols):
                    df_loaded = pd.read_csv(filename, sep=sep)
                    break
            except:
                continue
        
        if df_loaded is None:
            df_loaded = pd.read_csv(filename)
        
        # Valider data
        df_loaded = self.validate_csv_data(df_loaded)
        
        # Merge med satcat hvis NORAD kolonne findes
        df_loaded = merge_with_satcat(df_loaded)
        
        # Sorter data efter StartTime
        df_loaded = self.sort_dataframe_by_starttime(df_loaded)
        
        # Opdater variabler
        self.df_merged = df_loaded
        
        # Opdater display
        self.update_satellite_tree()
        
        # Prøv at læse metadata fra CSV
        self.extract_metadata_from_csv(filename)
        
        # Opdater warning label
        self.update_satellite_list_warning()
        # Start timer for at opdatere warning hver 5. minut
        self.schedule_warning_update()
        
        messagebox.showinfo("Succes", f"CSV-fil indlæst med {len(df_loaded)} satellitter")
        
    except Exception as e:
        messagebox.showerror("Fejl", f"Kunne ikke indlæse CSV-fil:\n{str(e)}")

def extract_metadata_from_csv(self, filename):
    """Læser metadata fra CSV-fil headers"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
            
        # Søg efter #LIST_START og #LIST_END i første linje
        if '#LIST_START:' in first_line and '#LIST_END:' in first_line:
            start_match = re.search(r'#LIST_START:([\d\-\s:]+)', first_line)
            end_match = re.search(r'#LIST_END:([\d\-\s:]+)', first_line)
            
            if start_match and end_match:
                start_str = start_match.group(1).strip()
                end_str = end_match.group(1).strip()
                
                self.list_start_datetime = datetime.strptime(start_str, '%Y-%m-%d %H:%M:%S')
                self.list_end_datetime = datetime.strptime(end_str, '%Y-%m-%d %H:%M:%S')
                self.log_satellite_message(f"✅ Læst satelitliste tidspunkt: {start_str} til {end_str}")
    except Exception as e:
        self.log_satellite_message(f"⚠️ Kunne ikke læse metadata fra CSV: {str(e)}")

def update_satellite_list_warning(self):
    """Opdater warning label baseret på om vi er inden for satelitlistens tidsinterval"""
    if not hasattr(self, 'satellite_list_warning'):
        return
    
    if self.list_start_datetime is None or self.list_end_datetime is None:
        self.satellite_list_warning.config(text="")
        return
    
    current_time = datetime.now()
    
    # Check om vi er inden for intervallet
    if current_time < self.list_start_datetime or current_time > self.list_end_datetime:
        # Vi er udenfor intervallet
        start_str = self.list_start_datetime.strftime('%Y-%m-%d %H:%M')
        end_str = self.list_end_datetime.strftime('%Y-%m-%d %H:%M')
        warning_text = f"🔴 OBS! VI BEFINDER OS UDENFOR LISTENS TIDSINTERVAL - Gælder: {start_str} til {end_str}"
        self.satellite_list_warning.config(text=warning_text, foreground='red')
    else:
        # Vi er inden for intervallet
        start_str = self.list_start_datetime.strftime('%Y-%m-%d %H:%M')
        end_str = self.list_end_datetime.strftime('%Y-%m-%d %H:%M')
        info_text = f"Satellitliste fra {start_str} til {end_str}"
        self.satellite_list_warning.config(text=info_text, foreground='green')

def schedule_warning_update(self):
    """Planlægger warning update hver 5. minut"""
    # Annuller tidligere timer hvis den eksisterer
    if self.warning_update_job is not None:
        self.root.after_cancel(self.warning_update_job)
    
    # Opdater nu
    self.update_satellite_list_warning()
    
    # Planlæg næste opdatering efter 5 minutter (300000 ms)
    self.warning_update_job = self.root.after(300000, self.schedule_warning_update)

def save_satellite_list(self):
    """Gem satelitlisten til fil med metadata"""
    if self.df_merged is None:
        self.log_satellite_message("❌ Ingen data at gemme")
        messagebox.showwarning("Advarsel", "Ingen data at gemme!")
        return
    
    self.log_satellite_message("Åbner gem dialog...")
    filename = filedialog.asksaveasfilename(
        title="Gem satelitliste",
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
    )
    
    if filename:
        self.log_satellite_message(f"Gemmer liste til: {filename}")
        
        # Forbered dataframen
        df_to_save = self.df_merged.copy()
        
        # Opret metadata header
        metadata_line = ""
        if self.list_start_datetime and self.list_end_datetime:
            start_str = self.list_start_datetime.strftime('%Y-%m-%d %H:%M:%S')
            end_str = self.list_end_datetime.strftime('%Y-%m-%d %H:%M:%S')
            metadata_line = f"#LIST_START:{start_str},#LIST_END:{end_str}"
        
        # Gem CSV med metadata i første linje
        with open(filename, 'w', encoding='utf-8') as f:
            if metadata_line:
                f.write(metadata_line + "\n")
            df_to_save.to_csv(f, index=False, sep=';')
        
        self.log_satellite_message("✅ Satelitliste gemt succesfuldt")
        messagebox.showinfo("Gemt", f"Satelitliste gemt som: {filename}")
    else:
        self.log_satellite_message("❌ Gem operation afbrudt")

def open_filter_dialog(self):
    """Åbner et filter dialog popup med oversigt over aktive betingelser"""
    if self.df_merged is None or len(self.df_merged) == 0:
        messagebox.showwarning("Advarsel", "Ingen data at filtrere. Hent eller indlæs satelitdata først.")
        return
    
    # Opret popup vindue
    popup = tk.Toplevel(self.root)
    popup.title("Filtrer Satellitter")
    popup.geometry("900x800")
    popup.resizable(False, False)
    
    # Opret main frame
    main_frame = ttk.Frame(popup)
    main_frame.pack(fill='both', expand=True, padx=10, pady=10)
    
    # Titel
    ttk.Label(main_frame, text="Filtrer Satellitter", font=('TkDefaultFont', 12, 'bold')).pack(pady=(0, 10))
    
    # To-kolonne layout: Venstre (filtre) og Højre (aktive betingelser)
    content_frame = ttk.Frame(main_frame)
    content_frame.pack(fill='both', expand=True)
    
    # ============ VENSTRE SEKTION: FILTER INPUTS ============
    left_frame = ttk.Frame(content_frame)
    left_frame.pack(side='left', fill='both', expand=True, padx=(0, 10))
    
    ttk.Label(left_frame, text="Filter Indstillinger:", font=('TkDefaultFont', 10, 'bold')).pack(anchor='w', pady=(0, 10))
    
    # Canvas med scrollbar for filter inputs
    canvas = tk.Canvas(left_frame, highlightthickness=0)
    scrollbar = ttk.Scrollbar(left_frame, orient='vertical', command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)
    
    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    
    # Filter variabler
    filter_vars = {}
    
    # SatName filter
    ttk.Label(scrollable_frame, text="Satelit navn (indeholder):", font=('TkDefaultFont', 10, 'bold')).pack(anchor='w', pady=(10, 5))
    filter_vars['satname'] = tk.StringVar(value=self.active_filters.get('satname', ''))
    ttk.Entry(scrollable_frame, textvariable=filter_vars['satname'], width=40).pack(anchor='w', padx=5)
    
    # NORAD ID filter
    ttk.Label(scrollable_frame, text="NORAD ID (eksakt match):", font=('TkDefaultFont', 10, 'bold')).pack(anchor='w', pady=(10, 5))
    filter_vars['norad'] = tk.StringVar(value=self.active_filters.get('norad', ''))
    ttk.Entry(scrollable_frame, textvariable=filter_vars['norad'], width=40).pack(anchor='w', padx=5)
    
    # StartTime filter
    ttk.Label(scrollable_frame, text="StartTime (HH:MM:SS):", font=('TkDefaultFont', 10, 'bold')).pack(anchor='w', pady=(10, 5))
    time_frame = ttk.Frame(scrollable_frame)
    time_frame.pack(anchor='w', padx=5, pady=(0, 10))
    ttk.Label(time_frame, text="Fra:").pack(side='left', padx=(0, 5))
    filter_vars['start_time_min'] = tk.StringVar(value=self.active_filters.get('start_time_min', ''))
    ttk.Entry(time_frame, textvariable=filter_vars['start_time_min'], width=12).pack(side='left', padx=(0, 20))
    ttk.Label(time_frame, text="Til:").pack(side='left', padx=(0, 5))
    filter_vars['start_time_max'] = tk.StringVar(value=self.active_filters.get('start_time_max', ''))
    ttk.Entry(time_frame, textvariable=filter_vars['start_time_max'], width=12).pack(side='left')
    
    # Min varighed filter
    ttk.Label(scrollable_frame, text="Minimum varighed (minutter):", font=('TkDefaultFont', 10, 'bold')).pack(anchor='w', pady=(10, 5))
    filter_vars['min_duration'] = tk.StringVar(value=self.active_filters.get('min_duration', ''))
    ttk.Entry(scrollable_frame, textvariable=filter_vars['min_duration'], width=40).pack(anchor='w', padx=5)
    
    # HiAlt filter
    ttk.Label(scrollable_frame, text="HiAlt (maksimum højde):", font=('TkDefaultFont', 10, 'bold')).pack(anchor='w', pady=(10, 5))
    hialt_frame = ttk.Frame(scrollable_frame)
    hialt_frame.pack(anchor='w', padx=5, pady=(0, 10))
    ttk.Label(hialt_frame, text="Min:").pack(side='left', padx=(0, 5))
    filter_vars['hialt_min'] = tk.StringVar(value=self.active_filters.get('hialt_min', ''))
    ttk.Entry(hialt_frame, textvariable=filter_vars['hialt_min'], width=12).pack(side='left', padx=(0, 20))
    ttk.Label(hialt_frame, text="Max:").pack(side='left', padx=(0, 5))
    filter_vars['hialt_max'] = tk.StringVar(value=self.active_filters.get('hialt_max', ''))
    ttk.Entry(hialt_frame, textvariable=filter_vars['hialt_max'], width=12).pack(side='left')
    
    # Mag_High filter
    ttk.Label(scrollable_frame, text="Mag_High (magnitude):", font=('TkDefaultFont', 10, 'bold')).pack(anchor='w', pady=(10, 5))
    mag_frame = ttk.Frame(scrollable_frame)
    mag_frame.pack(anchor='w', padx=5, pady=(0, 10))
    ttk.Label(mag_frame, text="Min:").pack(side='left', padx=(0, 5))
    filter_vars['mag_min'] = tk.StringVar(value=self.active_filters.get('mag_min', ''))
    ttk.Entry(mag_frame, textvariable=filter_vars['mag_min'], width=12).pack(side='left', padx=(0, 20))
    ttk.Label(mag_frame, text="Max:").pack(side='left', padx=(0, 5))
    filter_vars['mag_max'] = tk.StringVar(value=self.active_filters.get('mag_max', ''))
    ttk.Entry(mag_frame, textvariable=filter_vars['mag_max'], width=12).pack(side='left')
    
    # ObjType filter
    ttk.Label(scrollable_frame, text="Objekttype:", font=('TkDefaultFont', 10, 'bold')).pack(anchor='w', pady=(10, 5))
    filter_vars['objtype'] = tk.StringVar(value=self.active_filters.get('objtype', ''))
    objtype_options = [''] + sorted(self.df_merged['OBJECT_TYPE'].dropna().unique().tolist())
    objtype_combo = ttk.Combobox(scrollable_frame, textvariable=filter_vars['objtype'], values=objtype_options, state='readonly', width=37)
    objtype_combo.pack(anchor='w', padx=5)
    
    # Owner filter
    ttk.Label(scrollable_frame, text="Owner:", font=('TkDefaultFont', 10, 'bold')).pack(anchor='w', pady=(10, 5))
    filter_vars['owner'] = tk.StringVar(value=self.active_filters.get('owner', ''))
    owner_options = [''] + sorted(self.df_merged['OWNER'].dropna().unique().tolist())
    owner_combo = ttk.Combobox(scrollable_frame, textvariable=filter_vars['owner'], values=owner_options, state='readonly', width=37)
    owner_combo.pack(anchor='w', padx=5, pady=(0, 20))
    
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    
    # ============ HØJRE SEKTION: AKTIVE BETINGELSER ============
    right_frame = ttk.Frame(content_frame, width=250)
    right_frame.pack(side='right', fill='both', padx=(10, 0), expand=False)
    right_frame.pack_propagate(False)
    
    ttk.Label(right_frame, text="Aktive Betingelser:", font=('TkDefaultFont', 10, 'bold')).pack(anchor='w', pady=(0, 10))
    
    # Canvas for aktive betingelser (scrollbar)
    active_canvas = tk.Canvas(right_frame, highlightthickness=0)
    active_scrollbar = ttk.Scrollbar(right_frame, orient='vertical', command=active_canvas.yview)
    active_list_frame = ttk.Frame(active_canvas)
    
    active_list_frame.bind(
        "<Configure>",
        lambda e: active_canvas.configure(scrollregion=active_canvas.bbox("all"))
    )
    
    active_canvas.create_window((0, 0), window=active_list_frame, anchor="nw")
    active_canvas.configure(yscrollcommand=active_scrollbar.set)
    
    # Generer aktive betingelser
    if self.active_filters and any(v.strip() for v in self.active_filters.values()):
        filter_labels = {
            'satname': 'SatName',
            'norad': 'NORAD ID',
            'start_time_min': 'StartTime Min',
            'start_time_max': 'StartTime Max',
            'min_duration': 'Min Varighed',
            'hialt_min': 'HiAlt Min',
            'hialt_max': 'HiAlt Max',
            'mag_min': 'Mag Min',
            'mag_max': 'Mag Max',
            'objtype': 'ObjType',
            'owner': 'Owner'
        }
        
        for key, value in self.active_filters.items():
            if value and value.strip():
                condition_text = f"{filter_labels.get(key, key)}: {value}"
                
                condition_frame = ttk.Frame(active_list_frame)
                condition_frame.pack(fill='x', pady=3)
                
                ttk.Label(condition_frame, text=condition_text, foreground='blue', wraplength=180, justify='left').pack(side='left', fill='both', expand=True)
                
                # X-knap for at fjerne betingelse
                def make_remove_func(k):
                    def remove_condition():
                        del self.active_filters[k]
                        popup.destroy()
                        self.open_filter_dialog()
                    return remove_condition
                
                ttk.Button(condition_frame, text="✕", width=2, command=make_remove_func(key)).pack(side='right', padx=(5, 0))
        
        # Fjern alle betingelser knap
        ttk.Button(active_list_frame, text="Fjern Alle", command=lambda: (self.active_filters.clear(), popup.destroy(), self.open_filter_dialog())).pack(fill='x', pady=(10, 0))
    else:
        ttk.Label(active_list_frame, text="Ingen aktive betingelser", foreground='gray').pack(pady=20)
    
    active_canvas.pack(side="left", fill="both", expand=True)
    active_scrollbar.pack(side="right", fill="y")
    
    # ============ KNAPPER I BUNDEN ============
    button_frame = ttk.Frame(main_frame)
    button_frame.pack(fill='x', pady=(10, 0))
    
    def apply_filters():
        filters = {k: v.get() for k, v in filter_vars.items()}
        self.apply_filter(filters)
        popup.destroy()
    
    def reset_all():
        for var in filter_vars.values():
            var.set('')
    
    ttk.Button(button_frame, text="Anvend Filter", command=apply_filters).pack(side='left', padx=5)
    ttk.Button(button_frame, text="Ryd Input", command=reset_all).pack(side='left', padx=5)
    ttk.Button(button_frame, text="Luk", command=popup.destroy).pack(side='left', padx=5)

def apply_filter(self, filters):
    """Anvender filter på satelitdata (kombinerer med eksisterende filtre - AND logic)"""
    try:
        if self.df_merged is None:
            return
        
        # Start med hele datasættet
        df_filtered = self.df_merged.copy()
        
        # Merge nye filtre med eksisterende (AND logic)
        combined_filters = {**self.active_filters}
        for key, value in filters.items():
            if value and value.strip():  # Kun tilføj hvis værdien er udefinimellem 1000
                combined_filters[key] = value
        
        # Anvend SatName filter
        if combined_filters.get('satname', '').strip():
            satname_filter = combined_filters['satname'].strip().upper()
            df_filtered = df_filtered[df_filtered['SatName'].str.upper().str.contains(satname_filter, na=False)]
        
        # Anvend NORAD filter
        if combined_filters.get('norad', '').strip():
            try:
                norad_id = int(combined_filters['norad'].strip())
                df_filtered = df_filtered[df_filtered['NORAD'] == norad_id]
            except ValueError:
                pass
        
        # Anvend StartTime range filter
        start_time_min = combined_filters.get('start_time_min', '').strip()
        start_time_max = combined_filters.get('start_time_max', '').strip()
        
        if start_time_min or start_time_max:
            df_filtered['StartTime_dt'] = pd.to_datetime(df_filtered['StartTime'], format='%H:%M:%S', errors='coerce')
            if start_time_min:
                min_dt = pd.to_datetime(start_time_min, format='%H:%M:%S', errors='coerce')
                if pd.notna(min_dt):
                    df_filtered = df_filtered[df_filtered['StartTime_dt'] >= min_dt]
            if start_time_max:
                max_dt = pd.to_datetime(start_time_max, format='%H:%M:%S', errors='coerce')
                if pd.notna(max_dt):
                    df_filtered = df_filtered[df_filtered['StartTime_dt'] <= max_dt]
            df_filtered = df_filtered.drop(columns=['StartTime_dt'])
        
        # Anvend minimum varighed filter
        if combined_filters.get('min_duration', '').strip():
            try:
                min_minutes = int(combined_filters['min_duration'].strip())
                df_filtered['StartTime_dt'] = pd.to_datetime(df_filtered['StartTime'], format='%H:%M:%S', errors='coerce')
                df_filtered['EndTime_dt'] = pd.to_datetime(df_filtered['EndTime'], format='%H:%M:%S', errors='coerce')
                
                # Håndter midnight crossing
                df_filtered['Duration'] = df_filtered.apply(
                    lambda row: (row['EndTime_dt'] - row['StartTime_dt']).total_seconds() / 60 
                    if row['EndTime_dt'] >= row['StartTime_dt']
                    else ((row['EndTime_dt'] + pd.Timedelta(days=1)) - row['StartTime_dt']).total_seconds() / 60,
                    axis=1
                )
                df_filtered = df_filtered[df_filtered['Duration'] >= min_minutes]
                df_filtered = df_filtered.drop(columns=['StartTime_dt', 'EndTime_dt', 'Duration'])
            except ValueError:
                pass
        
        # Anvend HiAlt filter
        hialt_min = combined_filters.get('hialt_min', '').strip()
        hialt_max = combined_filters.get('hialt_max', '').strip()
        
        if hialt_min or hialt_max:
            df_filtered['HiAlt_num'] = pd.to_numeric(df_filtered['HiAlt'], errors='coerce')
            if hialt_min:
                try:
                    min_alt = float(hialt_min)
                    df_filtered = df_filtered[df_filtered['HiAlt_num'] >= min_alt]
                except ValueError:
                    pass
            if hialt_max:
                try:
                    max_alt = float(hialt_max)
                    df_filtered = df_filtered[df_filtered['HiAlt_num'] <= max_alt]
                except ValueError:
                    pass
            df_filtered = df_filtered.drop(columns=['HiAlt_num'])
        
        # Anvend Magnitude filter
        mag_min = combined_filters.get('mag_min', '').strip()
        mag_max = combined_filters.get('mag_max', '').strip()
        
        if mag_min or mag_max:
            df_filtered['Mag_num'] = pd.to_numeric(df_filtered['Magnitude_High'], errors='coerce')
            if mag_min:
                try:
                    min_mag = float(mag_min)
                    df_filtered = df_filtered[df_filtered['Mag_num'] >= min_mag]
                except ValueError:
                    pass
            if mag_max:
                try:
                    max_mag = float(mag_max)
                    df_filtered = df_filtered[df_filtered['Mag_num'] <= max_mag]
                except ValueError:
                    pass
            df_filtered = df_filtered.drop(columns=['Mag_num'])
        
        # Anvend ObjType filter
        if combined_filters.get('objtype', '').strip():
            df_filtered = df_filtered[df_filtered['OBJECT_TYPE'] == combined_filters['objtype'].strip()]
        
        # Anvend Owner filter
        if combined_filters.get('owner', '').strip():
            df_filtered = df_filtered[df_filtered['OWNER'] == combined_filters['owner'].strip()]
        
        # Gem filtreret data
        self.df_filtered = df_filtered
        self.is_filtered = True
        self.current_page = 0
        self.active_filters = combined_filters
        
        self.log_satellite_message(f"✅ Filter anvendt: {len(self.df_filtered)} satellitter vises af {len(self.df_merged)}")
        
        # Opdater treeview
        self.update_page_display()
        
    except Exception as e:
        self.log_satellite_message(f"❌ Filterfejl: {str(e)}")
        messagebox.showerror("Fejl", f"Fejl ved filteranvendelse: {str(e)}")

def reset_filter(self):
    """Nulstiller filter og viser alle satellitter"""
    self.df_filtered = None
    self.is_filtered = False
    self.current_page = 0
    self.active_filters = {}
    
    self.log_satellite_message("✅ Filter nulstillet - viser alle satellitter")
    self.update_page_display()

def update_page_display(self):
    """Opdater treeview til at vise aktuel side af filtreret eller ufiltreret data"""
    # Bestem hvilken dataframe der skal bruges
    display_df = self.df_filtered if self.is_filtered else self.df_merged
    
    if display_df is None or len(display_df) == 0:
        return
    
    # Beregn pagination
    total_rows = len(display_df)
    total_pages = (total_rows + self.page_size - 1) // self.page_size
    
    if total_pages == 0:
        total_pages = 1
    
    # Sikr at current_page er inden for grænser
    self.current_page = min(self.current_page, total_pages - 1)
    self.current_page = max(self.current_page, 0)
    
    # Beregn start og slut indeks
    start_idx = self.current_page * self.page_size
    end_idx = min(start_idx + self.page_size, total_rows)
    
    # Get data for denne side
    page_df = display_df.iloc[start_idx:end_idx].reset_index(drop=True)
    
    # Opdater treeview
    self.satellite_tree.delete(*self.satellite_tree.get_children())
    
    selected_date = self.date_entry.get()
    try:
        selected_date_obj = datetime.strptime(selected_date, '%Y-%m-%d').date()
    except ValueError:
        selected_date_obj = datetime.now().date()
    
    current_time = datetime.now()
    
    # Beregn status for hver satellit på siden
    start_times_parsed = pd.to_datetime(page_df['StartTime'], format='%H:%M:%S', errors='coerce')
    end_times_parsed = pd.to_datetime(page_df['EndTime'], format='%H:%M:%S', errors='coerce')
    
    start_datetimes = pd.to_datetime(
        page_df['StartTime'].astype(str).str.replace(' ', ''),
        format='%H:%M:%S', errors='coerce'
    ) + pd.Timedelta(days=0)
    
    end_datetimes = pd.to_datetime(
        page_df['EndTime'].astype(str).str.replace(' ', ''),
        format='%H:%M:%S', errors='coerce'
    ) + pd.Timedelta(days=0)
    
    mask_midnight = end_times_parsed < start_times_parsed
    end_datetimes[mask_midnight] = end_datetimes[mask_midnight] + pd.Timedelta(days=1)
    
    # PRE-CACHE COLUMN INDICES
    cols = page_df.columns.tolist()
    col_map = {col: cols.index(col) if col in cols else None for col in 
               ['SatName', 'NORAD', 'StartTime', 'StartAlt', 'StartAz', 'HiTime', 'HiAlt', 'HiAz',
                'EndTime', 'EndAlt', 'EndAz', 'Magnitude_Rise', 'Magnitude_High', 'Magnitude_Set', 
                'OBJECT_TYPE', 'OWNER']}
    
    for i, row in enumerate(page_df.itertuples(index=False)):
        try:
            satname = str(row[col_map['SatName']] or '')
            norad = str(row[col_map['NORAD']] or '')
            starttime = str(row[col_map['StartTime']] or '')
            startalt = str(row[col_map['StartAlt']] or '')
            startaz = str(row[col_map['StartAz']] or '')
            hitime = str(row[col_map['HiTime']] or '')
            hialt = str(row[col_map['HiAlt']] or '')
            hiaz = str(row[col_map['HiAz']] or '')
            endtime = str(row[col_map['EndTime']] or '')
            endalt = str(row[col_map['EndAlt']] or '')
            endaz = str(row[col_map['EndAz']] or '')
            mag_rise = str(row[col_map['Magnitude_Rise']] or '')
            mag_high = str(row[col_map['Magnitude_High']] or '')
            mag_set = str(row[col_map['Magnitude_Set']] or '')
            objtype = str(row[col_map['OBJECT_TYPE']] or '')
            owner = str(row[col_map['OWNER']] or '')
        except (IndexError, TypeError):
            continue
        
        # Beregn status
        if pd.isna(start_datetimes.iloc[i]) or pd.isna(end_datetimes.iloc[i]):
            status = 'normal'
        elif current_time > end_datetimes.iloc[i]:
            status = 'passed'
        elif current_time >= start_datetimes.iloc[i]:
            status = 'active'
        elif (start_datetimes.iloc[i] - current_time).total_seconds() <= 300:
            status = 'starting_soon'
        else:
            status = 'normal'
        
        values = (satname, norad, starttime, startalt, startaz, hitime, hialt, hiaz, 
                  endtime, endalt, endaz, mag_rise, mag_high, mag_set, objtype, owner)
        self.satellite_tree.insert('', 'end', values=values, tags=(status,))
    
    # Beregn satellit range for denne side
    start_sat_idx = start_idx + 1
    end_sat_idx = end_idx
    total_sats = total_rows
    
    # Opdater page label med side info og satellit range
    page_info = f"Side {self.current_page + 1}/{total_pages} | Satellitter: {start_sat_idx}-{end_sat_idx} af {total_sats}"
    self.page_label.config(text=page_info)
    
    # Opdater titel med filter info
    filter_status = " [FILTER AKTIVT]" if self.is_filtered else ""
    self.root.title(f"Denassi - Specialkursus 2025 | Side {self.current_page + 1}/{total_pages}{filter_status}")
    
    # Opdater navigation knapper hvis de findes
    if hasattr(self, 'prev_page_btn'):
        self.prev_page_btn.config(state='normal' if self.current_page > 0 else 'disabled')
        self.next_page_btn.config(state='normal' if self.current_page < total_pages - 1 else 'disabled')

def setup_pagination_buttons(self, result_frame):
    """Tilføjer pagination kontroller under treeviewet - centreret"""
    nav_frame = ttk.Frame(result_frame)
    nav_frame.pack(fill='x', pady=(5, 0), side='bottom')
    
    # Venstre sektion: Pagination size dropdown
    left_frame = ttk.Frame(nav_frame)
    left_frame.pack(side='left', padx=5)
    
    ttk.Label(left_frame, text="Pr. side:").pack(side='left', padx=5)
    size_combo = ttk.Combobox(left_frame, textvariable=self.page_size_var, 
                              values=['100', '200', '500'], state='readonly', width=6)
    size_combo.pack(side='left', padx=(0, 5))
    
    # Bind ændring af dropdown til opdatering
    def on_page_size_change(*args):
        try:
            self.page_size = int(self.page_size_var.get())
            self.current_page = 0
            self.update_page_display()
        except ValueError:
            pass
    
    self.page_size_var.trace('w', on_page_size_change)
    
    # Midt sektion: Navigation knapper og side info (centreret)
    center_frame = ttk.Frame(nav_frame)
    center_frame.pack(side='left', expand=True, fill='x')
    
    # Forrige knap
    self.prev_page_btn = ttk.Button(center_frame, text="← Forrige", command=self.prev_page)
    self.prev_page_btn.pack(side='left', padx=5)
    
    # Page info label
    self.page_label = ttk.Label(center_frame, text="Side 1/1")
    self.page_label.pack(side='left', padx=20)
    
    # Næste knap
    self.next_page_btn = ttk.Button(center_frame, text="Næste →", command=self.next_page)
    self.next_page_btn.pack(side='left', padx=5)
    
    # Højer sektion: Nulstil filter knap
    right_frame = ttk.Frame(nav_frame)
    right_frame.pack(side='right', padx=5)
    
    ttk.Button(right_frame, text="Nulstil Filter", command=self.reset_filter).pack(side='left')

def sort_treeview_by_column(self, col):
    """Sorter treeview efter valgt kolonne med StartTime som sekundær sortering. Klikkes igen for at vende sorteringsretning."""
    if self.df_merged is None or len(self.df_merged) == 0:
        return
    
    # Hvis vi klikker på samme kolonne, vend sorteringsretningen
    if self.sort_column == col:
        self.sort_reverse = not self.sort_reverse
    else:
        self.sort_column = col
        self.sort_reverse = False
    
    # Sorter dataframen
    try:
        df_to_sort = self.df_merged.copy()
        
        # Definer sortering efter den primære kolonne
        if col == 'StartTime':
            # Hvis StartTime er primær, sorter kun efter det
            sorted_df = df_to_sort.sort_values(
                by=col, 
                ascending=not self.sort_reverse, 
                key=lambda x: pd.to_datetime(x, format='%H:%M:%S', errors='coerce')
            )
        elif col in ['NORAD', 'Mag_Rise', 'Mag_High', 'Mag_Set']:
            # Numeriske kolonner med StartTime som sekundær
            df_to_sort[col] = pd.to_numeric(df_to_sort[col], errors='coerce')
            sorted_df = df_to_sort.sort_values(
                by=[col, 'StartTime'],
                ascending=[not self.sort_reverse, True],
                na_position='last'
            )
        elif col in ['HiTime', 'EndTime']:
            # Tidskolonner med StartTime som sekundær
            sorted_df = df_to_sort.sort_values(
                by=[col, 'StartTime'],
                ascending=[not self.sort_reverse, True],
                key=lambda x: pd.to_datetime(x, format='%H:%M:%S', errors='coerce')
            )
        else:
            # Tekst-kolonner med StartTime som sekundær
            sorted_df = df_to_sort.sort_values(
                by=[col, 'StartTime'],
                ascending=[not self.sort_reverse, True]
            )
        
        # Opdater den interne dataframe
        self.df_merged = sorted_df.reset_index(drop=True)
        
        # Hvis der er aktivt filter, sorter også den filtrerede dataframe
        if self.is_filtered and self.df_filtered is not None:
            df_filtered_to_sort = self.df_filtered.copy()
            
            if col == 'StartTime':
                sorted_filtered = df_filtered_to_sort.sort_values(
                    by=col, 
                    ascending=not self.sort_reverse, 
                    key=lambda x: pd.to_datetime(x, format='%H:%M:%S', errors='coerce')
                )
            elif col in ['NORAD', 'Mag_Rise', 'Mag_High', 'Mag_Set']:
                df_filtered_to_sort[col] = pd.to_numeric(df_filtered_to_sort[col], errors='coerce')
                sorted_filtered = df_filtered_to_sort.sort_values(
                    by=[col, 'StartTime'],
                    ascending=[not self.sort_reverse, True],
                    na_position='last'
                )
            elif col in ['HiTime', 'EndTime']:
                sorted_filtered = df_filtered_to_sort.sort_values(
                    by=[col, 'StartTime'],
                    ascending=[not self.sort_reverse, True],
                    key=lambda x: pd.to_datetime(x, format='%H:%M:%S', errors='coerce')
                )
            else:
                sorted_filtered = df_filtered_to_sort.sort_values(
                    by=[col, 'StartTime'],
                    ascending=[not self.sort_reverse, True]
                )
            
            self.df_filtered = sorted_filtered.reset_index(drop=True)
        
        # Opdater header med sorter-indikator (pil)
        self.update_header_sort_indicators(col)
        
        # Nulstil til første side efter sortering
        self.current_page = 0
        
        # Opdater visningen
        self.update_page_display()
        
        self.log_satellite_message(f"✅ Sorteret efter {col} {'↑' if self.sort_reverse else '↓'} (sekundær: StartTime)")
        
    except Exception as e:
        self.log_satellite_message(f"❌ Sortering fejlede: {str(e)}")

def update_header_sort_indicators(self, sorted_col):
    """Opdater headers for at vise sorterings-retning med pile"""
    columns = ('SatName', 'NORAD', 'StartTime', 'StartAlt', 'StartAz', 'HiTime', 'HiAlt', 'HiAz', 
               'EndTime', 'EndAlt', 'EndAz', 'Mag_Rise', 'Mag_High', 'Mag_Set', 'ObjType', 'Owner')
    
    for col in columns:
        if col == sorted_col:
            # Tilføj pile for aktiv sorterings-kolonne
            arrow = '▲' if self.sort_reverse else '▼'
            self.satellite_tree.heading(col, text=f"{col} {arrow}")
        else:
            # Fjern pile fra andre kolonner
            self.satellite_tree.heading(col, text=col)

def prev_page(self):
    """Gå til forrige side"""
    if self.current_page > 0:
        self.current_page -= 1
        self.update_page_display()

def next_page(self):
    """Gå til næste side"""
    display_df = self.df_filtered if self.is_filtered else self.df_merged
    if display_df is None:
        return
    
    total_pages = (len(display_df) + self.page_size - 1) // self.page_size
    if self.current_page < total_pages - 1:
        self.current_page += 1
        self.update_page_display()