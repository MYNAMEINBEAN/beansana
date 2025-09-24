@echo off
setlocal EnableDelayedExpansion

:: Fully Autonomous FreeDNS Domain Maker Setup Script
:: This script handles everything automatically

title FreeDNS Domain Maker - Autonomous Setup
color 0a

set "PYTHON_EXE=C:\Users\Public.PI_1\AppData\Local\Programs\Python\Python313\python.exe"
set "PIP_EXE=C:\Users\Public.PI_1\AppData\Local\Programs\Python\Python313\Scripts\pip3.13.exe"

echo.
echo ============================================================
echo             FREEDNS DOMAIN MAKER - AUTONOMOUS SETUP
echo ============================================================
echo.
echo This script will automatically set up everything for you:
echo  ✓ Check and install Python dependencies
echo  ✓ Setup Tor service from local files
echo  ✓ Configure everything automatically
echo  ✓ Clean up and prepare for use
echo.
echo Starting autonomous setup in 3 seconds...
timeout /t 3 /nobreak >nul

:: Get the directory where this batch file is located
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

:: Check if Python is accessible
echo.
echo [1/6] Checking Python path...
"%PYTHON_EXE%" --version >nul 2>&1
if errorlevel 1 (
    echo ❌ ERROR: Python executable not found at:
    echo    %PYTHON_EXE%
    echo.
    echo Please ensure Python is installed at the specified path.
    pause
    exit /b 1
)
"%PYTHON_EXE%" --version
echo ✅ Python found

:: Install Python dependencies
echo.
echo [2/6] Installing Python dependencies...

echo Installing stem...
"%PYTHON_EXE%" -m pip install stem --quiet --disable-pip-version-check

echo Installing pysocks...
"%PYTHON_EXE%" -m pip install pysocks --quiet --disable-pip-version-check

echo Installing requests...
"%PYTHON_EXE%" -m pip install requests --quiet --disable-pip-version-check

echo Installing Pillow...
"%PYTHON_EXE%" -m pip install Pillow --quiet --disable-pip-version-check

echo Installing freedns...
"%PYTHON_EXE%" -m pip install freedns-client --quiet --disable-pip-version-check

echo Installing art...
"%PYTHON_EXE%" -m pip install art --quiet --disable-pip-version-check

echo Installing pytesseract...
"%PYTHON_EXE%" -m pip install pytesseract --quiet --disable-pip-version-check

echo Installing lolpython...
"%PYTHON_EXE%" -m pip install lolpython --quiet --disable-pip-version-check

echo ✅ Python dependencies installation completed

:: Check for local tor folder
echo.
echo [3/6] Checking for Tor files...
if not exist "%SCRIPT_DIR%\tor" (
    echo ❌ ERROR: Tor folder not found!
    pause
    exit /b 1
)

if not exist "%SCRIPT_DIR%\tor\tor.exe" (
    echo ❌ ERROR: tor.exe not found in tor folder!
    pause
    exit /b 1
)

echo ✅ Found Tor folder with tor.exe

:: Setup Tor folder in working directory (no C:\ usage)
echo.
echo [4/6] Setting up Tor locally...

set "LOCAL_TOR=%SCRIPT_DIR%\tor_runtime"

echo Cleaning existing tor_runtime directory...
if exist "%LOCAL_TOR%" (
    rmdir /s /q "%LOCAL_TOR%" >nul 2>&1
)

mkdir "%LOCAL_TOR%\data" >nul 2>&1
mkdir "%LOCAL_TOR%\logs" >nul 2>&1

xcopy "%SCRIPT_DIR%\tor\*" "%LOCAL_TOR%\" /E /I /Q /Y >nul 2>&1

echo ✅ Tor files copied to tor_runtime

:: Create torrc config
echo.
echo [5/6] Creating torrc configuration...
(
echo SocksPort 9050
echo ControlPort 9051
echo CookieAuthentication 1
echo DataDirectory "%LOCAL_TOR%\data"
echo Log notice file "%LOCAL_TOR%\logs\tor.log"
echo ExitRelay 0
echo ClientOnly 1
) > "%LOCAL_TOR%\torrc"

echo ✅ Tor configuration created

:: Create helper scripts
echo.
echo [6/6] Creating helper scripts...

(
echo @echo off
echo title Start Tor - Local
echo cd /d "%LOCAL_TOR%"
echo "%LOCAL_TOR%\tor.exe" -f torrc
echo pause
) > "%SCRIPT_DIR%\start_tor.bat"

(
echo @echo off
echo "%PYTHON_EXE%" -c "import requests; proxies={'http':'socks5h://127.0.0.1:9050','https':'socks5h://127.0.0.1:9050'}; r1=requests.get('https://httpbin.org/ip', timeout=10); r2=requests.get('https://httpbin.org/ip', proxies=proxies, timeout=20); print(f'Direct IP: {r1.json()[\"origin\"]}'); print(f'Tor IP: {r2.json()[\"origin\"]}'); print('SUCCESS: Tor is working!' if r1.json()['origin'] != r2.json()['origin'] else 'ERROR: Tor not working')"
echo pause
) > "%SCRIPT_DIR%\test_tor.bat"

echo ✅ Helper scripts created

:: Done
echo.
echo ============================================================
echo                    🎉 SETUP COMPLETED! 🎉
echo ============================================================
echo.
echo ✅ Python dependencies installed
echo ✅ Tor configured in local folder
echo ✅ start_tor.bat and test_tor.bat created
echo.
echo 📋 NEXT STEPS:
echo.
echo 1. Start Tor with:
echo    start_tor.bat
echo.
echo 2. Then run your script using:
echo    "%PYTHON_EXE%" __main__.py
echo.
echo 3. Optional: Run test_tor.bat to verify anonymity
echo.
pause
exit /b
