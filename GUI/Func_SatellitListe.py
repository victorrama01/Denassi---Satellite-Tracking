import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime, timedelta
import os
import requests
import pandas as pd
import re
import time
import threading
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
    columns = ('SatName', 'NORAD', 'StartTime', 'HiTime', 'EndTime', 'HiAlt', 'Mag_Rise', 'Mag_High', 'Mag_Set', 'TLE1', 'TLE2')
    self.satellite_tree = ttk.Treeview(result_frame, columns=columns, show='headings', height=15)
    
    # Definer kolonner
    column_widths = {'SatName': 150, 'NORAD': 80, 'StartTime': 80, 'HiTime': 80, 
                    'EndTime': 80, 'HiAlt': 60, 'Mag_Rise': 60, 'Mag_High': 60, 'Mag_Set': 60, 'TLE1': 200, 'TLE2': 200}
    
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

def get_satellite_status(self, start_time_str, end_time_str, selected_date):
    """
    Bestemmer status for en satelit baseret på nuværende tid
    
    Args:
        start_time_str (str): StartTime i format 'HH:MM'
        end_time_str (str): EndTime i format 'HH:MM'
        selected_date (str): Datoen for satelitpassagen i format 'YYYY-MM-DD'
        
    Returns:
        str: 'passed', 'starting_soon', 'active', eller 'normal'
    """
    try:
        # Konverter strenge til datetime objekter
        current_datetime = datetime.now()
        
        # Parse den valgte dato
        selected_datetime = datetime.strptime(selected_date, '%Y-%m-%d')
        
        # Tjek om vi kigger på i dag
        if selected_datetime.date() != current_datetime.date():
            return 'normal'  # Hvis det ikke er i dag, vis normal farve
        
        # Parse tiderne - prøv først med sekunder, derefter uden
        try:
            start_time = datetime.strptime(start_time_str, '%H:%M:%S').time()
        except ValueError:
            start_time = datetime.strptime(start_time_str, '%H:%M').time()
        
        try:
            end_time = datetime.strptime(end_time_str, '%H:%M:%S').time()
        except ValueError:
            end_time = datetime.strptime(end_time_str, '%H:%M').time()
        
        # Kombiner dato og tid
        start_datetime = datetime.combine(selected_datetime.date(), start_time)
        end_datetime = datetime.combine(selected_datetime.date(), end_time)
        
        # Håndter tilfælde hvor end_time er efter midnat (næste dag)
        if end_time < start_time:
            end_datetime = end_datetime + timedelta(days=1)
        
        # Sammenlign med nuværende tid
        current_time = current_datetime
        
        # Tjek status
        if current_time > end_datetime:
            return 'passed'  # Passeret
        elif current_time >= start_datetime:
            return 'active'  # Aktiv nu
        elif (start_datetime - current_time).total_seconds() <= 300:  # 5 minutter = 300 sekunder
            return 'starting_soon'  # Starter snart
        else:
            return 'normal'  # Normal
            
    except (ValueError, TypeError):
        return 'normal'  # Hvis parsing fejler, returner normal
            
def fetch_satellites_threaded(self):
    """Starter satelit-hentning i separat tråd"""
    self.log_satellite_message("Starter satelit hentning...")
    threading.Thread(target=self.fetch_satellites, daemon=True).start()

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
        period = self.period_combo.get()
        username = self.username_entry.get()
        password = self.password_entry.get()
        utc_offset = float(self.utc_offset_entry.get())
        
        if not username or not password:
            self.log_satellite_message("❌ Manglende Space-Track login oplysninger")
            messagebox.showerror("Fejl", "Indtast Space-Track login oplysninger")
            return
        
        self.log_satellite_message(f"Henter data for {date_str}")
        self.log_satellite_message(f"Lokation: {lat:.4f}, {lng:.4f}")
        self.status_label.config(text="Henter satelitdata...")
        self.progress_var.set(20)
        
        # Kald dine funktioner
        self.df_merged, self.df_heavens = self.fetch_satellite_data_with_tle(
            date_str, username, password, lat, lng, period, utc_offset
        )

        self.log_satellite_message("Sorterer data efter starttid...")
        # Sorter data efter StartTime
        self.df_merged = self.sort_dataframe_by_starttime(self.df_merged)
        
        self.progress_var.set(90)
        
        # Opdater treeview
        self.log_satellite_message("Opdaterer satelitliste...")
        self.update_satellite_tree()
        
        self.progress_var.set(100)
        success_msg = f"Hentet {len(self.df_merged)} satellitter med TLE data (sorteret efter starttid)"
        self.status_label.config(text=success_msg)
        
    except Exception as e:
        error_msg = f"Fejl ved hentning: {str(e)}"
        self.log_satellite_message(f"❌ {error_msg}")
        messagebox.showerror("Fejl", error_msg)
        self.status_label.config(text="Fejl ved hentning af data")
    finally:
        self.progress_var.set(0)

