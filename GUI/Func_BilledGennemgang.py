"""Module for image review tab functionality"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
from PIL import Image, ImageTk
from datetime import datetime


def select_review_directory(self):
    """Vælg mappe til billedgennemgang"""
    directory = filedialog.askdirectory(title="Vælg mappe med PNG-billeder")
    if directory:
        self.review_directory = directory
        self.review_dir_entry.delete(0, tk.END)
        self.review_dir_entry.insert(0, directory)
        self.load_review_images()


def load_review_images(self):
    """Indlæs PNG-billeder fra mappen"""
    if not self.review_directory:
        return
    
    try:
        self.review_files = [f for f in os.listdir(self.review_directory) 
                            if f.lower().endswith('.png')]
        self.review_index = 0
        
        self.review_log_message(f"Fundet {len(self.review_files)} PNG-billeder")
        
        if self.review_files:
            self.show_review_image()
        else:
            self.review_image_label.config(text="Ingen PNG-billeder fundet")
            self.review_info_label.config(text="")
    except Exception as e:
        self.review_log_message(f"Fejl ved indlæsning: {e}")


def show_review_image(self):
    """Vis aktuelt billede"""
    if self.review_index >= len(self.review_files):
        self.review_image_label.config(text="Alle billeder gennemgået ✓")
        self.review_info_label.config(text="")
        self.review_keep_btn.config(state='disabled')
        self.review_delete_btn.config(state='disabled')
        return
    
    self.review_keep_btn.config(state='normal')
    self.review_delete_btn.config(state='normal')
    
    filename = self.review_files[self.review_index]
    filepath = os.path.join(self.review_directory, filename)
    
    # Opdater info
    self.review_info_label.config(
        text=f"{self.review_index + 1}/{len(self.review_files)} — {filename}"
    )
    
    try:
        # Indlæs PNG-billede
        img = Image.open(filepath)
        
        # Konverter til RGB hvis nødvendigt
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Downscale billedet
        original_size = img.size
        new_size = (max(1, original_size[0] // self.review_downscale), 
                   max(1, original_size[1] // self.review_downscale))
        img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        # Konverter til PhotoImage
        photo = ImageTk.PhotoImage(img)
        self.review_image_label.config(image=photo, text="")
        self.review_image_label.image = photo
        
    except Exception as e:
        self.review_image_label.config(text=f"Fejl ved indlæsning:\n{e}")
        self.review_log_message(f"Fejl ved indlæsning af {filename}: {e}")
        self.review_next_image()


def review_keep_file(self):
    """Behold billede og gå til næste"""
    self.review_log_message(f"Beholdtes: {self.review_files[self.review_index]}")
    self.review_next_image()


def review_delete_file(self):
    """Slet PNG og tilsvarende FITS-fil"""
    if self.review_index >= len(self.review_files):
        return
    
    filename = self.review_files[self.review_index]
    png_filepath = os.path.join(self.review_directory, filename)
    
    # Find tilsvarende FITS-fil - prøv først med _plot.png erstatning, derefter direkte .png erstatning
    fits_filename = filename.replace('_plot.png', '.fits')
    if fits_filename == filename:  # Hvis erstatning ikke fungerede, prøv direkte .png -> .fits
        fits_filename = filename.replace('.png', '.fits')
    
    fits_filepath = os.path.join(self.review_directory, fits_filename)
    
    files_deleted = []
    errors = []
    
    # Slet PNG-filen
    try:
        os.remove(png_filepath)
        files_deleted.append(filename)
        self.review_log_message(f"Slettede PNG: {filename}")
    except Exception as e:
        errors.append(f"PNG sletning fejlede: {e}")
        self.review_log_message(f"FEJL ved sletning af PNG: {e}")
    
    # Slet FITS-filen hvis den eksisterer
    if os.path.exists(fits_filepath):
        try:
            os.remove(fits_filepath)
            files_deleted.append(fits_filename)
            self.review_log_message(f"Slettede FITS: {fits_filename}")
        except Exception as e:
            errors.append(f"FITS sletning fejlede: {e}")
            self.review_log_message(f"FEJL ved sletning af FITS: {e}")
    else:
        # Prøv at finde lignende FITS-filer
        try:
            possible_fits = [f for f in os.listdir(self.review_directory) 
                            if f.lower().endswith('.fits') and filename.split('_')[0] in f]
            if possible_fits:
                self.review_log_message(f"FITS ikke fundet. Mulige: {', '.join(possible_fits)}")
        except:
            pass
    
    self.review_next_image()


def review_next_image(self):
    """Gå til næste billede"""
    self.review_index += 1
    self.show_review_image()


def review_log_message(self, message):
    """Tilføj meddelelse til log"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    self.review_log_text.insert(tk.END, f"[{timestamp}] {message}\n")
    self.review_log_text.see(tk.END)
    self.review_log_text.update()


