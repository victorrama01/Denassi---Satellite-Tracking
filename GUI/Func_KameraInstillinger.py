import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta

def log_camera_message(self, message):
    """Tilføj besked til kamera loggen med tidsstempel"""
    try:
        if hasattr(self, 'camera_log_text'):
            timestamp = datetime.now().strftime('%H:%M:%S')
            log_entry = f"[{timestamp}] {message}\n"
            self.camera_log_text.insert(tk.END, log_entry)
            self.camera_log_text.see(tk.END)  # Scroll til bunden
    except:
        pass  # Ignorer fejl hvis log ikke er tilgængelig

def log_satellite_message(self, message):
    """Tilføj besked til satelit loggen med tidsstempel"""
    try:
        if hasattr(self, 'satellite_log_text'):
            timestamp = datetime.now().strftime('%H:%M:%S')
            log_entry = f"[{timestamp}] {message}\n"
            self.satellite_log_text.insert(tk.END, log_entry)
            self.satellite_log_text.see(tk.END)  # Scroll til bunden
    except:
        pass  # Ignorer fejl hvis log ikke er tilgængelig

def connect_camera(self):
    """Tilslut til Moravian kamera"""
    try:
        from moravian_camera_official import MoravianCameraOfficial
        MORAVIAN_AVAILABLE = True
    except ImportError:
        MORAVIAN_AVAILABLE = False
    
    self.log_camera_message("Forsøger at tilslutte Moravian kamera...")
    try:
        if not MORAVIAN_AVAILABLE:
            self.log_camera_message("FEJL: Moravian kamera support ikke tilgængelig")
            messagebox.showerror("Fejl", "Moravian kamera support ikke tilgængelig.\n\nSørg for at moravian_camera_official.py er tilgængelig og cXusb.dll er installeret.")
            return
        
        if self.moravian_camera is not None:
            self.log_camera_message("Kamera er allerede tilsluttet")
            messagebox.showwarning("Allerede tilsluttet", "Kamera er allerede tilsluttet")
            return
        
        # Opret og tilslut kamera
        self.moravian_camera = MoravianCameraOfficial()
        
        if self.moravian_camera.connect():
            self.camera_connected = True
            self.camera_status_label.config(text="Tilsluttet", foreground='green')
            
            # Hent kamera info og opdater GUI
            update_camera_info(self)
            
            self.log_camera_message("✅ Moravian kamera tilsluttet succesfuldt!")

        else:
            self.moravian_camera = None
            self.log_camera_message("❌ Kunne ikke tilslutte til Moravian kamera")
            messagebox.showerror("Fejl", "Kunne ikke tilslutte til Moravian kamera")
            
    except Exception as e:
        self.moravian_camera = None
        self.camera_connected = False
        self.log_camera_message(f"❌ Fejl ved tilslutning: {str(e)}")
        messagebox.showerror("Fejl", f"Fejl ved tilslutning til kamera: {str(e)}")

def disconnect_camera(self):
    """Afbryd forbindelse til Moravian kamera"""
    self.log_camera_message("Afbryder kamera forbindelse...")
    try:
        if self.moravian_camera is not None:
            self.moravian_camera.disconnect()
            self.moravian_camera = None
        
        self.camera_connected = False
        self.camera_status_label.config(text="Ikke tilsluttet", foreground='red')
        self.current_temp_label.config(text="N/A")
        self.filter_combo['values'] = []
        self.gain_scale.configure(to=100)
        
        self.log_camera_message("✅ Kamera forbindelse afbrudt")

        
    except Exception as e:
        self.log_camera_message(f"❌ Fejl ved afbrydelse: {str(e)}")
        messagebox.showerror("Fejl", f"Fejl ved afbrydelse af kamera: {str(e)}")

