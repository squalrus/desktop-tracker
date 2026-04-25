@echo off
echo Setting up Windows Virtual Desktop Tracker Auto-Start...
echo.

:: Define the path to the Windows Startup folder
set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "VBS_FILE=%STARTUP_FOLDER%\DesktopTracker.vbs"

:: Get the current folder path where the tracker is located
set "TRACKER_DIR=%~dp0"

:: Create the VBScript file in the Startup folder
echo Set WshShell = CreateObject("WScript.Shell") > "%VBS_FILE%"
echo WshShell.CurrentDirectory = "%TRACKER_DIR%" >> "%VBS_FILE%"
echo WshShell.Run "pythonw.exe tracker.py", 0, False >> "%VBS_FILE%"

echo Success! The tracker will now run invisibly in the background
echo every time you log into Windows.
echo.
pause