def update_satellite_tree(self):
    """Opdater treeview med satelitdata og farvekodning"""
    # Ryd tidligere data
    for item in self.satellite_tree.get_children():
        self.satellite_tree.delete(item)
    
    if self.df_merged is not None:
        selected_date = self.date_entry.get()
        
        for _, row in self.df_merged.iterrows():
            values = (
                row.get('SatName', ''),
                row.get('NORAD', ''),
                row.get('StartTime', ''),
                row.get('HiTime', ''),
                row.get('EndTime', ''),
                row.get('HiAlt', ''),
                row.get('Magnitude_Rise', ''),
                row.get('Magnitude_High', ''),
                row.get('Magnitude_Set', ''),
                row.get('TLE1', '')[:50] + '...' if len(str(row.get('TLE1', ''))) > 50 else row.get('TLE1', ''),
                row.get('TLE2', '')[:50] + '...' if len(str(row.get('TLE2', ''))) > 50 else row.get('TLE2', '')
            )
            
            # Bestem farvekategori
            start_time = str(row.get('StartTime', ''))
            end_time = str(row.get('EndTime', ''))
            status = self.get_satellite_status(start_time, end_time, selected_date)
            
            # Indsæt række med korrekt farvetag
            self.satellite_tree.insert('', 'end', values=values, tags=(status,))

def save_satellite_list(self):
    """Gem satelitlisten til fil"""
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
        self.df_merged.to_csv(filename, index=False, sep=';')
        self.log_satellite_message("✅ Satelitliste gemt succesfuldt")
        messagebox.showinfo("Gemt", f"Satelitliste gemt som: {filename}")
    else:
        self.log_satellite_message("❌ Gem operation afbrudt")

def clear_satellite_list(self):
    """Ryd satelitlisten"""
    self.log_satellite_message("Rydder satelitliste...")
    for item in self.satellite_tree.get_children():
        self.satellite_tree.delete(item)
    self.df_merged = None
    self.df_heavens = None
    self.log_satellite_message("✅ Satelitliste ryddet")
    self.status_label.config(text="Liste ryddet")

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
        self.status_label.config(text="Indlæser CSV-fil...")
        self.progress_var.set(20)
        
        # Prøv forskellige separatorer
        separators = [';', ',', '\t']
        df_loaded = None
        
        for sep in separators:
            try:
                df_test = pd.read_csv(filename, sep=sep, nrows=5)
                # Tjek om vi har de forventede kolonner
                expected_cols = ['SatName', 'NORAD', 'StartTime', 'HiTime', 'EndTime']
                if any(col in df_test.columns for col in expected_cols):
                    df_loaded = pd.read_csv(filename, sep=sep)
                    self.status_label.config(text=f"CSV indlæst med separator '{sep}'")
                    break
            except:
                continue
        
        if df_loaded is None:
            # Hvis automatisk detektion fejler, prøv standard CSV
            df_loaded = pd.read_csv(filename)
        
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
        success_msg = f"CSV-fil indlæst: {len(df_loaded)} satellitter (sorteret efter starttid)"
        self.log_satellite_message(f"✅ {success_msg}")
        self.status_label.config(text=success_msg)
        
        messagebox.showinfo("Succes", f"CSV-fil indlæst med {len(df_loaded)} satellitter")
        
    except Exception as e:
        error_msg = f"Kunne ikke indlæse CSV-fil: {str(e)}"
        self.log_satellite_message(f"❌ {error_msg}")
        messagebox.showerror("Fejl", error_msg)
        self.status_label.config(text="Fejl ved indlæsning af CSV-fil")
    finally:
        self.progress_var.set(0)