def update_camera_info(self):
    """Opdater kamera information i GUI"""
    try:
        if not self.camera_connected or self.moravian_camera is None:
            return
        
        # Hent kamera info
        info = self.moravian_camera.get_camera_info()
        
        # Opdater status
        camera_desc = info.get('description', 'Unknown Camera')
        self.camera_status_label.config(text=f"Tilsluttet: {camera_desc}", foreground='green')
        
        # Opdater temperatur
        current_temp = info.get('temperature', None)
        if current_temp is not None:
            self.current_temp_label.config(text=f"{current_temp:.1f}°C")
        
        # Opdater gain range
        max_gain = info.get('max_gain', 100)
        if max_gain > 0:
            self.gain_scale.configure(to=max_gain)
        
        # Opdater filter liste
        filters = info.get('filters', [])
        if filters:
            filter_names = []
            for filter_info in filters:
                name = filter_info.get('name', f"Filter {filter_info.get('index', '?')}")
                filter_names.append(f"[{filter_info.get('index', '?')}] {name}")
            
            self.filter_combo['values'] = filter_names
            if filter_names and not self.selected_filter.get():
                self.filter_combo.current(0)
        
    except Exception as e:
        print(f"Fejl ved opdatering af kamera info: {str(e)}")

def update_temperature_display(self):
    """Opdater temperatur display"""
    try:
        if self.camera_connected and self.moravian_camera is not None:
            temp = self.moravian_camera.get_temperature()
            if temp is not None:
                self.current_temp_label.config(text=f"{temp:.1f}°C")
    except:
        pass

def update_gain_label(self, value):
    """Opdater gain værdi label når slider bevæges"""
    try:
        gain_value = int(float(value))
        self.gain_value_label.config(text=str(gain_value))
        
        # Opdater manual entry felt
        self.manual_gain_entry.delete(0, tk.END)
        self.manual_gain_entry.insert(0, str(gain_value))
    except:
        pass

def set_camera_gain(self):
    """Sæt kamera gain"""
    try:
        if not self.camera_connected or self.moravian_camera is None:
            messagebox.showwarning("Ikke tilsluttet", "Tilslut kamera først")
            return
        
        # Prøv at få gain fra manual entry først, ellers brug slider
        manual_value = self.manual_gain_entry.get().strip()
        if manual_value:
            try:
                gain_value = int(manual_value)
                # Opdater slider til at matche manual input
                self.camera_gain.set(gain_value)
            except ValueError:
                messagebox.showerror("Fejl", "Ugyldig gain værdi i manuelt felt")
                return
        else:
            gain_value = int(self.camera_gain.get())
        
        # Validér gain range
        info = self.moravian_camera.get_camera_info()
        max_gain = info.get('max_gain', 100)
        
        if gain_value < 0 or gain_value > max_gain:
            messagebox.showerror("Fejl", f"Gain skal være mellem 0 og {max_gain}")
            return
        
        if self.moravian_camera.set_gain(gain_value):
            self.log_camera_message(f"✅ Gain sat til {gain_value}")
        else:
            messagebox.showerror("Fejl", f"Kunne ikke sætte gain til {gain_value}")
            self.log_camera_message(f"❌ Kunne ikke sætte gain til {gain_value}")
            
    except Exception as e:
        messagebox.showerror("Fejl", f"Fejl ved sætning af gain: {str(e)}")

def set_camera_binning(self):
    """Sæt kamera binning"""
    try:
        if not self.camera_connected or self.moravian_camera is None:
            messagebox.showwarning("Ikke tilsluttet", "Tilslut kamera først")
            return
        
        x_binning = int(self.camera_binning_x.get())
        y_binning = int(self.camera_binning_y.get())
        
        # Validér binning værdier
        if x_binning < 1 or x_binning > 8 or y_binning < 1 or y_binning > 8:
            messagebox.showerror("Fejl", "Binning skal være mellem 1 og 8")
            return
        
        self.moravian_camera.set_binning(x_binning, y_binning)
        self.log_camera_message(f"✅ Binning sat til {x_binning}x{y_binning}")
            
    except Exception as e:
        messagebox.showerror("Fejl", f"Fejl ved sætning af binning: {str(e)}")

