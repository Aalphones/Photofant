@echo off
REM Photofant starten — Backend (http://localhost:8000) + Frontend (http://localhost:4200)
REM Voraussetzung: install.cmd wurde ausgefuehrt.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1"
