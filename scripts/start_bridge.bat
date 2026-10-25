@echo off
chcp 65001 >nul
rem 若手机USB连着且电脑代理不可用，可借手机代理线路（可选，按需启用）
rem "%~dp0..\tools\adb\adb.exe" forward tcp:17890 tcp:7890 >nul 2>nul
cd /d %~dp0
where python >nul 2>nul
if %errorlevel%==0 (
  python tg_bridge.py
) else (
  py tg_bridge.py
)
pause