def set_camera_filter(self):
    """Sæt kamera filter"""
    try:
        if not self.camera_connected or self.moravian_camera is None:
            messagebox.showwarning("Ikke tilsluttet", "Tilslut kamera først")
            return
        
        # Hent filter info
        info = self.moravian_camera.get_camera_info()
        filters = info.get('filters', [])
        
        if not filters:
            messagebox.showwarning("Ingen filtre", "Ingen filter hjul fundet på dette kamera")
            return
        
        selected_index = self.filter_combo.current()
        if selected_index < 0:
            messagebox.showwarning("Intet valg", "Vælg et filter først")
            return
        
        filter_info = filters[selected_index]
        filter_index = filter_info.get('index', selected_index)
        filter_name = filter_info.get('name', f"Filter {filter_index}")
        
        if self.moravian_camera.set_filter(filter_index):
            self.log_camera_message(f"✅ Filter skiftet til: [{filter_index}] {filter_name}")
        else:
            messagebox.showerror("Fejl", f"Kunne ikke skifte til filter {filter_index}")
            
    except Exception as e:
        messagebox.showerror("Fejl", f"Fejl ved sætning af filter: {str(e)}")

def take_test_image(self):
    """Tag et testbillede med 1 sekunds eksponering og fuld FITS header"""
    self.log_camera_message("Forbereder testbillede...")
    try:
        # Tjek om kamera er tilgængeligt
        camera = get_camera_for_observation(self)
        if camera is None:
            self.log_camera_message("❌ Intet kamera tilgængeligt til testbillede")
            messagebox.showerror("Fejl", "Intet kamera tilgængeligt. Tilslut et kamera først.")
            return
        
        # Vis status at vi tager et billede
        status_msg = "Tager testbillede (1s)..."
        self.log_camera_message("Tager testbillede med 1s eksponering...")
        self.root.update_idletasks()
        
        # Exposure indstillinger
        exposure_time = 1.0  # 1 sekund
        
        # Tag billede
        if camera is self.moravian_camera and self.moravian_camera is not None:  # Moravian kamera
            binning_x = self.camera_binning_x.get()
            binning_y = self.camera_binning_y.get()
            
            # Sæt binning før billede
            camera.set_binning(binning_x, binning_y)
            
            # Tag billede med Moravian kamera
            image_data = camera.take_image(exposure_time)
            
            if image_data is None:
                messagebox.showerror("Fejl", "Kunne ikke tage billede med Moravian kamera")
                return
                
            # Hent kamera info til FITS header
            camera_info = camera.get_camera_info()
        
        # Timestamps for FITS header
        from datetime import timezone
        import pytz
        
        utc_time = datetime.now(timezone.utc)
        exposure_start_time = utc_time
        exposure_end_time = datetime.now(timezone.utc)
        
        # Teleskop information (hvis tilgængeligt)
        try:
            if self.pw4_client:
                pw4_status = self.pw4_client.status()
                ra_hours = pw4_status.mount.ra_j2000_hours
                dec_degrees = pw4_status.mount.dec_j2000_degs
                alt_degrees = pw4_status.mount.altitude_degs
                az_degrees = pw4_status.mount.azimuth_degs
            else:
                pw4_status = None
                ra_hours = None
                dec_degrees = None
                alt_degrees = None
                az_degrees = None
        except:
            pw4_status = None
            ra_hours = None
            dec_degrees = None
            alt_degrees = None
            az_degrees = None
        
        # Hent filter information
        filter_name = get_current_filter_name(self)
        
        # Opret FITS header
        header = create_standard_fits_header(
            self,
            obstype="TEST",
            sat_name="TESTBILLEDE",
            exposure_start_time=exposure_start_time,
            exposure_end_time=exposure_end_time,
            exposure_time=exposure_time,
            tle1="",
            tle2="",
            norad_id="",
            camera=camera_info,
            pw4_status=pw4_status,
            ra_hours=ra_hours,
            dec_degrees=dec_degrees,
            alt_degrees=alt_degrees,
            az_degrees=az_degrees,
            image_width=image_data.shape[1] if len(image_data.shape) > 1 else len(image_data),
            image_height=image_data.shape[0] if len(image_data.shape) > 0 else 1,
            x_binning=camera_info.get('BinX', 1),
            y_binning=camera_info.get('BinY', 1),
            filter_name=filter_name
        )
        
        # Gem som FITS fil
        from astropy.io import fits
        import numpy as np
        import os
        
        # Opret HDU
        hdu = fits.PrimaryHDU(data=np.array(image_data), header=header)
        
        # Generer filnavn med timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"testbillede_{timestamp}.fits"
        
        # Gem til samme folder som GUI
        filepath = os.path.join(os.path.dirname(__file__), filename)
        hdu.writeto(filepath, overwrite=True)
        
        self.log_camera_message(f"✅ Testbillede gemt som: {filename}")
        messagebox.showinfo("Succes", 
                           f"Testbillede gemt som:\n{filename}\n\n"
                           f"Eksponering: {exposure_time}s\n"
                           f"Størrelse: {image_data.shape if hasattr(image_data, 'shape') else 'N/A'}\n"
                           f"Temperatur: {camera_info.get('Temperature', 'N/A')}°C")
        
    except Exception as e:
        self.log_camera_message(f"❌ Fejl ved testbillede: {str(e)}")
        messagebox.showerror("Fejl", f"Fejl ved testbillede: {str(e)}")
        import traceback
        print(f"Testbillede fejl: {traceback.format_exc()}")

