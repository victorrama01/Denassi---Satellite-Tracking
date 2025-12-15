import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
import cv2
from astropy.io import fits
from skyfield.api import load, EarthSatellite, wgs84
from datetime import datetime
from scipy.ndimage import rotate, label, find_objects
from tqdm import tqdm
from matplotlib.patches import Circle
import requests
import time
import subprocess

def beregn_sat_pos(theta, Ra, Dec, pixscale, sizex, sizey, posx, posy):
    import numpy as np
    """
    Beregn satellittens himmelkoordinater (RA, Dec) ud fra billedets midtpunkt,
    rotationsvinkel og pixelposition.

    Parameters:
    theta (float): rotationsvinkel i grader (positiv med uret normalt, afhænger af dit def.)
    Ra (float): midtpunktets Right Ascension i grader
    Dec (float): midtpunktets Declination i grader
    pixscale (float): pixel scale i arcsec/pixel
    sizex, sizey (int): billedets størrelse i pixels
    posx, posy (float): satellittens pixelposition i billedet

    Returns:
    (sat_ra, sat_dec): koordinater i grader
    """

    # forskydning fra billedcenter (bemærk flytning til center af pixel: -0.5)
    dx = posx - (sizex / 2 - 0.5)
    dy = posy - (sizey / 2 - 0.5) 

    # rotation (theta i grader → radianer)
    theta_rad = np.radians(theta)
    rot_matrix = np.array([[np.cos(theta_rad), -np.sin(theta_rad)],
                           [np.sin(theta_rad),  np.cos(theta_rad)]])
    d_rot = rot_matrix @ np.array([dx, dy])

    # konverter til buesekunder → grader
    delta_ra  = (d_rot[0] * pixscale) / 3600
    delta_dec = (d_rot[1] * pixscale) / 3600

    # RA skal evt. justeres for cos(Dec), afhængig af hvor præcist du vil have det (projektionseffekt)
    sat_ra  = Ra + delta_ra 
    sat_dec = Dec + delta_dec
    return sat_ra, sat_dec, delta_ra, delta_dec

def format_TLE_Teleskob(behandlet_teleskob, TLE, NoradID=00000, tidsstempel_index=0):
    TLE_lines_list = []
    
    # Først: konverter hele kolonnen én gang udenfor løkken
    behandlet_teleskob['DATE-OBS-datetime'] = pd.to_datetime(behandlet_teleskob['DATE-OBS'][tidsstempel_index])

    for i in range(len(TLE)):
        # Hent allerede konverteret tidspunkt
        t = behandlet_teleskob['DATE-OBS-datetime'].iloc[i]

        # Beregn epoch year og epoch day
        epoch_year = t.year % 100
        start_of_year = pd.Timestamp(year=t.year, month=1, day=1)
        delta = t - start_of_year
        epoch_day = delta.days + 1 + delta.seconds / 86400 + delta.microseconds / 86400e6
        
        # Formater som strings
        epoch_yr_str = f"{epoch_year:02d}"
        epoch_day_str = f"{epoch_day:012.8f}"


        # --- Orbital elements ---
        GM = 3.986004415e5  # km^3/s^2
        a_km = TLE[i]['sma'] / 1000  # meters -> km
        n_rad = np.sqrt(GM / a_km**3)
        mean_motion = (n_rad / (2 * np.pi)) * 86400  # rev/day
        mean_motion_str = f"{mean_motion:11.8f}".strip()

        inclination_str = f"{TLE[i]['incl']:8.4f}".strip()
        raan_str = f"{TLE[i]['raan']:8.4f}".strip()
        argp_str = f"{TLE[i]['argp']:8.4f}".strip()

        ecc = TLE[i]['ecc']
        ecc_str = f"{ecc:.7f}".split('.')[1]

        # --- Mean anomaly beregning ---
        true_anomaly = TLE[i]['tran']
        E = 2 * np.arctan(np.tan(np.radians(true_anomaly) / 2) * np.sqrt((1 - ecc) / (1 + ecc)))
        M = E - ecc * np.sin(E)
        mean_anomaly = np.degrees(M) % 360
        mean_anomaly_str = f"{mean_anomaly:8.4f}".strip()

        # --- Kald til write_tle_lines ---
        TLE_lines = write_tle_lines(
            NoradID=NoradID,
            epoch_year=epoch_yr_str,
            epoch_day=epoch_day_str,
            mean_motion=mean_motion_str,
            inclination=inclination_str,
            raan=raan_str,
            eccentricity=ecc_str,
            argument_of_perigee=argp_str,
            mean_anomaly=mean_anomaly_str
        )

        TLE_lines_list.append(TLE_lines)

    return TLE_lines_list

def udregn_gennemsnit(Rho_list):
    from collections import defaultdict
    value_dict = defaultdict(list)

    for i, sublist in enumerate(Rho_list):  # i = index i Rho_list
        for j, x in enumerate(sublist):     # j = position i sublisten (0,1,2)
            index = i + j                   # X_i's globale index
            value_dict[index].append(x)

    # Beregn gennemsnit for hver X_i
    average_list = [np.mean(value_dict[i]) for i in sorted(value_dict)]
    return average_list, value_dict

def udregn_R_og_TLE(angles, times, r,):
    from collections import defaultdict
    from orbit_determination_functions import gauss, gibbs
    from keplerTLE import kepel
    Rho_list = []
    TLE_list = []
    for i in range(len(times)-2):
        tider = np.array([times[i], times[i+1], times[i+2]])
        r_ = np.array([np.array(r[i]), np.array(r[i+1]), np.array(r[i+2])])
        angles_ = np.array([
            np.array(angles[i]),
            np.array(angles[i+1]),
            np.array(angles[i+2])
        ])
        R, rho = gauss(angles_, tider, r_, mu=398600.4418)
        v2, e, P = gibbs(R)
        print(R[:, 1])
        TLE = kepel(R[:, 1]*1000, v2*1000, GM=3.986004415e14)
        Rho_list.append(rho)
        TLE_list.append(TLE)
    average_list, value_dict = udregn_gennemsnit(Rho_list)
    return TLE_list, average_list, value_dict

def beregn_observatørpositioner(df):
    from datetime import datetime
    from skyfield.api import load, wgs84
    import numpy as np
    """
    Beregner observatørens position i ECI-koordinater ud fra dato og geografiske data.

    Parametre:
        df (pd.DataFrame): DataFrame med kolonnerne 'DATE-OBS', 'LAT--OBS', 'LONG-OBS', 'ELEV-OBS'

    Returnerer:
        X, Y, Z (np.ndarray): Arrays med koordinater i ECI-systemet (km)
    """
        # Konverter datostreng til (år, måned, dag, time, minut, sekund)
    def convert_to_tuple(date_str):
        try:
            # Først prøv med mikrosekunder
            dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S.%f")
        except ValueError:
            # Hvis det fejler, prøv med T-format
            dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%f")

        return (dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)

    # Initialisering
    ts = load.timescale()
    
    observation_points = []

    for i, date_str in enumerate(df["DATE-OBS"]):
        date_tuple = convert_to_tuple(date_str)
        t = ts.utc(*date_tuple)

        lat = df["LAT--OBS"].iloc[i]
        lon = df["LONG-OBS"].iloc[i]
        elev = df["ELEV-OBS"].iloc[i]

        eci_pos = wgs84.latlon(lat, lon, elev).at(t).position.km
        observation_points.append(eci_pos)

    observation_points = np.array(observation_points)
    X, Y, Z = observation_points.T
    return X, Y, Z

