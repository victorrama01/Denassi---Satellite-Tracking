"""Module for image review tab functionality"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
from PIL import Image, ImageTk
from datetime import datetime


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