def get_camera_for_observation(self):
    """Hent kamera til brug i observationer - returnerer None hvis ikke tilgængelig"""
    if self.camera_connected and self.moravian_camera is not None:
        return self.moravian_camera
    return None

def get_current_filter_name(self):
    """Hent navn på det aktuelt valgte filter"""
    try:
        if self.camera_connected and self.moravian_camera is not None:
            # Hent filter info fra Moravian kamera
            info = self.moravian_camera.get_camera_info()
            filters = info.get('filters', [])
            
            if filters:
                # Prøv at hente aktuel filter position fra kamera
                current_filter = info.get('current_filter')
                if current_filter is not None:
                    # Find filter navn baseret på position
                    for filter_info in filters:
                        if filter_info.get('index') == current_filter:
                            return f"[{current_filter}] {filter_info.get('name', f'Filter {current_filter}')}"
                
                # Hvis ikke, prøv at få det fra GUI selection
                selected_filter = self.selected_filter.get()
                if selected_filter:
                    return selected_filter
        
        # Fallback - hent filter fra GUI selection
        selected_filter = self.selected_filter.get()
        if selected_filter:
            return selected_filter
            
    except Exception as e:
        print(f"Fejl ved hentning af filter navn: {str(e)}")
    
    return None

def create_standard_fits_header(self, obstype, sat_name, exposure_start_time, exposure_end_time, 
                               exposure_time, tle1, tle2, norad_id, camera=None, pw4_status=None, 
                               ra_hours=None, dec_degrees=None, alt_degrees=None, az_degrees=None,
                               image_width=None, image_height=None, x_binning=1, y_binning=1, filter_name=None,
                               mid_exposure_time=None):
    """
    Opretter en standard FITS header til både LeapFrog og Tracking observationer.
    Tilpasset til at fungere med Moravian kamera objekter og PWI4 teleskop.
    
    Args:
        obstype (str): Type af observation ('LeapFrog', 'Tracking', 'stjernehimmel')
        sat_name (str): Satellit navn
        exposure_start_time (datetime): Start tid for eksponering
        exposure_end_time (datetime): Slut tid for eksponering  
        exposure_time (float): Eksponeringstid i sekunder
        tle1 (str): TLE linje 1
        tle2 (str): TLE linje 2
        norad_id (str): NORAD ID
        camera (obj, optional): Moravian kamera objekt
        pw4_status (dict, optional): PWI4 status data
        ra_hours (float, optional): RA i timer (kun til LeapFrog)
        dec_degrees (float, optional): DEC i grader (kun til LeapFrog)
        alt_degrees (float, optional): Altitude i grader (kun til LeapFrog)
        az_degrees (float, optional): Azimuth i grader (kun til LeapFrog)
        image_width (int, optional): Billede bredde
        image_height (int, optional): Billede højde
        x_binning (int): X binning
        y_binning (int): Y binning
        filter_name (str, optional): Navn på det anvendte filter
        
    Returns:
        fits.Header: Komplet FITS header
    """
    from astropy.io import fits
    
    header = fits.Header()
    
    # Standard FITS headers
    header['SIMPLE'] = True
    header['BITPIX'] = 16
    header['NAXIS'] = 2
    
    # Billede dimensioner
    if image_width and image_height:
        header['NAXIS1'] = image_width
        header['NAXIS2'] = image_height
    elif camera is not None:
        # Check if it's a Moravian camera
        if hasattr(camera, 'get_camera_info'):
            info = camera.get_camera_info()
            ccd_width = info.get('width', 0)
            ccd_height = info.get('height', 0)
            header['NAXIS1'] = ccd_width // camera.bin_x
            header['NAXIS2'] = ccd_height // camera.bin_y
            
    
    # Observation info
    header['OBJECT'] = sat_name
    header['OBSTYPE'] = obstype
    header['EXPTIME'] = exposure_time
    
    # Tidsstempel felter - præcis timing kun for Tracking observationer
    if obstype == 'Tracking' and mid_exposure_time is not None:
        # Brug præcis målt midtertidspunkt for Tracking (hvor PWI4 status blev hentet)
        calculated_mid_time = mid_exposure_time
    else:
        # Brug beregnede midtertidspunkt for LeapFrog og andre observation typer
        calculated_mid_time = exposure_start_time + timedelta(seconds=(exposure_end_time - exposure_start_time).total_seconds() / 2)
    
    header['DATE-STA'] = exposure_start_time.isoformat()  # Start eksponering
    header['DATE-OBS'] = calculated_mid_time.isoformat()   # Midt i eksponering (præcis for Tracking)
    header['DATE-END'] = exposure_end_time.isoformat()   # Slut eksponering
    
    header['OBSERVER'] = 'Satellite Tracking GUI'
    
    # Kamera info
    if camera is not None:
        # Check if it's a Moravian camera
        if hasattr(camera, 'get_camera_info'):
            info = camera.get_camera_info()
            header['INSTRUME'] = info.get('description', 'Moravian Camera')
            header['XBINNING'] = camera.bin_x
            header['YBINNING'] = camera.bin_y
            
            # Tilføj ekstra Moravian kamera parametre
            if 'pixel_width' in info:
                header['XPIXSZ'] = info['pixel_width'] * camera.bin_x
            if 'pixel_height' in info:
                header['YPIXSZ'] = info['pixel_height'] * camera.bin_y
            if 'temperature' in info:
                header['CCD-TEMP'] = info['temperature']
            if 'serial' in info:
                header['CAMERA_S'] = info['serial']
            if 'current_gain' in info:
                header['GAIN'] = info['current_gain']
            if 'gain_db' in info:
                header['GAIN_DB'] = info['gain_db']
        else:
            # Fallback værdier
            header['INSTRUME'] = 'Unknown Camera'
            header['XBINNING'] = x_binning
            header['YBINNING'] = y_binning
    else:
        # Fallback værdier
        header['INSTRUME'] = 'Unknown Camera'
        header['XBINNING'] = x_binning
        header['YBINNING'] = y_binning
    
    # Filter information
    if filter_name is not None:
        header['FILTER'] = filter_name
    elif camera is not None and hasattr(camera, 'get_camera_info'):
        # Prøv at hente aktuel filter fra Moravian kamera
        try:
            info = camera.get_camera_info()
            current_filter = info.get('current_filter')
            if current_filter is not None:
                header['FILTER'] = f"Filter {current_filter}"
        except:
            pass
    
    # PWI4 teleskop koordinater (hvis tilgængelige)
    if pw4_status:
        mount_data = pw4_status.get('mount', {})
        
        # RA/DEC koordinater - afrundet til 7 decimaler
        if 'ra_apparent_hours' in mount_data:
            header['RA_APP'] = round(float(mount_data['ra_apparent_hours']), 7)
        if 'dec_apparent_degs' in mount_data:
            header['DEC_APP'] = round(float(mount_data['dec_apparent_degs']), 7)
        if 'ra_j2000_hours' in mount_data:
            header['RA_J2000'] = round(float(mount_data['ra_j2000_hours']), 7)
            header['RA'] = round(float(mount_data['ra_j2000_hours']) * 15.0, 7)  # omregner fra timer til grader
        if 'dec_j2000_degs' in mount_data:
            header['DEC_J200'] = round(float(mount_data['dec_j2000_degs']), 7)  # Kort navn pga. FITS begrænsning
            header['DEC'] = round(float(mount_data['dec_j2000_degs']), 7)  # Alias for kompatibilitet
            
        # Teleskop status
        if 'is_slewing' in mount_data:
            header['SLEWING'] = mount_data['is_slewing']
        if 'is_tracking' in mount_data:
            header['TRACKING'] = mount_data['is_tracking']
        if 'altitude_degs' in mount_data:
            header['ALT_TEL'] = round(float(mount_data['altitude_degs']), 7)  # Alias
        if 'azimuth_degs' in mount_data:
            header['AZ_TEL'] = round(float(mount_data['azimuth_degs']), 7)  # Alias
            
        # PWI4 specifikke felter
        header['TELESCOP'] = 'PlaneWave PWI4'
        if 'julian_date' in mount_data:
            header['JD'] = float(mount_data['julian_date'])
        if 'field_angle_degs' in mount_data:
            header['CROTA2'] = round(float(mount_data['field_angle_degs']), 7)
        if 'distance_to_sun_degs' in mount_data:
            header['DIST_SUN'] = round(float(mount_data['distance_to_sun_degs']), 7)
        if 'timestamp_utc' in mount_data:
            header['PWI4MTS'] = mount_data['timestamp_utc']
        if 'update_duration_msec' in mount_data:
            header['PWI4DUR'] = int(mount_data['update_duration_msec'])
        if 'field_angle_here_degs' in mount_data:
            header['FA_HERE'] = round(float(mount_data['field_angle_here_degs']), 7)
        if 'field_angle_at_target_degs' in mount_data:
            header['FA_TARG'] = round(float(mount_data['field_angle_at_target_degs']), 7)
        
            
        # Observer position
        site_data = pw4_status.get('site', {})
        if 'latitude_degs' in site_data:
            header['LAT-OBS'] = round(float(site_data['latitude_degs']), 7)
        if 'longitude_degs' in site_data:
            header['LONG-OBS'] = round(float(site_data['longitude_degs']), 7)
        if 'height_meters' in site_data:
            header['ELEV-OBS'] = round(float(site_data['height_meters']), 3)
            
        # PWI4 version
        pwi4_data = pw4_status.get('pwi4', {})
        if 'version' in pwi4_data:
            header['PWI4VER'] = pwi4_data['version']
            
        response_data = pw4_status.get('response', {})
        if 'timestamp_utc' in response_data:
            header['PWI4TIME'] = response_data['timestamp_utc']

        rotator_data = pw4_status.get('rotator', {})
        if 'field_angle_degs' in rotator_data:
            header['ROT_ANGLE'] = round(float(rotator_data['field_angle_degs']), 7)
        if 'mech_position_degs' in rotator_data:
            header['ROT_MECH'] = round(float(rotator_data['mech_position_degs']), 7)

    # LeapFrog satellite koordinater (planlagte - kun hvis angivet)
    if ra_hours is not None and dec_degrees is not None:
        header['Leap_RA'] = (ra_hours, 'Planned satellite RA (hours)')
        header['Leap_DEC'] = (dec_degrees, 'Planned satellite DEC (degrees)')
        if alt_degrees is not None:
            header['Leap_ALT'] = (alt_degrees, 'Planned satellite altitude (degrees)')
        if az_degrees is not None:
            header['Leap_AZ'] = (az_degrees, 'Planned satellite azimuth (degrees)')

    # TLE info
    header['TLE1'] = tle1
    header['TLE2'] = tle2
    header['NORAD_ID'] = norad_id
    
    # Tilføj kommentar afhængig af observation type
    if obstype == 'LeapFrog':
        header["COMMENT"] = f"LeapFrog observation point for {sat_name}"
    elif obstype == 'Tracking':
        header["COMMENT"] = f"Satellite tracking image for {sat_name}"
    elif obstype == 'stjernehimmel':
        header["COMMENT"] = "Star field reference image during satellite tracking"
        header["REFIMAGE"] = True
    
    return header

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
