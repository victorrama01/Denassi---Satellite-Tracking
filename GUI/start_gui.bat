@echo off
REM Batch script to start the satellite tracking GUI
REM This script activates the correct conda environment and starts the GUI

title Satellite Tracking GUI

REM Change to the GUI directory
cd /d "C:\Users\denassi\Documents\GUI - Repo\Denassi---Satellite-Tracking\GUI"

REM Activate conda environment and start the GUI
echo Starting Satellite Tracking GUI...
call "C:\Users\denassi\miniconda3\Scripts\activate.bat" Denassi_specialkursus
python GUI.py

REM Pause to see any error messages
pause

REM Close when done
exit