def create_image_review_tab(self, notebook):
    """Tab til billedgennemgang og håndtering af PNG-billeder med FITS-fil sletning"""
    review_frame = ttk.Frame(notebook)
    notebook.add(review_frame, text="Billedgennemgang")
    
    # Hovedcontainer
    main_frame = ttk.Frame(review_frame)
    main_frame.pack(fill='both', expand=True, padx=10, pady=10)
    
    # Venstre side: Billedvisning
    left_frame = ttk.Frame(main_frame)
    left_frame.pack(side='left', fill='both', expand=True, padx=(0, 5))
    
    # Øverst: Mappevælger
    dir_frame = ttk.LabelFrame(left_frame, text="Mappevælger")
    dir_frame.pack(fill='x', pady=(0, 10))
    
    self.review_dir_entry = ttk.Entry(dir_frame, width=50)
    self.review_dir_entry.pack(side='left', fill='x', expand=True, padx=5, pady=5)
    ttk.Button(dir_frame, text="Vælg Mappe", 
              command=self.select_review_directory).pack(side='left', padx=5, pady=5)
    
    # Billedvisning
    image_frame = ttk.LabelFrame(left_frame, text="Billedvisning")
    image_frame.pack(fill='both', expand=True, pady=(0, 10))
    
    self.review_image_label = ttk.Label(image_frame, text="Intet billede indlæst", 
                                       background='#f0f0f0')
    self.review_image_label.pack(fill='both', expand=True, padx=10, pady=10)
    
    # Billedinfo
    self.review_info_label = ttk.Label(left_frame, text="", justify='center')
    self.review_info_label.pack(pady=5)
    
    # Kontrolknapper (nederst på venstre side)
    button_frame = ttk.Frame(left_frame)
    button_frame.pack(fill='x', pady=10)
    
    self.review_keep_btn = ttk.Button(button_frame, text="Behold ✓", 
                                     command=self.review_keep_file, width=20)
    self.review_keep_btn.pack(side='left', padx=5, pady=5, fill='both', expand=True)
    
    self.review_delete_btn = ttk.Button(button_frame, text="Slet ✗", 
                                       command=self.review_delete_file, width=20)
    self.review_delete_btn.pack(side='left', padx=5, pady=5, fill='both', expand=True)
    
    # Højre side: Log
    right_frame = ttk.Frame(main_frame)
    right_frame.pack(side='right', fill='both', expand=False, padx=(5, 0))
    right_frame.pack_propagate(False)
    right_frame.configure(width=300)
    
    log_frame = ttk.LabelFrame(right_frame, text="Gennemgang Log")
    log_frame.pack(fill='both', expand=True)
    
    # Log text widget med scrollbar
    log_container = ttk.Frame(log_frame)
    log_container.pack(fill='both', expand=True, padx=5, pady=5)
    
    self.review_log_text = tk.Text(log_container, width=35, wrap='word')
    review_log_scrollbar = ttk.Scrollbar(log_container, orient='vertical', 
                                        command=self.review_log_text.yview)
    self.review_log_text.configure(yscrollcommand=review_log_scrollbar.set)
    
    review_log_scrollbar.pack(side='right', fill='y')
    self.review_log_text.pack(side='left', fill='both', expand=True)
    
    # Clear log button
    ttk.Button(log_frame, text="Ryd Log", 
              command=lambda: self.review_log_text.delete(1.0, tk.END)).pack(pady=2)