def process_and_save_coordinates_leapfrog(directory, rotation_angle=0, plot=True):
    fits_files = [f for f in os.listdir(directory) if f.lower().endswith('.fits')]
    
    results = []
    updated_times = []
    
    df = pd.read_csv(os.path.join(directory, "local_output.csv"), sep=",", engine="python", decimal=".")
    TLE_fil = pd.read_csv(os.path.join(directory, "TLE.csv"), sep=",", engine="python", decimal=".")
    TLE_Line1 = TLE_fil["TLE1"].iloc[0]
    TLE_Line2 = TLE_fil["TLE2"].iloc[0]

    for n, filename in enumerate(fits_files):
        filepath = os.path.join(directory, filename)
        print(f"Behandler fil: {filename}")

        with fits.open(filepath) as hdul:
            image_data = hdul[0].data

        # Billedbehandling
        mean = np.mean(image_data)
        std_dev = np.std(image_data)
        max_value = np.max(image_data)
        threshold = mean if max_value > 30000 else mean + 0.5 * std_dev

        if mean > 700:
            image_data[image_data > (mean + 200)] = 0
        else:
            image_data[image_data > 800] = 0

        image_data[image_data < threshold] = 0
        image_data = np.nan_to_num(image_data)
        image_data = (image_data - np.min(image_data)) / (np.max(image_data) - np.min(image_data)) * 255
        image_data = np.uint8(image_data)
        mean = np.mean(image_data[image_data != 0])
        image_data[image_data <= mean] = 0
        image_data[image_data > mean] = 255
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(image_data, connectivity=8)
        large_components_mask = np.isin(labels, np.where(stats[:, cv2.CC_STAT_AREA] >= 10)[0])
        image_data = np.where(large_components_mask, image_data, 0)

        lines = cv2.HoughLinesP(image_data, 1, np.pi / 180, threshold=10, minLineLength=1000, maxLineGap=10)

        if lines is not None:
            antal_linjer = len(lines)
            best_line = max(lines, key=lambda l: np.hypot(l[0][2] - l[0][0], l[0][3] - l[0][1]))
            x1, y1, x2, y2 = best_line[0]

            height, width = image_data.shape
            edge_margin = 35

            is_edge1 = (x1 < edge_margin or x1 > width - edge_margin or
                        y1 < edge_margin or y1 > height - edge_margin)
            is_edge2 = (x2 < edge_margin or x2 > width - edge_margin or
                        y2 < edge_margin or y2 > height - edge_margin)

            tidsstempel_start = df["DATE-BEG"][n]
            tidsstempel_slut = df["DATE-END"][n]
            Longitude = df['LONG-OBS'][n]
            Latitude = df['LAT--OBS'][n]
            Elevation = df['ELEV-OBS'][n]

            obs_time = datetime.strptime(tidsstempel_start, '%Y-%m-%dT%H:%M:%S.%f')
            obs_time_slut = datetime.strptime(tidsstempel_slut, '%Y-%m-%dT%H:%M:%S.%f')
            ts = load.timescale()
            t = ts.utc(obs_time.year, obs_time.month, obs_time.day, obs_time.hour, obs_time.minute, obs_time.second)

            satellite = EarthSatellite(TLE_Line1, TLE_Line2, name='sat', ts=ts)
            observer = wgs84.latlon(Latitude, Longitude, Elevation)
            difference = satellite - observer
            topocentric = difference.at(t)
            enu_velocity = topocentric.velocity.km_per_s
            east_velocity = enu_velocity[0]

            if east_velocity > 0:
                print("Satellitten bevæger sig mod øst på observationstidspunktet.")
            else:
                print("Satellitten bevæger sig mod vest på observationstidspunktet.")

            # Beregn skillelinje og masker
            theta_rad = np.radians(-rotation_angle[n]) # MINUS ER EN TEST
            x_c = (width - 1) / 2
            y_c = (height - 1) / 2
            Y, X = np.indices(image_data.shape)
            dx_grid = X - x_c
            dy_grid = y_c - Y
            nx = np.sin(theta_rad)
            ny = np.cos(theta_rad)
            side = dx_grid * ny - dy_grid * nx
            

            # identificer hvilket punkt der er kantpunktet
            if (is_edge1 or is_edge2):
                print("OBS! fundet streg går ud af billedet!")
                if is_edge1:
                    non_edge_point = (x2, y2)
                    edge_point = (x1, y1)
                else:
                    non_edge_point = (x1, y1)
                    edge_point = (x2, y2)
                mid_x, mid_y = non_edge_point

                # Ekstraher punktet --- 
                px, py = edge_point

                # Beregn forskydning fra billedets centrum
                dx_p = px - x_c
                dy_p = y_c - py  # fordi billedet er "y nedad"

                # Beregn side-værdien for dette punkt
                side_p = dx_p * ny - dy_p * nx

                # Afgør hvilken maske punktet ligger i
                if side_p >= 0:
                    print("kantpunktet ligger i vest")
                    if east_velocity > 0:
                        print("Slutpunktet for linjen bliver til midtpunktet, vi lægger 1 sekund til")
                        new_obs_time = obs_time + pd.Timedelta(seconds=1)
                    else:
                        print("Startpunktet for linjen bliver til midtpunktet, vi lægger 0 sekunder til")
                        new_obs_time = obs_time + pd.Timedelta(seconds=0)
                else:
                    print("kantpunktet ligger i øst")
                    if east_velocity > 0:
                        print("Startpunktet for linjen bliver til midtpunktet, vi lægger 0 sekund til")
                        new_obs_time = obs_time + pd.Timedelta(seconds=0)
                    else:
                        print("Slutpunktet for linjen bliver til midtpunktet, vi lægger 1 sekund til")
                        new_obs_time = obs_time + pd.Timedelta(seconds=1)
                # ----

            else:
                delta_obs_time = obs_time_slut - obs_time
                print(f"Ingen kant - vi lægger {delta_obs_time.total_seconds()/2} sekunder til")
                mid_x = (x1 + x2) // 2
                mid_y = (y1 + y2) // 2
                new_obs_time = obs_time + pd.Timedelta(seconds=delta_obs_time.total_seconds()/2)

            updated_times.append(new_obs_time.strftime('%Y-%m-%dT%H:%M:%S.%f'))

            # Filnavn
            new_filename = f"1_" + filename
            if not (filename.startswith("0_") or filename.startswith("1_")):
                os.rename(filepath, os.path.join(directory, new_filename))
            else:
                new_filename = filename

            results.append({
                'filename': new_filename,
                'antal_linjer': antal_linjer,
                'point1': (x1, y1),
                'point2': (x2, y2),
                'midpoint': (int(mid_x), int(mid_y)),
                'size': (int(height), int(width))
            })

            # ------- PLOT --------
            if plot:
                fig, axs = plt.subplots(1, 2, figsize=(18, 6))

                # -------- Begrænset linje beregning --------
                dx_line = np.sin(theta_rad)
                dy_line = -np.cos(theta_rad)
                t_vals = np.linspace(-max(width, height), max(width, height), 1000)
                x_line_all = x_c + t_vals * dx_line
                y_line_all = y_c + t_vals * dy_line
                mask_inside = (
                    (x_line_all >= 0) & (x_line_all < width) &
                    (y_line_all >= 0) & (y_line_all < height)
                )
                x_line = x_line_all[mask_inside]
                y_line = y_line_all[mask_inside]

                # Plot 1: hele billedet
                axs[0].imshow(image_data, cmap='gray')
                axs[0].scatter([x1, x2], [y1, y2], edgecolor='red', facecolors='none', s=40)
                axs[0].scatter(mid_x, mid_y, color='green', marker='x', s=100)
                axs[0].plot(x_line, y_line, 'r-', linewidth=2, label=f'Nord: {rotation_angle[n]:.2f}°')
                axs[0].legend()
                axs[0].set_title(f"Detekteret linje: {filename}")

                # Plot 2: zoomet ind
                axs[1].imshow(image_data, cmap='gray')
                axs[1].scatter([x1, x2], [y1, y2], edgecolor='red', facecolors='none', s=40)
                axs[1].scatter(mid_x, mid_y, color='green', marker='x', s=100)
                axs[1].plot(x_line, y_line, 'r-', linewidth=2, label=f'Nord: {rotation_angle[n]:.2f}°')
                axs[1].legend()
                axs[1].set_title("Forstørret Detekteret linje")
                axs[1].set_xlim(min(x1, x2) - 200, max(x1, x2) + 200)
                axs[1].set_ylim(max(y1, y2) + 200, min(y1, y2) - 200)

                plt.tight_layout()
                plt.show()

        else:
            print(f"Ingen linjer fundet i {filename}")
            updated_times.append(tidsstempel_start)
            new_filename = "0_" + filename
            if not (filename.startswith("0_") or filename.startswith("1_")):
                os.rename(filepath, os.path.join(directory, new_filename))
            else:
                new_filename = filename

            results.append({'filename': new_filename, 'antal_linjer': 0})

    pd.DataFrame(results).to_csv(os.path.join(directory, "coordinates_output.csv"), index=False)
    df['DATE-OBS'] = updated_times
    df.to_csv(os.path.join(directory, "local_output.csv"), sep=",", decimal=".", index=False)
    print("Både coordinates_output.csv og local_output.csv er opdateret.")
    
    return pd.DataFrame(results)


