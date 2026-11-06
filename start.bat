@echo off
setlocal
title dv365-music-downloader
pushd "%~dp0"
if errorlevel 1 exit /b 1

if exist ".venv\Scripts\python.exe" goto source
if exist "dv365-music-downloader.exe" goto portable
if exist "dist\dv365-music-downloader\dv365-music-downloader.exe" goto bundle

echo No Python virtual environment or packaged application was found.
echo See DESKTOP_PREVIEW.md for setup instructions.
set "launch_code=1"
goto finish

:source
".venv\Scripts\python.exe" -m music_dl.desktop
set "launch_code=%errorlevel%"
goto finish

:portable
"dv365-music-downloader.exe"
set "launch_code=%errorlevel%"
goto finish

:bundle
"dist\dv365-music-downloader\dv365-music-downloader.exe"
set "launch_code=%errorlevel%"

:finish
popd
if not "%launch_code%"=="0" (
    echo.
    echo Application failed to start or exited with an error. Code: %launch_code%
    pause
)
exit /b %launch_code%
