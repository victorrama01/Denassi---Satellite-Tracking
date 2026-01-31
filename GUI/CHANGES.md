# Ændringer til satelit-datahentning - Sammentallet

## 1. Ændringer i fetch_inthesky.py
- **Parameternavn ændret**: `timezone` → `utc_offset` (mere intuitivt)
- **Tidskonvertering**: Tidspunkter konverteres nu fra UTC til lokal tid direkte i funktionen ved brug af `utc_offset`
- **Eksempel**: `fetch_satellites_inthesky('2026-01-30', 66.996007, -50.621153, utc_offset=-2)`

## 2. Ændringer i Func_SatellitListe.py

### fetch_satellite_data_selenium() - NY WRAPPER
- Erstatter den gamle Heavens-Above scraper
- Kalder `fetch_satellites_inthesky()` direkte
- Konverterer data fra in-the-sky.org format til Heavens-Above format
- Returnerer DataFrame med kolonner:
  - SatName, NORAD, StartTime, HiTime, EndTime
  - StartAlt, StartAz, HiAlt, HiAz, EndAlt, EndAz
  - **Magnitude_Rise, Magnitude_High, Magnitude_Set** (alle 3 værdier bevarés!)

### fetch_satellite_data_with_tle()
- Fjernet den manuelle UTC offset-logik (gøres nu i fetch_inthesky())
- Kalder `fetch_satellite_data_selenium()` med `utc_offset` parameter
- Resten af flow-et er uændret

### update_satellite_tree()
- Treeview kolonner opdateret til at vise alle 3 magnitude-værdier:
  - 'Mag_Rise', 'Mag_High', 'Mag_Set'

### validate_csv_data()
- Tilføjet understøttelse for de nye magnitude-kolonner
- Fallback-logik: hvis kun én magnitude-kolonne findes, kopieres den til alle 3

## 3. GUI Input (Denassi tab)
- **periode** parameter: Kan STADIG bruges (men ignoreres - in-the-sky.org returnerer hele dagen)
- **utc_offset**: Sendes direkte til fetch-funktionen (-2 for dansk tid)

## 4. Data Format Fordele
✅ Alle 3 magnitude-værdier bevares (Rise, High, Set)
✅ Ingen faste tidsskift - UTC offset håndteres korrekt
✅ Morning/evening filtrering ikke nødvendig (kan implementeres på client-side hvis ønskes)
✅ Samme GUI og TLE-merge flow som før

## 5. Testing Resultat
- ✅ Fetched 11,178 satellitter
- ✅ Tider konverteret til lokal tid (-2 timer)
- ✅ Alle magnitude-værdier tilstede
- ✅ Kolonner mapper korrekt til GUI format
- ✅ Ingen syntaxfejl i Func_SatellitListe.py