def find_sat_tracking(directory, rotation_angles=None, pixscale=0.22, plot_result=False):
    """
    Finder delta_RA og delta_DEC for alle fits-filer i en mappe.
    Inkluderer progressbar.

    Parameters:
        directory (str): sti til mappe med fits-filer.
        rotation_angles (list or pd.Series or None): rotationsvinkler i grader.
        pixscale (float): pixel-skala i arcsec/pixel.

    Returns:
        tuple: (delta_RA_list, delta_DEC_list)
    """

    # Hvis rotation_angles er en pandas Series, konverter den til liste
    if isinstance(rotation_angles, pd.Series):
        rotation_angles = rotation_angles.tolist()

    delta_RA_list = []
    delta_DEC_list = []

    # Find og sorter alle fits-filer
    fits_files = sorted([f for f in os.listdir(directory) if f.lower().endswith('.fits')])

    # Hvis rotation_angles er None, lav liste med 0'er
    if rotation_angles is None:
        rotation_angles = [0] * len(fits_files)

    # Safety check: hvis rotation_angles har forkert længde
    if len(rotation_angles) != len(fits_files):
        raise ValueError("Antallet af rotation_angles matcher ikke antallet af fits-filer.")

    # Brug tqdm til progressbar
    for i, fits_file in enumerate(tqdm(fits_files, desc="Processing FITS files", unit="file")):
        file_path = os.path.join(directory, fits_file)
        rotation_angle = rotation_angles[i]

        with fits.open(file_path) as hdul:
            data = np.asanyarray(hdul[0].data, dtype=np.float32)

        if rotation_angle != 0:
            data = rotate(data, rotation_angle, reshape=False, order=1)

        num_top_pixels = 1000
        flat_indices = np.argpartition(data.ravel(), -num_top_pixels)[-num_top_pixels:]
        sorted_indices = flat_indices[np.argsort(data.ravel()[flat_indices])[::-1]]
        sorted_positions = np.unravel_index(sorted_indices, data.shape)

        neighbor_radius = 80
        mask = np.zeros_like(data, dtype=bool)

        for y, x in zip(sorted_positions[0], sorted_positions[1]):
            y_start = max(0, y - neighbor_radius)
            y_end = min(data.shape[0], y + neighbor_radius + 1)
            x_start = max(0, x - neighbor_radius)
            x_end = min(data.shape[1], x + neighbor_radius + 1)
            mask[y_start:y_end, x_start:x_end] = True

        thresholded_data = mask & (data > np.mean(data) + 0.75 * np.std(data))
        labeled_array, num_features = label(thresholded_data)
        object_slices = find_objects(labeled_array)

        brightest_object_slice = None
        max_val = -np.inf

        for slice_ in object_slices:
            region = data[slice_]
            if region.shape[0] >= 20 and region.shape[1] >= 20:
                region_mean = np.mean(region)
                if region_mean > max_val:
                    max_val = region_mean
                    brightest_object_slice = slice_
                    brightest_object_index = i

        if brightest_object_slice is None:
            print(f"Ingen gyldig region fundet i {fits_file}")
            delta_RA_list.append(np.nan)
            delta_DEC_list.append(np.nan)
            continue

        y_start, y_stop = brightest_object_slice[0].start, brightest_object_slice[0].stop
        x_start, x_stop = brightest_object_slice[1].start, brightest_object_slice[1].stop
        y_center = (y_start + y_stop - 1) // 2
        x_center = (x_start + x_stop - 1) // 2

        y_mid = data.shape[0] // 2
        x_mid = data.shape[1] // 2

        dx = x_center - x_mid
        dy = y_center - y_mid

        delta_RA = -dx * pixscale / 3600
        delta_DEC = -dy * pixscale / 3600

        delta_RA_list.append(delta_RA)
        delta_DEC_list.append(delta_DEC)

        if plot_result:
            valid_pixels = data[data > 0]
            vmin = np.percentile(valid_pixels, 5)
            vmax = np.percentile(valid_pixels, 99)
            fig, ax = plt.subplots(figsize=(8, 8))
            ax.imshow(data, cmap='gray', vmin=vmin, vmax=vmax)

            # --- Her kommer de nye overlays ---

            # Gul: hele masken
            ax.imshow(np.ma.masked_where(~mask, mask), cmap='summer', alpha=0.5)

            # Rød: det lyseste objekt
            if brightest_object_index is not None:
                brightest_mask = labeled_array == (brightest_object_index + 1)
                ax.imshow(np.ma.masked_where(~brightest_mask, brightest_mask), cmap='autumn', alpha=1)

            # --- Resten er din eksisterende grafik ---
            if brightest_object_slice is not None:
                circ = Circle((x_center, y_center), radius=80, edgecolor='red', facecolor='none', lw=1)
                ax.add_patch(circ)
                ax.set_title(f"{fits_file}\nΔRA={delta_RA:.3f}° pixels dx = {dx} - ΔDEC={delta_DEC:.3f}° pixels dy = {dy}")
            else:
                ax.set_title("Ingen gyldig region fundet.")

            ax.set_xlabel("Pixel X")
            ax.set_ylabel("Pixel Y")
            ax.arrow(100, data.shape[0]-300, 200, 0, head_width=50, head_length=50, fc='blue', ec='blue', length_includes_head=False)
            ax.arrow(100, data.shape[0]-300, 0, 200, head_width=50, head_length=50, fc='green', ec='green', length_includes_head=False)
            ax.text(210, data.shape[0]-310, 'X', color='blue', fontsize=14)
            ax.text(110, data.shape[0]-110, 'Y', color='green', fontsize=14)
            if brightest_object_slice is not None:
                ax.arrow(x_mid, y_mid, dx, 0, head_width=20, head_length=20, fc='blue', ec='blue', length_includes_head=True, label='dx')
                ax.arrow(x_mid+dx, y_mid, 0, dy, head_width=20, head_length=20, fc='green', ec='green', length_includes_head=True, label='dy')
            plt.show()

    return delta_RA_list, delta_DEC_list


def find_sat_tracking_xy(directory, plot_result=False):
    """
    Finder delta_RA og delta_DEC for alle fits-filer i en mappe.
    Inkluderer progressbar.

    Parameters:
        directory (str): sti til mappe med fits-filer.
        rotation_angles (list or pd.Series or None): rotationsvinkler i grader.
        pixscale (float): pixel-skala i arcsec/pixel.

    Returns:
        tuple: (delta_RA_list, delta_DEC_list)
    """

    x_list = []
    y_list = []

    # Find og sorter alle fits-filer
    fits_files = sorted([f for f in os.listdir(directory) if f.lower().endswith('.fits')])

    # Brug tqdm til progressbar
    for i, fits_file in enumerate(tqdm(fits_files, desc="Processing FITS files", unit="file")):
        file_path = os.path.join(directory, fits_file)

        with fits.open(file_path) as hdul:
            data = np.asanyarray(hdul[0].data, dtype=np.float32)

        num_top_pixels = 1000
        flat_indices = np.argpartition(data.ravel(), -num_top_pixels)[-num_top_pixels:]
        sorted_indices = flat_indices[np.argsort(data.ravel()[flat_indices])[::-1]]
        sorted_positions = np.unravel_index(sorted_indices, data.shape)

        neighbor_radius = 80
        mask = np.zeros_like(data, dtype=bool)

        for y, x in zip(sorted_positions[0], sorted_positions[1]):
            y_start = max(0, y - neighbor_radius)
            y_end = min(data.shape[0], y + neighbor_radius + 1)
            x_start = max(0, x - neighbor_radius)
            x_end = min(data.shape[1], x + neighbor_radius + 1)
            mask[y_start:y_end, x_start:x_end] = True

        thresholded_data = mask & (data > np.mean(data) + 0.75 * np.std(data))
        labeled_array, num_features = label(thresholded_data)
        object_slices = find_objects(labeled_array)

        brightest_object_slice = None
        max_val = -np.inf

        for slice_ in object_slices:
            region = data[slice_]
            if region.shape[0] >= 20 and region.shape[1] >= 20:
                region_mean = np.mean(region)
                if region_mean > max_val:
                    max_val = region_mean
                    brightest_object_slice = slice_
                    brightest_object_index = i

        if brightest_object_slice is None:
            print(f"Ingen gyldig region fundet i {fits_file}")
            x_list.append(np.nan)
            y_list.append(np.nan)
            continue

        y_start, y_stop = brightest_object_slice[0].start, brightest_object_slice[0].stop
        x_start, x_stop = brightest_object_slice[1].start, brightest_object_slice[1].stop
        y_center = (y_start + y_stop - 1) // 2
        x_center = (x_start + x_stop - 1) // 2

        x_list.append(x_center)
        y_list.append(y_center)

        if plot_result:
            valid_pixels = data[data > 0]
            vmin = np.percentile(valid_pixels, 5)
            vmax = np.percentile(valid_pixels, 99)
            fig, ax = plt.subplots(figsize=(8, 8))
            ax.imshow(data, cmap='gray', vmin=vmin, vmax=vmax)

            # --- Her kommer de nye overlays ---

            # Gul: hele masken
            ax.imshow(np.ma.masked_where(~mask, mask), cmap='summer', alpha=0.5)

            # Rød: det lyseste objekt
            if brightest_object_index is not None:
                brightest_mask = labeled_array == (brightest_object_index + 1)
                ax.imshow(np.ma.masked_where(~brightest_mask, brightest_mask), cmap='autumn', alpha=1)

            # --- Resten er din eksisterende grafik ---
            if brightest_object_slice is not None:
                circ = Circle((x_center, y_center), radius=80, edgecolor='red', facecolor='none', lw=1)
                ax.add_patch(circ)
                ax.set_title(f"{fits_file}\nX={x_center:.3f} Y={y_center:.3f} ")
            else:
                ax.set_title("Ingen gyldig region fundet.")

            ax.set_xlabel("Pixel X")
            ax.set_ylabel("Pixel Y")
            ax.arrow(100, data.shape[0]-300, 200, 0, head_width=50, head_length=50, fc='blue', ec='blue', length_includes_head=False)
            ax.arrow(100, data.shape[0]-300, 0, 200, head_width=50, head_length=50, fc='green', ec='green', length_includes_head=False)
            ax.text(210, data.shape[0]-310, 'X', color='blue', fontsize=14)
            ax.text(110, data.shape[0]-110, 'Y', color='green', fontsize=14)

            plt.show()

    return x_list, y_list

