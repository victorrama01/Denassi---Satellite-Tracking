from tkinter import Menu, ttk

def create_menu(self):
    """Opretter menubar"""
    menubar = Menu(self.root)
    self.root.config(menu=menubar)
    
    # File menu
    file_menu = Menu(menubar, tearoff=0)
    menubar.add_cascade(label="File", menu=file_menu)
    file_menu.add_command(label="Open", command=self.open_file)
    file_menu.add_command(label="Save", command=self.save_file)
    file_menu.add_separator()
    file_menu.add_command(label="Exit", command=self.root.quit)
    
    # Om menu
    help_menu = Menu(menubar, tearoff=0)
    menubar.add_cascade(label="Om", menu=help_menu)
    help_menu.add_command(label="Om denne applikation", command=self.show_about)

def create_widgets(self):
    """Opretter alle widgets"""
    
    # UR I TOPPEN AF PROGRAMMET - SYNLIGT PÅ ALLE TABS
    top_frame = ttk.Frame(self.root)
    top_frame.pack(fill='x', padx=10, pady=5)
    
    # Titel til venstre
    title_label = ttk.Label(top_frame, text="Satellite Tracking System", font=('Arial', 14, 'bold'))
    title_label.pack(side='left')
    
    # Ur til højre
    clock_label = ttk.Label(
        top_frame, 
        textvariable=self.clock_var, 
        font=('Arial', 14, 'bold'),
        foreground='darkblue'
    )
    clock_label.pack(side='right')
    
    ttk.Label(top_frame, text="Tid:", font=('Arial', 10)).pack(side='right', padx=(0, 5))
    
    # Separator linje
    separator = ttk.Separator(self.root, orient='horizontal')
    separator.pack(fill='x', padx=10, pady=5)
    
    # Hovedcontainer med tabs
    notebook = ttk.Notebook(self.root)
    notebook.pack(fill='both', expand=True, padx=10, pady=10)
    
    # Tab 1: Kameraindstillinger
    self.create_kameraindstillinger_tab(notebook)
    
    # Tab 2: Hent Satelitlister
    self.create_satellite_tab(notebook)
    
    # Tab 3: LeapFrog Observation
    self.create_leapfrog_tab(notebook)
    
    # Tab 4: Tracking Observation
    self.create_tracking_tab(notebook)
    
    # Tab 5: Billede Analyse
    self.create_image_analysis_tab(notebook)
    
    # Tab 6: Billedgennemgang
    self.create_image_review_tab(notebook)
    
    # Tab 7: Beregn TLE
    self.create_calculate_tle_tab(notebook)

def update_clock(self):
    """Opdaterer uret og farvekodning hvert sekund"""
    from datetime import datetime
    current_time = datetime.now().strftime('%H:%M:%S')
    self.clock_var.set(current_time)
    
    # Opdater farvekodning hvis vi har satelitdata
    if self.df_merged is not None:
        self.update_satellite_colors()
    
    # Planlæg næste opdatering om 1000ms (1 sekund)
    self.root.after(1000, self.update_clock)

def update_satellite_colors(self):
    """Opdaterer kun farvekodningen uden at genopbygge hele listen"""
    if self.df_merged is None:
        return
        
    selected_date = self.date_entry.get()
    
    # Gennemgå alle eksisterende rækker i treeview
    for item in self.satellite_tree.get_children():
        values = self.satellite_tree.item(item, 'values')
        if len(values) >= 5:  # Sikr at vi har start og end tid
            start_time = values[2]  # StartTime kolonne
            end_time = values[4]    # EndTime kolonne
            
            # Beregn ny status
            status = self.get_satellite_status(start_time, end_time, selected_date)
            
            # Opdater farvetag for denne række
            self.satellite_tree.item(item, tags=(status,))

def sort_dataframe_by_starttime(self, df):
    """Sorterer DataFrame efter StartTime"""
    import pandas as pd
    if df is None or df.empty:
        return df
        
    try:
        # Konverter StartTime til datetime for korrekt sortering
        df_sorted = df.copy()
        
        # Sikr at StartTime eksisterer
        if 'StartTime' in df_sorted.columns:
            # Konverter til datetime objekt for korrekt sortering - prøv først med sekunder, derefter uden
            df_sorted['StartTime_dt'] = pd.to_datetime(df_sorted['StartTime'], format='%H:%M:%S', errors='coerce')
            # Hvis parsing fejlede (NaT værdier), prøv uden sekunder
            if df_sorted['StartTime_dt'].isna().all():
                df_sorted['StartTime_dt'] = pd.to_datetime(df_sorted['StartTime'], format='%H:%M', errors='coerce')
            
            # Sorter efter tiden
            df_sorted = df_sorted.sort_values('StartTime_dt')
            
            # Fjern hjælpekolonnen
            df_sorted = df_sorted.drop(columns=['StartTime_dt'])
            
            # Reset index
            df_sorted = df_sorted.reset_index(drop=True)
            
        return df_sorted
        
    except Exception as e:
        print(f"Fejl ved sortering: {e}")
        return df