def validate_csv_data(self, df):
    """Validerer og renser CSV-data for at sikre kompatibilitet"""
    try:
        # Standardiser kolonnenavne (case-insensitive mapping)
        column_mapping = {
            'satname': 'SatName',
            'satellite': 'SatName',
            'name': 'SatName',
            'norad': 'NORAD',
            'norad_id': 'NORAD',
            'starttime': 'StartTime',
            'start_time': 'StartTime',
            'hitime': 'HiTime',
            'hi_time': 'HiTime',
            'endtime': 'EndTime',
            'end_time': 'EndTime',
            'hialt': 'HiAlt',
            'hi_alt': 'HiAlt',
            'altitude': 'HiAlt',
            'magnitude': 'Magnitude_High',  # Standard magnitude bliver High magnitude
            'mag': 'Magnitude_High',
            'magnitude_rise': 'Magnitude_Rise',
            'mag_rise': 'Magnitude_Rise',
            'magnitude_high': 'Magnitude_High',
            'mag_high': 'Magnitude_High',
            'magnitude_set': 'Magnitude_Set',
            'mag_set': 'Magnitude_Set',
            'tle1': 'TLE1',
            'tle_1': 'TLE1',
            'tle2': 'TLE2',
            'tle_2': 'TLE2'
        }
        
        # Omdøb kolonner
        df_renamed = df.copy()
        for old_col in df.columns:
            standard_name = column_mapping.get(old_col.lower())
            if standard_name:
                df_renamed = df_renamed.rename(columns={old_col: standard_name})
        
        # Sikr at vi har magnitude kolonne(r)
        if 'Magnitude_Rise' not in df_renamed.columns and 'Magnitude_High' in df_renamed.columns:
            df_renamed['Magnitude_Rise'] = df_renamed['Magnitude_High']
        if 'Magnitude_Set' not in df_renamed.columns and 'Magnitude_High' in df_renamed.columns:
            df_renamed['Magnitude_Set'] = df_renamed['Magnitude_High']
        
        # Sikr at vi har minimumskolonner
        required_cols = ['SatName', 'NORAD']
        missing_cols = [col for col in required_cols if col not in df_renamed.columns]
        
        if missing_cols:
            # Prøv at oprette manglende kolonner med standardværdier
            for col in missing_cols:
                if col == 'SatName':
                    df_renamed['SatName'] = f"Satellite_{df_renamed.index}"
                elif col == 'NORAD':
                    df_renamed['NORAD'] = range(1, len(df_renamed) + 1)
        
        # Sikr at NORAD er numerisk
        if 'NORAD' in df_renamed.columns:
            df_renamed['NORAD'] = pd.to_numeric(df_renamed['NORAD'], errors='coerce')
        
        # Fjern rækker med tomme satelitnavne
        df_renamed = df_renamed.dropna(subset=['SatName'])
        
        return df_renamed
        
    except Exception as e:
        # Hvis validering fejler, returner original DataFrame
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
    except Exception as e:
        raise Exception(f"Chrome WebDriver fejl: {e}")
    
    try:
        # Step 1: Set location via location.php form (always use UTC in browser, will convert locally)
        driver.get("https://in-the-sky.org/location.php")
        time.sleep(1)
        
        tz_str = "+00:00"  # Always fetch in UTC, convert locally
        driver.execute_script(f"""
            document.querySelector('input[name="latitude"]').value = '{lat}';
            document.querySelector('input[name="longitude"]').value = '{lng}';
            document.querySelector('input[name="timezone"]').value = '{tz_str}';
        """)
        time.sleep(0.5)
        
        driver.execute_script("""
            document.querySelectorAll('input[type="submit"]')
                .forEach(btn => btn.value.includes('custom') && btn.click());
        """)
        time.sleep(2)
        
        # Step 2: Fetch satpasses data
        url = f"https://in-the-sky.org/satpasses.php?day={day}&month={month}&year={year}&mag=500&anysat=v0&group=1&s="
        driver.get(url)
        time.sleep(3)
        
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