def format_TLE_mean(behandlet_radar, TLE, NoradID=00000):
    # --- Finder det midterste index ---
    i = len(behandlet_radar) // 2  # midterste index
    # --- Epoch computation ---
    t = pd.to_datetime(behandlet_radar['Datetime']).iloc[i]
    epoch_year = t.year % 100
    start_of_year = pd.Timestamp(year=t.year, month=1, day=1)
    delta = t - start_of_year
    epoch_day = delta.days + 1 + delta.seconds / 86400 + delta.microseconds / 86400e6
    epoch_yr_str = f"{epoch_year:02d}"
    epoch_day_str = f"{epoch_day:012.8f}"

    # --- Orbital elements ---
    GM = 3.986004415e5  # km^3/s^2
    a_km = TLE['sma'] / 1000  # meters -> km
    n_rad = np.sqrt(GM / a_km**3)
    mean_motion = (n_rad / (2 * np.pi)) * 86400  # rev/day
    mean_motion_str = f"{mean_motion:11.8f}".strip()

    inclination_str = f"{TLE['incl']:8.4f}".strip()
    raan_str = f"{TLE['raan']:8.4f}".strip()
    argp_str = f"{TLE['argp']:8.4f}".strip()

    ecc = TLE['ecc']
    ecc_str = f"{ecc:.7f}".split('.')[1]

    # --- Mean anomaly beregning ---
    true_anomaly = TLE['tran']
    E = 2 * np.arctan(np.tan(np.radians(true_anomaly) / 2) * np.sqrt((1 - ecc) / (1 + ecc)))
    M = E - ecc * np.sin(E)
    mean_anomaly = np.degrees(M) % 360
    mean_anomaly_str = f"{mean_anomaly:8.4f}".strip()

    # --- Kald til write_tle_lines ---
    TLE_lines = write_tle_lines(
        NoradID=NoradID,
        epoch_year=epoch_yr_str,
        epoch_day=epoch_day_str,
        mean_motion=mean_motion_str,
        inclination=inclination_str,
        raan=raan_str,
        eccentricity=ecc_str,
        argument_of_perigee=argp_str,
        mean_anomaly=mean_anomaly_str
    )

    TLE_lines

    return TLE_lines

def compute_average_orbital_elements(tle_list):
    """
    Beregner gennemsnit af orbital elementer ud fra liste af dictionaries med sma, ecc, incl, raan, argp, tran.
    Returnerer en dict med gennemsnitlige elementer:
        - sma i km
        - ecc enhedsløs
        - vinkler i grader (0-360)
    """
    
    def mean_angle(angles):
        return np.arctan2(np.mean(np.sin(angles)), np.mean(np.cos(angles)))
    
    def normalize_angle_deg(angle_deg):
        return angle_deg % 360

    sma_array = np.array([tle['sma'] for tle in tle_list])
    ecc_array = np.array([tle['ecc'] for tle in tle_list])
    incl_array = np.radians([tle['incl'] for tle in tle_list])
    raan_array = np.radians([tle['raan'] for tle in tle_list])
    argp_array = np.radians([tle['argp'] for tle in tle_list])
    tran_array = np.radians([tle['tran'] for tle in tle_list])
    p_array = np.array([tle['p'] for tle in tle_list])
    
    sma_mean_m = np.mean(sma_array)
    ecc_mean = np.mean(ecc_array)
    incl_mean = normalize_angle_deg(np.degrees(mean_angle(incl_array)))
    raan_mean = normalize_angle_deg(np.degrees(mean_angle(raan_array)))
    argp_mean = normalize_angle_deg(np.degrees(mean_angle(argp_array)))
    tran_mean = normalize_angle_deg(np.degrees(mean_angle(tran_array)))
    p_mean = np.mean(p_array)
    
    return {
        'sma': sma_mean_m,  # km
        'ecc': ecc_mean,
        'incl': incl_mean,         # grader [0, 360)
        'raan': raan_mean,
        'argp': argp_mean,
        'tran': tran_mean,
        'p': p_mean                # km
    }

def format_TLE(behandlet_radar, TLE, NoradID=00000):
    TLE_lines_list = []
    
    for i in range(len(TLE)):
        # --- Epoch computation ---
        t = pd.to_datetime(behandlet_radar['Datetime']).iloc[i]
        epoch_year = t.year % 100
        start_of_year = pd.Timestamp(year=t.year, month=1, day=1)
        delta = t - start_of_year
        epoch_day = delta.days + 1 + delta.seconds / 86400 + delta.microseconds / 86400e6
        epoch_yr_str = f"{epoch_year:02d}"
        epoch_day_str = f"{epoch_day:012.8f}"

        # --- Orbital elements ---
        GM = 3.986004415e5  # km^3/s^2
        a_km = TLE[i]['sma'] / 1000  # meters -> km
        n_rad = np.sqrt(GM / a_km**3)
        mean_motion = (n_rad / (2 * np.pi)) * 86400  # rev/day
        mean_motion_str = f"{mean_motion:11.8f}".strip()

        inclination_str = f"{TLE[i]['incl']:8.4f}".strip()
        raan_str = f"{TLE[i]['raan']:8.4f}".strip()
        argp_str = f"{TLE[i]['argp']:8.4f}".strip()

        ecc = TLE[i]['ecc']
        ecc_str = f"{ecc:.7f}".split('.')[1]

        # --- Mean anomaly beregning ---
        true_anomaly = TLE[i]['tran']
        E = 2 * np.arctan(np.tan(np.radians(true_anomaly) / 2) * np.sqrt((1 - ecc) / (1 + ecc)))
        M = E - ecc * np.sin(E)
        mean_anomaly = np.degrees(M) % 360
        mean_anomaly_str = f"{mean_anomaly:8.4f}".strip()

        # --- Kald til write_tle_lines ---
        TLE_lines = write_tle_lines(
            NoradID=NoradID,
            epoch_year=epoch_yr_str,
            epoch_day=epoch_day_str,
            mean_motion=mean_motion_str,
            inclination=inclination_str,
            raan=raan_str,
            eccentricity=ecc_str,
            argument_of_perigee=argp_str,
            mean_anomaly=mean_anomaly_str
        )

        TLE_lines_list.append(TLE_lines)

    return TLE_lines_list

