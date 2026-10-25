@echo off
chcp 65001 >nul
start "" /min "%~dp0tools\syncthing-windows-amd64-v2.1.7\syncthing.exe" --no-browser