def fetch_satellite_data_selenium(self, date, lat=55.781553, lng=12.514595, period='morning', utc_offset=0):
    """
    Henter satellitdata fra in-the-sky.org og konverterer til Heavens-Above format
    
    Parameters:
    -----------
    date : str
        Dato i format 'YYYY-MM-DD' eller 'DD-MM-YYYY'
    lat : float
        Breddegrad
    lng : float
        Længdegrad
    period : str
        Ikke brugt (for backward compatibility) - in-the-sky.org returnerer alle dage
    utc_offset : float
        UTC offset i timer (f.eks. -2 for CEST, +1 for CET)
    
    Returns:
    --------
    pd.DataFrame
        DataFrame med kolonner: SatName, Magnitude_Rise, Magnitude_High, Magnitude_Set,
                                StartTime, StartAlt, StartAz, HiTime, HiAlt, HiAz,
                                EndTime, EndAlt, EndAz, NORAD
        (Bemærk: 3 separate magnitude-værdier i stedet for 1)
    """
    try:
        # Hent data fra in-the-sky.org
        df_inthesky = fetch_satellites_inthesky(date, lat, lng, utc_offset=utc_offset)
        
        if df_inthesky is None or len(df_inthesky) == 0:
            raise Exception("Ingen satellitdata hentet fra in-the-sky.org")
        
        # Konverter til Heavens-Above format, men behold alle 3 magnitude-værdier
        df = pd.DataFrame({
            'SatName': df_inthesky['SatName'],
            'Magnitude_Rise': df_inthesky['RiseMagnitude'],
            'Magnitude_High': df_inthesky['HighMagnitude'],
            'Magnitude_Set': df_inthesky['SetMagnitude'],
            'StartTime': df_inthesky['RiseTime'],
            'StartAlt': df_inthesky['RiseAltitude'],
            'StartAz': df_inthesky['RiseDirection'],
            'HiTime': df_inthesky['HighTime'],
            'HiAlt': df_inthesky['HighAltitude'],
            'HiAz': df_inthesky['HighDirection'],
            'EndTime': df_inthesky['SetTime'],
            'EndAlt': df_inthesky['SetAltitude'],
            'EndAz': df_inthesky['SetDirection'],
            'NORAD': df_inthesky['NORAD']
        })
        
        # Rens data
        for col in ['StartAlt', 'StartAz', 'HiAlt', 'HiAz', 'EndAlt', 'EndAz']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace('°', '', regex=False).str.strip()
        
        # Konverter dansk retningsangivelser til engelsk
        direction_map = {'Ø': 'E', 'V': 'W'}
        for col in ['StartAz', 'HiAz', 'EndAz']:
            if col in df.columns:
                for dk, en in direction_map.items():
                    df[col] = df[col].str.replace(dk, en, regex=False)
        
        df = df.reset_index(drop=True)
        return df
        
    except Exception as e:
        raise Exception(f"Fejl ved hentning af satellitdata fra in-the-sky.org: {str(e)}")

def fetch_satellite_data_with_tle(self, date, username, password, lat=55.781553, lng=12.514595, period='morning', utc_offset=2):
    """Hovedfunktion der kombinerer in-the-sky.org og Space-Track data"""
    self.progress_var.set(30)
    self.log_satellite_message("Henter aktive TLE'er fra Space-Track...")
    df_TLE = self.fetch_active_tles(username, password)
    self.log_satellite_message(f"Hentede {len(df_TLE)} aktive TLE'er fra Space-Track")

    df_TLE['NORAD_ID'] = pd.to_numeric(df_TLE['NORAD_ID'], errors='coerce')
    
    self.progress_var.set(60)

    self.log_satellite_message(f"Henter satellitdata fra in-the-sky.org (UTC offset: {utc_offset})...")
    df_heavens = self.fetch_satellite_data_selenium(date, lat, lng, period, utc_offset=utc_offset)
    self.log_satellite_message(f"Hentede {len(df_heavens)} satellitter fra in-the-sky.org")

    # Bemærk: UTC offset er allerede anvendt i fetch_satellite_data_selenium -> fetch_satellites_inthesky
    # Så vi skal IKKE tilføje det igen her
    
    self.progress_var.set(80)
    self.log_satellite_message("Sammenfletter in-the-sky.org data med TLE'er...")
    df_merged = df_heavens.merge(df_TLE, left_on='NORAD', right_on='NORAD_ID', how='left')
    df_merged = df_merged.drop(columns=['NORAD_ID', 'Name'])
    df_merged = df_merged.reset_index(drop=True)
    df_merged = df_merged.dropna(subset=['TLE1'])
    
    return df_merged, df_heavens

def open_file(self):
    """Opdateret open_file metode med CSV-support"""
    file_types = [
        ("CSV files", "*.csv"),
        ("All files", "*.*")
    ]
    
    filename = filedialog.askopenfilename(
        title="Åbn fil",
        filetypes=file_types
    )
    
    if filename:
        if filename.endswith('.csv'):
            self.load_csv_file_direct(filename)
        else:
            messagebox.showinfo("Info", f"Åbnede fil: {filename}")

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
        
        # Sorter data efter StartTime
        df_loaded = self.sort_dataframe_by_starttime(df_loaded)
        
        # Opdater variabler
        self.df_merged = df_loaded
        
        # Opdater display
        self.update_satellite_tree()
        
        self.status_label.config(text=f"CSV-fil indlæst: {len(df_loaded)} satellitter (sorteret efter starttid)")
        messagebox.showinfo("Succes", f"CSV-fil indlæst med {len(df_loaded)} satellitter")
        
    except Exception as e:
        messagebox.showerror("Fejl", f"Kunne ikke indlæse CSV-fil:\n{str(e)}")

def save_file(self):
    messagebox.showinfo("Gem", "Gem fil funktion")