def process_radar_folders_20(main_folder):
    import os
    import numpy as np
    import pandas as pd
    from datetime import datetime, timedelta
    from astropy.time import Time
    from astropy.coordinates import EarthLocation, AltAz, SkyCoord
    import astropy.units as u
    from Radar_TLE import Radar_TLE
    from keplerTLE import kepel

    # Gennemløb alle undermapper
    for root, dirs, files in os.walk(main_folder):
        asc_files = [file for file in files if file.endswith('.asc')]
        
        # Kun hvis der er asc fil i undermappen
        if asc_files:
            asc_file = asc_files[0]
            filepath = os.path.join(root, asc_file)
            output_filepath = os.path.join(root, 'behandlet_radar_data_20.csv')
            print(f"Behandler: {filepath}")

            # ----------- Læs ASC fil ------------
            with open(filepath, encoding="latin1") as f:
                lines = f.readlines()

            raw_colnames = lines[52].strip()
            raw_units = lines[53].strip()

            colnames = raw_colnames.split(",  ")
            units = raw_units.split(", ")

            combined_headers = [f"{n} {u}" if i < len(units) and u else n
                                for i, (n, u) in enumerate(zip(colnames, units))]

            df = pd.read_csv(filepath, skiprows=54, sep=r"\s*,\s*", engine='python',
                             header=None, encoding="latin1", usecols=range(len(combined_headers)))
            df.columns = combined_headers

            # ----------- Behandling af observationerne ------------
            year, month, day = 2025, 3, 31
            seconds_array = df['     Time_UTC            [s]']
            base_time = datetime(year, month, day)
            datetimes = np.array([base_time + timedelta(seconds=s) for s in seconds_array])
            behandlet_df = pd.DataFrame({'Datetime': datetimes})

            # Lokation (fast)
            lat_deg, lon_deg, alt_m = 55.89160919, 12.41544724, 87.339
            location = EarthLocation(lat=lat_deg*u.deg, lon=lon_deg*u.deg, height=alt_m*u.m)
            behandlet_df['Lat'] = lat_deg
            behandlet_df['Lon'] = lon_deg
            behandlet_df['Alt'] = alt_m

            time = Time(datetimes, scale='utc')
            gcrs = location.get_gcrs(obstime=time)
            eci_xyz = gcrs.cartesian.xyz.to(u.m).T.value
            behandlet_df['X'], behandlet_df['Y'], behandlet_df['Z'] = eci_xyz[:, 0], eci_xyz[:, 1], eci_xyz[:, 2]

            itrs = location.get_itrs(obstime=time)
            ecef_xyz = itrs.cartesian.xyz.to(u.m).T.value
            behandlet_df['X_ECEF'], behandlet_df['Y_ECEF'], behandlet_df['Z_ECEF'] = ecef_xyz[:, 0], ecef_xyz[:, 1], ecef_xyz[:, 2]

            # RA/DEC beregnes
            az = df[' Azimuth (rad)           [deg]'].values * u.deg
            el = df[' Elevation(rad)            [deg]'].values * u.deg
            altaz_frame = AltAz(obstime=time, location=location)
            coord_altaz = SkyCoord(az=az, alt=el, frame=altaz_frame)
            coord_icrs = coord_altaz.transform_to('icrs')
            behandlet_df['RA'] = coord_icrs.ra.to(u.deg).value
            behandlet_df['DEC'] = coord_icrs.dec.to(u.deg).value

            # Beregn RA/DEC fejl
            ra_errors, dec_errors = [], []
            az_err = df['    AZ_err_mea           [deg]'].values * u.deg
            el_err = df['    EL_err_mea           [deg]'].values * u.deg

            def clip_elevation(alt): return np.clip(alt.to(u.deg).value, -90.0, 90.0) * u.deg

            for i in range(len(df)):
                az_i, el_i, time_i = az[i], el[i], time[i]
                az_err_i, el_err_i = az_err[i], el_err[i]
                frame = AltAz(obstime=time_i, location=location)

                coord_az_plus = SkyCoord(az=az_i + az_err_i, alt=el_i, frame=frame).transform_to('icrs')
                coord_az_minus = SkyCoord(az=az_i - az_err_i, alt=el_i, frame=frame).transform_to('icrs')

                el_plus = clip_elevation(el_i + el_err_i)
                el_minus = clip_elevation(el_i - el_err_i)
                coord_el_plus = SkyCoord(az=az_i, alt=el_plus, frame=frame).transform_to('icrs')
                coord_el_minus = SkyCoord(az=az_i, alt=el_minus, frame=frame).transform_to('icrs')

                ra_err_i = np.sqrt(((coord_az_plus.ra - coord_az_minus.ra).to(u.deg).value / 2)**2 +
                                   ((coord_el_plus.ra - coord_el_minus.ra).to(u.deg).value / 2)**2)
                dec_err_i = np.sqrt(((coord_az_plus.dec - coord_az_minus.dec).to(u.deg).value / 2)**2 +
                                    ((coord_el_plus.dec - coord_el_minus.dec).to(u.deg).value / 2)**2)

                ra_errors.append(ra_err_i)
                dec_errors.append(dec_err_i)

            behandlet_df['RA_error'] = ra_errors
            behandlet_df['DEC_error'] = dec_errors

            behandlet_df['afstand'] = df[' Sl.Range (rad)              [m]']
            behandlet_df['azimuth'] = df[' Azimuth (rad)           [deg]']
            behandlet_df['elevation'] = df[' Elevation(rad)            [deg]']
            behandlet_df['radial_Vel'] = df[' Rad. Vel.(rad)            [m/s]']
            behandlet_df['tang_vel'] = df[' Tang. Velocity            [m/s]']

            # Beregn azimuth_dot og elevation_dot
            delta_azimuth = behandlet_df['azimuth'].shift(-1) - behandlet_df['azimuth'].shift(1)
            delta_time = (behandlet_df['Datetime'].shift(-1) - behandlet_df['Datetime'].shift(1)).dt.total_seconds()
            behandlet_df['azimuth_dot'] = delta_azimuth / delta_time

            delta_elevation = behandlet_df['elevation'].shift(-1) - behandlet_df['elevation'].shift(1)
            behandlet_df['elevation_dot'] = delta_elevation / delta_time

            behandlet_df = behandlet_df.dropna().reset_index(drop=True)

            # Gem første csv (før filter)
            behandlet_df.to_csv(output_filepath, index=False)

            # Sortér og filtrér på tid (minimum 20 sek mellem målinger)
            behandlet_df['Datetime'] = pd.to_datetime(behandlet_df['Datetime'])
            behandlet_df = behandlet_df.sort_values('Datetime').reset_index(drop=True)

            filtered_indices = [0]
            last_time = behandlet_df.loc[0, 'Datetime']
            for i in range(1, len(behandlet_df)):
                if (behandlet_df.loc[i, 'Datetime'] - last_time).total_seconds() >= 20:
                    filtered_indices.append(i)
                    last_time = behandlet_df.loc[i, 'Datetime']

            behandlet_df = behandlet_df.iloc[filtered_indices].reset_index(drop=True)


            # Beregn r og v vektorer via din Radar_TLE funktion
            Radar_R_V = Radar_TLE(behandlet_df)
            behandlet_df['r_vec X'] = np.array(Radar_R_V[0]).T[0]
            behandlet_df['r_vec Y'] = np.array(Radar_R_V[0]).T[1]
            behandlet_df['r_vec Z'] = np.array(Radar_R_V[0]).T[2]
            behandlet_df['v_vec X'] = np.array(Radar_R_V[1]).T[0]
            behandlet_df['v_vec Y'] = np.array(Radar_R_V[1]).T[1]
            behandlet_df['v_vec Z'] = np.array(Radar_R_V[1]).T[2]
            behandlet_df['v_rho X'] = np.array(Radar_R_V[2]).T[0]
            behandlet_df['v_rho Y'] = np.array(Radar_R_V[2]).T[1]
            behandlet_df['v_rho Z'] = np.array(Radar_R_V[2]).T[2]
            behandlet_df['v_site X'] = np.array(Radar_R_V[3]).T[0]
            behandlet_df['v_site Y'] = np.array(Radar_R_V[3]).T[1]
            behandlet_df['v_site Z'] = np.array(Radar_R_V[3]).T[2]

                        # Data formateres om til kepel funktion
            TLE = []
            for r_vec, v_vec in zip(Radar_R_V[0], Radar_R_V[1]):
                TLE.append(kepel(r_vec, v_vec, GM=3.986004415e14))

            #Omformatere kepel outout til 2 linjer TLE format
            TLE_LINES = format_TLE(behandlet_df, TLE, NoradID=16182)
            LINE1 = np.array(TLE_LINES).T[0]
            LINE2 = np.array(TLE_LINES).T[1]
            behandlet_df['TLE Line 1'] = LINE1
            behandlet_df['TLE Line 2'] = LINE2

            # Beregn gennemsnitlige TLE linjer
            mean_TLE_Line1, mean_TLE_Line2 = format_TLE_mean(behandlet_df,compute_average_orbital_elements(TLE), NoradID=16182)[0], format_TLE_mean(behandlet_df,compute_average_orbital_elements(TLE), NoradID=16182)[1]
            behandlet_df['mean_TLE_Line1'] = mean_TLE_Line1
            behandlet_df['mean_TLE_Line2'] = mean_TLE_Line2


            # Gem den endelige csv efter vektorberegninger
            behandlet_df.to_csv(output_filepath, index=False)

            # Gem den endelige csv efter vektorberegninger
            behandlet_df.to_csv(output_filepath, index=False)

            print(f"Gemte behandlet data til: {output_filepath}")
    print("Færdig med at behandle alle radar data.\n")


