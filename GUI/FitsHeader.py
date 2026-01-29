def add_pwi4_data_to_header(header, mount_status_raw):
    """
    Tilføjer alle PWI4 data fra mount.status().raw til FITS header med intelligent mapping.
    
    Præfiks-system (første tegn):
    - M_ = mount
    - R_ = rotator
    - S_ = site
    - P_ = pwi4
    - X_ = response
    - F_ = focuser
    - A_ = autofocus/m3
    
    Vigtige felter beholder key-navne fra Func_KameraInstillinger (key_mappings).
    Andre felter får manual intelligente forkortelser for læsbarhed.
    """
    
    # Vigtige mappings som skal beholde samme key-navne som Func_KameraInstillinger
    key_mappings = {
        'mount.ra_apparent_hours': 'RA_APP',
        'mount.dec_apparent_degs': 'DEC_APP',
        'mount.ra_j2000_hours': 'RA_J2000',
        'mount.dec_j2000_degs': 'DEC_J200',
        'mount.altitude_degs': 'ALT_TEL',
        'mount.azimuth_degs': 'AZ_TEL',
        'mount.is_slewing': 'SLEWING',
        'mount.is_tracking': 'TRACKING',
        'mount.julian_date': 'JD',
        'mount.distance_to_sun_degs': 'DIST_SUN',
        'mount.timestamp_utc': 'PWI4MTS',
        'mount.update_duration_msec': 'PWI4DUR',
        'mount.field_angle_here_degs': 'FA_HERE',
        'mount.field_angle_at_target_degs': 'FA_TARG',
        'site.latitude_degs': 'LAT-OBS',
        'site.longitude_degs': 'LONG-OBS',
        'site.height_meters': 'ELEV-OBS',
        'pwi4.version': 'PWI4VER',
        'response.timestamp_utc': 'PWI4TIME',
        'rotator.field_angle_degs': 'ROT_ANG',
        'rotator.mech_position_degs': 'ROT_MECH',
    }
    
    # Manuel mapping for alle andre felter - sikrer unikke, læsbare forkortelser
    manual_mapping = {
        # Mount - koordinater
        'mount.ra_apparent_degs': 'M_RA_APD',
        'mount.ra_j2000_degs': 'M_RA_J2D',
        'mount.target_ra_apparent_hours': 'M_TRAPH',
        'mount.target_ra_apparent_degs': 'M_TRAPD',
        'mount.target_dec_apparent_degs': 'M_TDAPD',
        'mount.target_ra_j2000_hours': 'M_TRA_J2H',
        'mount.target_dec_j2000_degs': 'M_TDC_J2D',
        
        # Mount - teleskop info
        'mount.is_connected': 'M_CONN',
        'mount.geometry': 'M_GEOM',
        'mount.slew_time_constant': 'M_SLEWT',
        'mount.update_count': 'M_UPDCNT',
        'mount.axis0_wrap_range_min_degs': 'M_AX0MIN',
        
        # Mount - offset data
        'mount.offsets.ra_arcsec.total': 'M_OFFRAT',
        'mount.offsets.ra_arcsec.rate': 'M_OFFRAR',
        'mount.offsets.dec_arcsec.total': 'M_OFFDCT',
        'mount.offsets.dec_arcsec.rate': 'M_OFFDCR',
        'mount.offsets.axis0_arcsec.total': 'M_OFF_AX0T',
        'mount.offsets.axis0_arcsec.rate': 'M_OFF_AX0R',
        'mount.offsets.axis1_arcsec.total': 'M_OFF_AX1T',
        'mount.offsets.axis1_arcsec.rate': 'M_OFF_AX1R',
        'mount.offsets.path_arcsec.total': 'M_OFF_PTHT',
        'mount.offsets.path_arcsec.rate': 'M_OFF_PTHR',
        'mount.offsets.transverse_arcsec.total': 'M_OFF_TRNT',
        'mount.offsets.transverse_arcsec.rate': 'M_OFF_TRNR',
        
        # Mount - spiral offset
        'mount.spiral_offset.x': 'M_SPL_X',
        'mount.spiral_offset.y': 'M_SPL_Y',
        'mount.spiral_offset.x_step_arcsec': 'M_SPL_XST',
        'mount.spiral_offset.y_step_arcsec': 'M_SPL_YST',
        
        # Mount - axis 0
        'mount.axis0.is_enabled': 'M_AX0ENA',
        'mount.axis0.rms_error_arcsec': 'M_AX0RMS',
        'mount.axis0.dist_to_target_arcsec': 'M_AX0DIS',
        'mount.axis0.servo_error_arcsec': 'M_AX0SRV',
        'mount.axis0.target_mech_position_degs': 'M_AX0TRG',
        'mount.axis0.position_degs': 'M_AX0POS',
        'mount.axis0.max_velocity_degs_per_sec': 'M_AX0VEL',
        'mount.axis0.setpoint_velocity_degs_per_sec': 'M_AX0SVL',
        'mount.axis0.measured_velocity_degs_per_sec': 'M_AX0MVL',
        'mount.axis0.acceleration_degs_per_sec_sqr': 'M_AX0ACC',
        'mount.axis0.measured_current_amps': 'M_AX0CUR',
        
        # Mount - axis 1
        'mount.axis1.is_enabled': 'M_AX1ENA',
        'mount.axis1.rms_error_arcsec': 'M_AX1RMS',
        'mount.axis1.dist_to_target_arcsec': 'M_AX1DIS',
        'mount.axis1.servo_error_arcsec': 'M_AX1SRV',
        'mount.axis1.target_mech_position_degs': 'M_AX1TRG',
        'mount.axis1.position_degs': 'M_AX1POS',
        'mount.axis1.max_velocity_degs_per_sec': 'M_AX1VEL',
        'mount.axis1.setpoint_velocity_degs_per_sec': 'M_AX1SVL',
        'mount.axis1.measured_velocity_degs_per_sec': 'M_AX1MVL',
        'mount.axis1.acceleration_degs_per_sec_sqr': 'M_AX1ACC',
        'mount.axis1.measured_current_amps': 'M_AX1CUR',
        
        # Mount - model
        'mount.model.rms_error_arcsec': 'M_MOD_RMS',
        
        # Mount - field angle
        'mount.field_angle_rate_at_target_degs_per_sec': 'M_FARATE',
        'mount.path_angle_at_target_degs': 'M_PTHANG',
        'mount.path_angle_rate_at_target_degs_per_sec': 'M_PTRAT',
        
        # Site
        'site.lmst_hours': 'S_LMST',
        
        # PWI4 version fields
        'pwi4.version_field[0]': 'P_VER_0',
        'pwi4.version_field[1]': 'P_VER_1',
        'pwi4.version_field[2]': 'P_VER_2',
        'pwi4.version_field[3]': 'P_VER_3',
        
        # Rotator
        'rotator.exists': 'R_EXISTS',
        'rotator.index': 'R_INDEX',
        'rotator.is_connected': 'R_CONCT',
        'rotator.is_enabled': 'R_ENA',
        'rotator.is_moving': 'R_MOVE',
        'rotator.is_slewing': 'R_SLEW',
        
        # Focuser
        'focuser.exists': 'F_EXISTS',
        'focuser.is_connected': 'F_CONCT',
        'focuser.is_enabled': 'F_ENA',
        'focuser.position': 'F_POS',
        'focuser.is_moving': 'F_MOVE',
        
        # M3 og Autofocus
        'm3.exists': 'A_M3_EXS',
        'm3.port': 'A_M3PORT',
        'autofocus.is_running': 'A_RUNNING',
        'autofocus.success': 'A_SUCCES',
        'autofocus.best_position': 'A_BESTPOS',
        'autofocus.tolerance': 'A_TOLRNCE',
    }
    
    # Tilføj alle data med korrekte key-navne
    for raw_key, value in mount_status_raw.items():
        try:
            # Hvis der er en vigtig mapping, brug den (fra Func_KameraInstillinger)
            if raw_key in key_mappings:
                fits_key = key_mappings[raw_key]
                
                # Konvertér værdier til passende typer
                if raw_key in ['mount.is_slewing', 'mount.is_tracking']:
                    converted_value = value.lower() == 'true' if isinstance(value, str) else bool(value)
                elif raw_key == 'mount.update_duration_msec':
                    converted_value = int(float(value))
                elif raw_key in ['mount.ra_apparent_hours', 'mount.ra_j2000_hours']:
                    float_val = float(value)
                    header[fits_key] = float_val
                    if raw_key == 'mount.ra_j2000_hours':
                        header['RA'] = float_val * 15.0
                    continue
                elif raw_key == 'mount.dec_j2000_degs':
                    float_val = float(value)
                    header[fits_key] = float_val
                    header['DEC'] = float_val
                    continue
                else:
                    try:
                        converted_value = float(value)
                    except (ValueError, TypeError):
                        converted_value = value
                
                header[fits_key] = converted_value
            
            # Hvis der er en manuel mapping, brug den
            elif raw_key in manual_mapping:
                fits_key = manual_mapping[raw_key]
                
                try:
                    # Konvertér værdier
                    if isinstance(value, str):
                        if value.lower() in ['true', 'false']:
                            converted_value = value.lower() == 'true'
                        else:
                            try:
                                converted_value = float(value)
                            except (ValueError, TypeError):
                                converted_value = value
                    else:
                        converted_value = value
                    
                    if fits_key not in header:
                        header[fits_key] = converted_value
                except Exception:
                    pass
        
        except Exception:
            pass
    
    return header