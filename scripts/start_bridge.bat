@echo off
chcp 65001 >nul
rem 若手机USB连着，借手机ClashMi的代理线路（电脑机场到期时的自动兜底）
E:\life-os\tools\adb\adb.exe forward tcp:17890 tcp:7890 >nul 2>nul
cd /d E:\life-os\scripts
where python >nul 2>nul
if %errorlevel%==0 (
  python tg_bridge.py
) else (
  py tg_bridge.py
)
pause