def process_radar_folders(main_folder):
    import os
    import numpy as np
    import pandas as pd
    from datetime import datetime, timedelta
    from astropy.time import Time
    from astropy.coordinates import EarthLocation, AltAz, SkyCoord
    import astropy.units as u
    from Radar_TLE import Radar_TLE
    from keplerTLE import kepel

    # Gennemløb alle undermapper
    for root, dirs, files in os.walk(main_folder):
        asc_files = [file for file in files if file.endswith('.asc')]
        
        # Kun hvis der er asc fil i undermappen
        if asc_files:
            asc_file = asc_files[0]
            filepath = os.path.join(root, asc_file)
            output_filepath = os.path.join(root, 'behandlet_radar_data.csv')
            print(f"Behandler: {filepath}")

            # ----------- Læs ASC fil ------------
            with open(filepath, encoding="latin1") as f:
                lines = f.readlines()

            raw_colnames = lines[52].strip()
            raw_units = lines[53].strip()

            colnames = raw_colnames.split(",  ")
            units = raw_units.split(", ")

            combined_headers = [f"{n} {u}" if i < len(units) and u else n
                                for i, (n, u) in enumerate(zip(colnames, units))]

            df = pd.read_csv(filepath, skiprows=54, sep=r"\s*,\s*", engine='python',
                             header=None, encoding="latin1", usecols=range(len(combined_headers)))
            df.columns = combined_headers

            # ----------- Behandling af observationerne ------------
            year, month, day = 2025, 3, 31
            seconds_array = df['     Time_UTC            [s]']
            base_time = datetime(year, month, day)
            datetimes = np.array([base_time + timedelta(seconds=s) for s in seconds_array])
            behandlet_df = pd.DataFrame({'Datetime': datetimes})

            # Lokation (fast)
            lat_deg, lon_deg, alt_m = 55.89160919, 12.41544724, 87.339
            location = EarthLocation(lat=lat_deg*u.deg, lon=lon_deg*u.deg, height=alt_m*u.m)
            behandlet_df['Lat'] = lat_deg
            behandlet_df['Lon'] = lon_deg
            behandlet_df['Alt'] = alt_m

            time = Time(datetimes, scale='utc')
            gcrs = location.get_gcrs(obstime=time)
            eci_xyz = gcrs.cartesian.xyz.to(u.m).T.value
            behandlet_df['X'], behandlet_df['Y'], behandlet_df['Z'] = eci_xyz[:, 0], eci_xyz[:, 1], eci_xyz[:, 2]

            itrs = location.get_itrs(obstime=time)
            ecef_xyz = itrs.cartesian.xyz.to(u.m).T.value
            behandlet_df['X_ECEF'], behandlet_df['Y_ECEF'], behandlet_df['Z_ECEF'] = ecef_xyz[:, 0], ecef_xyz[:, 1], ecef_xyz[:, 2]

            # RA/DEC beregnes
            az = df[' Azimuth (rad)           [deg]'].values * u.deg
            el = df[' Elevation(rad)            [deg]'].values * u.deg
            altaz_frame = AltAz(obstime=time, location=location)
            coord_altaz = SkyCoord(az=az, alt=el, frame=altaz_frame)
            coord_icrs = coord_altaz.transform_to('icrs')
            behandlet_df['RA'] = coord_icrs.ra.to(u.deg).value
            behandlet_df['DEC'] = coord_icrs.dec.to(u.deg).value

            # Beregn RA/DEC fejl
            ra_errors, dec_errors = [], []
            az_err = df['    AZ_err_mea           [deg]'].values * u.deg
            el_err = df['    EL_err_mea           [deg]'].values * u.deg

            def clip_elevation(alt): return np.clip(alt.to(u.deg).value, -90.0, 90.0) * u.deg

            for i in range(len(df)):
                az_i, el_i, time_i = az[i], el[i], time[i]
                az_err_i, el_err_i = az_err[i], el_err[i]
                frame = AltAz(obstime=time_i, location=location)

                coord_az_plus = SkyCoord(az=az_i + az_err_i, alt=el_i, frame=frame).transform_to('icrs')
                coord_az_minus = SkyCoord(az=az_i - az_err_i, alt=el_i, frame=frame).transform_to('icrs')

                el_plus = clip_elevation(el_i + el_err_i)
                el_minus = clip_elevation(el_i - el_err_i)
                coord_el_plus = SkyCoord(az=az_i, alt=el_plus, frame=frame).transform_to('icrs')
                coord_el_minus = SkyCoord(az=az_i, alt=el_minus, frame=frame).transform_to('icrs')

                ra_err_i = np.sqrt(((coord_az_plus.ra - coord_az_minus.ra).to(u.deg).value / 2)**2 +
                                   ((coord_el_plus.ra - coord_el_minus.ra).to(u.deg).value / 2)**2)
                dec_err_i = np.sqrt(((coord_az_plus.dec - coord_az_minus.dec).to(u.deg).value / 2)**2 +
                                    ((coord_el_plus.dec - coord_el_minus.dec).to(u.deg).value / 2)**2)

                ra_errors.append(ra_err_i)
                dec_errors.append(dec_err_i)

            behandlet_df['RA_error'] = ra_errors
            behandlet_df['DEC_error'] = dec_errors

            behandlet_df['afstand'] = df[' Sl.Range (rad)              [m]']
            behandlet_df['azimuth'] = df[' Azimuth (rad)           [deg]']
            behandlet_df['elevation'] = df[' Elevation(rad)            [deg]']
            behandlet_df['radial_Vel'] = df[' Rad. Vel.(rad)            [m/s]']
            behandlet_df['tang_vel'] = df[' Tang. Velocity            [m/s]']

            # Beregn azimuth_dot og elevation_dot
            delta_azimuth = behandlet_df['azimuth'].shift(-1) - behandlet_df['azimuth'].shift(1)
            delta_time = (behandlet_df['Datetime'].shift(-1) - behandlet_df['Datetime'].shift(1)).dt.total_seconds()
            behandlet_df['azimuth_dot'] = delta_azimuth / delta_time

            delta_elevation = behandlet_df['elevation'].shift(-1) - behandlet_df['elevation'].shift(1)
            behandlet_df['elevation_dot'] = delta_elevation / delta_time

            behandlet_df = behandlet_df.dropna().reset_index(drop=True)


            # Beregn r og v vektorer via din Radar_TLE funktion
            Radar_R_V = Radar_TLE(behandlet_df)
            behandlet_df['r_vec X'] = np.array(Radar_R_V[0]).T[0]
            behandlet_df['r_vec Y'] = np.array(Radar_R_V[0]).T[1]
            behandlet_df['r_vec Z'] = np.array(Radar_R_V[0]).T[2]
            behandlet_df['v_vec X'] = np.array(Radar_R_V[1]).T[0]
            behandlet_df['v_vec Y'] = np.array(Radar_R_V[1]).T[1]
            behandlet_df['v_vec Z'] = np.array(Radar_R_V[1]).T[2]
            behandlet_df['v_rho X'] = np.array(Radar_R_V[2]).T[0]
            behandlet_df['v_rho Y'] = np.array(Radar_R_V[2]).T[1]
            behandlet_df['v_rho Z'] = np.array(Radar_R_V[2]).T[2]
            behandlet_df['v_site X'] = np.array(Radar_R_V[3]).T[0]
            behandlet_df['v_site Y'] = np.array(Radar_R_V[3]).T[1]
            behandlet_df['v_site Z'] = np.array(Radar_R_V[3]).T[2]

                        # Data formateres om til kepel funktion
            TLE = []
            for r_vec, v_vec in zip(Radar_R_V[0], Radar_R_V[1]):
                TLE.append(kepel(r_vec, v_vec, GM=3.986004415e14))

            #Omformatere kepel outout til 2 linjer TLE format
            TLE_LINES = format_TLE(behandlet_df, TLE, NoradID=16182)
            LINE1 = np.array(TLE_LINES).T[0]
            LINE2 = np.array(TLE_LINES).T[1]
            behandlet_df['TLE Line 1'] = LINE1
            behandlet_df['TLE Line 2'] = LINE2

            # Beregn gennemsnitlige TLE linjer
            mean_TLE_Line1, mean_TLE_Line2 = format_TLE_mean(behandlet_df,compute_average_orbital_elements(TLE), NoradID=16182)[0], format_TLE_mean(behandlet_df,compute_average_orbital_elements(TLE), NoradID=16182)[1]
            behandlet_df['mean_TLE_Line1'] = mean_TLE_Line1
            behandlet_df['mean_TLE_Line2'] = mean_TLE_Line2


            # Gem den endelige csv efter vektorberegninger
            behandlet_df.to_csv(output_filepath, index=False)

            # Gem den endelige csv efter vektorberegninger
            behandlet_df.to_csv(output_filepath, index=False)

            print(f"Gemte behandlet data til: {output_filepath}")
    print("Færdig med at behandle alle radar data.\n")

def medregn_pixelforskydning(df_coordinates, df_internet):
    data_sat_pos = []
    for i in range(len(df_coordinates)):
        data = (df_internet['orientation'][i], df_internet['ra'][i], df_internet['dec'][i], df_internet['pixscale'][i], df_coordinates['size'][i], (df_coordinates['midpoint'][i]))
        # Hvis alle værdier er gyldige, så tilføj satellitens position til listen
        if all(value is not None and not pd.isna(value) for value in data):
            data = data[:-2] + eval(data[-2]) + eval(data[-1])
            data_sat_pos.append(beregn_sat_pos(*data))
    return data_sat_pos

def medregn_pixelforskydning_teleskob(df_coordinates, df_internet, df_local):
    ra = []
    dec = []
    for i in range(len(df_local['RA'])):
        ra.append(hms_to_decimal(df_local['RA'][i]))
        dec.append(dms_to_decimal(df_local['DEC'][i]))

    data_sat_pos = []
    for i in range(len(df_coordinates)):
        data = (df_internet['orientation'][i], ra[i], dec[i], df_internet['pixscale'][i], df_coordinates['size'][i], (df_coordinates['midpoint'][i]))
        # Hvis alle værdier er gyldige, så tilføj satellitens position til listen
        if all(value is not None and not pd.isna(value) for value in data):
            data = data[:-2] + eval(data[-2]) + eval(data[-1])
            data_sat_pos.append(beregn_sat_pos(*data))

    return data_sat_pos


def calculate_satellite_data(df_local, tle_line1, tle_line2):
    from datetime import datetime
    from skyfield.api import load, EarthSatellite, wgs84
    from numpy import arccos, degrees
    import numpy as np

    # Initialiser lister
    vinkel_sol_jord = []
    afstand_sat_observator = []
    satellite_positions = []
    earth_positions = []
    observation_points = []

    # Konverter dato-streng til tuple

    def convert_to_tuple(date_str):
        try:
            # Først prøv med mikrosekunder
            dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S.%f")
        except ValueError:
            # Hvis det fejler, prøv med T-format
            dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%f")

        return (dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)


    # Anvend funktionen på kolonnen "DATE-OBS"
    df_local["DATE-OBS-Tuple"] = df_local["DATE-OBS"].apply(convert_to_tuple)

    # Beregn vinkel mellem to vektorer
    def angle_between(v1, v2):
        dot_product = np.dot(v1, v2)
        norm_product = np.linalg.norm(v1) * np.linalg.norm(v2)
        return degrees(arccos(dot_product / norm_product))

    # Indlæs efemerider for Solen og Jorden
    ts = load.timescale()
    planets = load('de421.bsp')
    sun = planets['sun']
    earth = planets['earth']

    # Opret satellitobjekt
    satellite = EarthSatellite(tle_line1, tle_line2, 'Satellite', ts)

    # Beregn data for hver række i df_local
    for n, date_tuple in enumerate(df_local["DATE-OBS-Tuple"]):
        t = ts.utc(*date_tuple)

        # Satellittens position i ECI (km)
        sat_pos = satellite.at(t).position.km

        # Solens position i ECI (km)
        sun_pos = sun.at(t).position.km

        # Jordposition givet ved latitude og longitude
        lat_col = "LAT--OBS" if "LAT--OBS" in df_local.columns else "LAT-OBS"
        lat, lon, ele = df_local[lat_col][n], df_local["LONG-OBS"][n], df_local["ELEV-OBS"][n]
        earth_location = wgs84.latlon(lat, lon, ele)
        earth_pos_ecef = earth_location.at(t).position.km

        # Brug Jorden som reference og find positionen relativt til stjernerne
        earth_eci = earth.at(t).observe(earth).position.km
        earth_pos_eci = earth_pos_ecef + earth_eci

        # Beregn vinkel mellem Jordpositionen og Solen set fra satellitten
        angle = angle_between(earth_pos_eci - sat_pos, sun_pos - sat_pos)
        vinkel_sol_jord.append(angle)

        # Beregn afstanden mellem satellitten og observatøren
        distance = np.linalg.norm(sat_pos - earth_pos_eci)
        afstand_sat_observator.append(distance)

        # Gem positioner
        satellite_positions.append(sat_pos)
        earth_positions.append(earth_eci)
        observation_points.append(earth_pos_eci)

    # Returner resultaterne
    return np.array(afstand_sat_observator), np.array(vinkel_sol_jord), satellite_positions, earth_positions, observation_points

def ra_dec_to_eci(ra, dec, distance):
    """
    Konverterer RA, Dec og afstand til ECI-koordinater.

    Parameters:
    ra (float): Right Ascension (RA) i grader.
    dec (float): Declination (Dec) i grader.
    distance (float): Afstanden til satellitten (i km eller m).

    Returns:
    tuple: Satellittens position i ECI-koordinater (x, y, z).
    """
    # Konverter RA og Dec fra grader til radianer
    ra_rad = np.radians(ra)
    dec_rad = np.radians(dec)

    # Beregn ECI-koordinater # Se afsnit 2.2
    x = distance * np.cos(dec_rad) * np.cos(ra_rad)
    y = distance * np.cos(dec_rad) * np.sin(ra_rad)
    z = distance * np.sin(dec_rad)

    return x, y, z


def write_tle_lines(NoradID=00000, classification='U', Launch_year='00', Launch_number='000', 
                    internatinal_designator='A  ', epoch_year='00', epoch_day='000.00000000',
                    mean_motion_dot='.000000000', mean_motion_ddot='00000-0', drag_term='00000-0', 
                    Ephemris_type='1', Element_nr='0000', inclination='000.0000', raan='000.0000', 
                    eccentricity='0000000', argument_of_perigee='000.0000', mean_anomaly='000.0000', 
                    mean_motion='000.00000000', revolution_number='00000'):
    
    def tle_checksum(line):
        total = sum(int(c) for c in line if c.isdigit()) + line.count('-')
        return str(total % 10)
    
    # --- Konstruktion af Line 1 ---
    LINE1 = '1 xxxxxu xxxxxaaa xxxxx.xxxxxxxx +.xxxxxxxx +xxxxx-x +xxxxx-x x xxxxx'
    LINE1 = '1' + LINE1[1:]
    LINE1 = LINE1[:2] + str(NoradID).zfill(5) + LINE1[7:]
    LINE1 = LINE1[:7] + classification + LINE1[8:]
    LINE1 = LINE1[:9] + Launch_year + LINE1[11:]
    LINE1 = LINE1[:11] + Launch_number.zfill(3) + LINE1[14:]
    LINE1 = LINE1[:14] + internatinal_designator + LINE1[17:]
    LINE1 = LINE1[:18] + epoch_year + LINE1[20:]
    LINE1 = LINE1[:20] + epoch_day + LINE1[32:]
    LINE1 = LINE1[:33] + mean_motion_dot + LINE1[43:]
    LINE1 = LINE1[:45] + mean_motion_ddot + LINE1[52:]
    LINE1 = LINE1[:54] + drag_term + LINE1[61:]
    LINE1 = LINE1[:62] + Ephemris_type + LINE1[63:]
    LINE1 = LINE1[:64] + Element_nr.zfill(4) + LINE1[68:]
    LINE1 = LINE1[:68] + tle_checksum(LINE1)

    # --- Konstruktion af Line 2 ---
    LINE2 = '2 xxxxx xxx.xxxx xxx.xxxx xxxxxxx xxx.xxxx xxx.xxxx xx.xxxxxxxxxxxxxx'
    LINE2 = '2' + LINE2[1:]
    LINE2 = LINE2[:2] + str(NoradID).zfill(5) + LINE2[7:]
    LINE2 = LINE2[:8] + inclination.rjust(8) + LINE2[16:]
    LINE2 = LINE2[:17] + raan.rjust(8) + LINE2[25:]
    LINE2 = LINE2[:26] + eccentricity.zfill(7) + LINE2[33:]
    LINE2 = LINE2[:34] + argument_of_perigee.rjust(8) + LINE2[42:]
    LINE2 = LINE2[:43] + mean_anomaly.rjust(8) + LINE2[51:]
    LINE2 = LINE2[:52] + mean_motion.rjust(11) + LINE2[63:]
    LINE2 = LINE2[:63] + revolution_number.zfill(5) + LINE2[68:]
    LINE2 = LINE2[:68] + tle_checksum(LINE2)

    return LINE1, LINE2

def hms_to_decimal(hms_str):
    # Split the HMS string into components
    hms_components = hms_str.split(':')
    hours = float(hms_components[0])
    minutes = float(hms_components[1])
    seconds = float(hms_components[2])

    # Convert HMS to decimal degrees
    decimal_degrees = (hours + (minutes / 60) + (seconds / 3600)) * 15

    return decimal_degrees

def dms_to_decimal(dms_str):
    # Split the DMS string into components
    dms_components = dms_str.split(':')
    degrees = float(dms_components[0])
    minutes = float(dms_components[1])
    seconds = float(dms_components[2])

    # Handle negative degrees
    if degrees < 0:
        decimal_degrees = degrees - (minutes / 60) - (seconds / 3600)
    else:
        decimal_degrees = degrees + (minutes / 60) + (seconds / 3600)

    return decimal_degrees

# API-nøgle fra Astrometry.net
API_KEY = "vwecrxkbvasactyg"

def get_image_data_internet(filepath):
    # 1. Start en session
    session_url = "http://nova.astrometry.net/api/login"
    session_response = requests.post(session_url, data={"request-json": '{"apikey": "' + API_KEY + '"}'} )
    session_data = session_response.json()
    session_id = session_data["session"]

    # 2. Upload billede
    upload_url = "http://nova.astrometry.net/api/upload"
    files = {"file": open(filepath, "rb")}
    upload_response = requests.post(upload_url, data={"request-json": '{"session": "' + session_id + '"}'}, files=files)
    upload_data = upload_response.json()
    submission_id = upload_data["subid"]

    # 3. Vente på job-id
    job_id = None
    while not job_id:
        time.sleep(5)
        status_response = requests.get(f"http://nova.astrometry.net/api/submissions/{submission_id}")
        status_data = status_response.json()
        jobs = status_data.get("jobs")
        if jobs and jobs[0]:  
            job_id = jobs[0]
        print("Venter på job-id...")

    # 4. Vente på, at jobbet bliver færdigt
    job_status = "running"
    while job_status in ["running", "solving"]:
        time.sleep(5)  # Vent lidt længere mellem status-tjek
        job_status_response = requests.get(f"http://nova.astrometry.net/api/jobs/{job_id}/info")
        job_status_data = job_status_response.json()
        job_status = job_status_data.get("status", "unknown")
        print(f"Job-status: {job_status}")

        if job_status == "failure":
            print("Jobbet fejlede. Astrometry.net kunne ikke kalibrere billedet.")
            return None

    # 5. Hente kalibreringsdata
    result_url = f"http://nova.astrometry.net/api/jobs/{job_id}/calibration"
    result_response = requests.get(result_url)
    result_data = result_response.json()

    return(result_data)

def get_image_data_local(filepath):
    # Load FITS image
    hdul = fits.open(filepath)
    header = hdul[0].header
    hdul.close()

    # Konverter header til dictionary
    header_dict = {key: header[key] for key in header.keys()}

    return header_dict

def gem_billede_header(directory):
    from Func_fagprojekt import hms_to_decimal, dms_to_decimal
    data_list = []
    
    for filename in os.listdir(directory):
        if filename.endswith(".fits"):
            filepath = os.path.join(directory, filename)
            data = get_image_data_local(filepath)
            if data is None:
                data = {}
            data['filename'] = filename
            data_list.append(data)
    
    df = pd.DataFrame(data_list)
    
    # Funktion der tilføjer millisekunder hvis de mangler
    def add_milliseconds(time_str, desired_length):
        if len(time_str) < desired_length:
            return time_str + '.000'
        else:
            return time_str

    df['UT'] = df['UT'].apply(lambda x: add_milliseconds(x, 12))          # 8 → 12
    df['DATE-OBS'] = df['DATE-OBS'].apply(lambda x: add_milliseconds(x, 23))  # 19 → 23
    df['DATE-BEG'] = df['DATE-BEG'].apply(lambda x: add_milliseconds(x, 23))
    df['DATE-END'] = df['DATE-END'].apply(lambda x: add_milliseconds(x, 23))

    ra = []
    dec = []
    for i in range(len(df['RA'])):
        ra.append(hms_to_decimal(df['RA'][i]))
        dec.append(dms_to_decimal(df['DEC'][i]))
    df['RA_decimal'] = ra
    df['DEC_decimal'] = dec
    # Konverter Julian Date til sekunder efter første måling
    jd_first = df["JD"].iloc[0]
    seconds_after_first_measurement = (df["JD"] - jd_first) * 86400  # 1 JD = 86400 sekunder

    # Tilføj den nye kolonne til DataFrame
    df["Seconds_After_First"] = seconds_after_first_measurement

    #tilføj kolonner som wcs genkender
    df['CRPIX1'] = df['NAXIS1'] / 2
    df['CRPIX2'] = df['NAXIS2'] / 2
    df["CRVAL1"] = df['RA_decimal']
    df['CRVAL2'] = df['DEC_decimal']

    df.to_csv(os.path.join(directory, 'local_output.csv'), index=False)
    return df

def gem_astrometrisk_analyse(directory):
    data_list = []
    n = 1
    for filename in os.listdir(directory):
        print(f"Behandler billede {n} af {len(os.listdir(directory))} filer")
        n += 1
        if filename.endswith(".fits"):
            filepath = os.path.join(directory, filename)
            data = get_image_data_internet(filepath)
            if data is None:
                data = {}
            data['filename'] = filename
            data_list.append(data)
        df = pd.DataFrame(data_list)
        df.to_csv(os.path.join(directory, 'Astrometrisk_Analyse.csv'), index=False)

    #tilføj kolonner som wcs genkender

    df["CRVAL1"] = df['ra']
    df['CRVAL2'] = df['dec']

    df.to_csv(os.path.join(directory, 'Astrometrisk_Analyse.csv'), index=False)


def calculate_satellite_data_radar(df_behandlet, tle_line1, tle_line2):
    from datetime import datetime
    from skyfield.api import load, EarthSatellite, wgs84
    from numpy import arccos, degrees
    import numpy as np

    # Initialiser lister
    vinkel_sol_jord = []
    afstand_sat_observator = []
    satellite_positions = []
    earth_positions = []
    observation_points = []

    # Konverter dato-streng til tuple

    def convert_to_tuple(date_str):
        for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
            try:
                dt = datetime.strptime(date_str, fmt)
                return (dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)
            except ValueError:
                continue
        # Hvis intet virker, kast en fejl
        raise ValueError(f"Ukendt datoformat: {date_str}")
  
    # Anvend funktionen på kolonnen "DATE-BEG"
    df_behandlet["DATE-BEG-Tuple"] = df_behandlet["Datetime"].apply(convert_to_tuple)

    # Indlæs efemerider for Solen og Jorden
    ts = load.timescale()
    planets = load('de421.bsp')
    earth = planets['earth']

    # Opret satellitobjekt
    satellite = EarthSatellite(tle_line1, tle_line2, 'Satellite', ts)

    # Beregn data for hver række i df_local
    for n, date_tuple in enumerate(df_behandlet["DATE-BEG-Tuple"]):
        t = ts.utc(*date_tuple)

        # Satellittens position i ECI (km)
        sat_pos = satellite.at(t).position.km

        # Jordposition givet ved latitude og longitude
        lat, lon, ele = df_behandlet['Lat'][n], df_behandlet['Lon'][n], df_behandlet['Alt'][n]
        earth_location = wgs84.latlon(lat, lon, ele)
        earth_pos_ecef = earth_location.at(t).position.km

        # Brug Jorden som reference og find positionen relativt til stjernerne
        earth_eci = earth.at(t).observe(earth).position.km
        earth_pos_eci = earth_pos_ecef + earth_eci

        # Beregn afstanden mellem satellitten og observatøren
        distance = np.linalg.norm(sat_pos - earth_pos_eci)
        afstand_sat_observator.append(distance)

        # Gem positioner
        satellite_positions.append(sat_pos)
        earth_positions.append(earth_eci)
        observation_points.append(earth_pos_eci)

    # Returner resultaterne
    return np.array(afstand_sat_observator), np.array(vinkel_sol_jord), satellite_positions, earth_positions, observation_points

def run_astap_on_directory(directory, astap_exe=r"C:\Program Files\astap\astap.exe"):
    results = []

    # find alle fits filer
    for filename in os.listdir(directory):
        if filename.lower().endswith(".fits"):
            filepath = os.path.join(directory, filename)
            wcsfile = os.path.join(directory, filename.replace(".fits", ".wcs"))

            # kør astap
            result = subprocess.run(
                [astap_exe, "-f", filepath, "-wcs", wcsfile],
                capture_output=True, text=True
            )

            if result.returncode != 0:
                print(f"ASTAP fejlede for {filename}: {result.stderr}")
                continue

            # læs header fra wcs-filen
            if os.path.exists(wcsfile):
                with fits.open(wcsfile) as hdul:
                    header = hdul[0].header
                    

                # konverter header til dict
                header_dict = {k: header[k] for k in header.keys() if k != ''}

                # tilføj filnavn
                header_dict["filename"] = filename

                results.append(header_dict)
                os.remove(wcsfile)

    # lav dataframe af alle headere
    df = pd.DataFrame(results)

    # Slet alle .ini-filer i output-mappen (ASTAP kan have lavet dem)
    for f in os.listdir(directory):
        if f.lower().endswith('.ini'):
            try:
                os.remove(os.path.join(directory, f))
            except Exception:
                pass

    return df

def pixel_to_radec(x, y, header_row):
    """
    ASTAP-kompatibel konvertering fra pixel til RA/DEC koordinater.
    Implementerer den fulde Gnomonic (Tangent Plane) projektion.
    """
    
    # Hent header værdier
    crpix1 = header_row["CRPIX1"]
    crpix2 = header_row["CRPIX2"]
    crval1 = header_row["CRVAL1"]  # α0 (RA reference) i grader
    crval2 = header_row["CRVAL2"]  # δ0 (DEC reference) i grader
    
    cd11 = header_row["CD1_1"]
    cd12 = header_row["CD1_2"] 
    cd21 = header_row["CD2_1"]
    cd22 = header_row["CD2_2"]
    
    # Step 1: Beregn pixel offset
    u = x - crpix1
    v = y - crpix2
    
    # For nu springer vi SIP korrektion over (U = u, V = v)
    U = u
    V = v
    
    # Step 2: Anvend CD matrix til standard koordinater
    xi = cd11 * U + cd12 * V  # ξ (xi)
    eta = cd21 * U + cd22 * V  # η (eta)
    
    # Step 3: Konverter til radianer for trigonometriske beregninger
    xi_rad = xi * np.pi / 180
    eta_rad = eta * np.pi / 180
    alpha0_rad = crval1 * np.pi / 180  # α0
    delta0_rad = crval2 * np.pi / 180  # δ0
    
    # Trigonometriske beregninger
    sin_delta0 = np.sin(delta0_rad)
    cos_delta0 = np.cos(delta0_rad)
    
    # Beregn delta (midlertidig variabel)
    delta = cos_delta0 - eta_rad * sin_delta0
    
    # Beregn α (RA) og δ (DEC)
    alpha_rad = alpha0_rad + np.arctan2(xi_rad, delta)
    delta_rad = np.arctan((sin_delta0 + eta_rad * cos_delta0) / np.sqrt(xi_rad**2 + delta**2))
    
    # Konverter tilbage til grader
    ra = alpha_rad * 180 / np.pi
    dec = delta_rad * 180 / np.pi
    
    return ra, dec

def compute_cd(sx, sy, theta_deg, dec0_deg=None, ra_units_on_sky=True):
    theta = np.deg2rad(-theta_deg)
    cd11 =  sx * np.cos(theta)
    cd12 = -sx * np.sin(theta)  # sx, ikke sy, og negativt fortegn
    cd21 =  sy * np.sin(theta)  # sy her
    cd22 =  sy * np.cos(theta)

    if not ra_units_on_sky:
        if dec0_deg is None:
            raise ValueError("dec0_deg påkrævet hvis ra_units_on_sky=False")
        cd11 /= np.cos(np.deg2rad(dec0_deg))
        cd12 /= np.cos(np.deg2rad(dec0_deg))

    return cd11, cd12, cd21, cd22