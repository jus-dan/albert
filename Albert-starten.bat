@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ============================================
echo   Albert wird vorbereitet ...
echo ============================================
echo.

rem --- Neueste Version von GitHub holen, falls dies ein Git-Repo ist ---
if exist ".git" (
    where git >nul 2>nul
    if errorlevel 1 (
        echo Git wurde nicht gefunden -- installiere es automatisch ueber winget ...
        where winget >nul 2>nul
        if not errorlevel 1 (
            winget install --id Git.Git -e --silent --accept-source-agreements --accept-package-agreements >nul 2>nul
            echo Git wurde installiert. Die automatische Aktualisierung ist erst ab
            echo dem naechsten Start verfuegbar ^(neuer PATH wird erst dann uebernommen^).
        )
        echo.
    ) else (
        echo Hole neueste Version von GitHub ...
        git pull --ff-only 2>nul
        if errorlevel 1 (
            echo Konnte nicht automatisch aktualisieren ^(z.B. keine Internetverbindung
            echo oder lokale Aenderungen^) -- verwende den vorhandenen Stand.
        )
        echo.
    )
)

rem --- Aktuelle Version anzeigen ---
set "ALBERT_VERSION="
where git >nul 2>nul
if not errorlevel 1 (
    for /f "delims=" %%v in ('git describe --tags 2^>nul') do set "ALBERT_VERSION=%%v"
)
if "!ALBERT_VERSION!"=="" set "ALBERT_VERSION=unbekannt"
echo Version: !ALBERT_VERSION!
echo.

rem --- Python suchen ---
set "PYTHON_CMD="
where python >nul 2>nul
if not errorlevel 1 set "PYTHON_CMD=python"

if "%PYTHON_CMD%"=="" (
    where py >nul 2>nul
    if not errorlevel 1 set "PYTHON_CMD=py -3"
)

if "%PYTHON_CMD%"=="" (
    echo Python wurde nicht gefunden -- versuche automatische Installation ueber winget ...
    echo.
    where winget >nul 2>nul
    if errorlevel 1 (
        echo winget ist auf diesem Rechner nicht verfuegbar.
        echo Bitte installiere Python 3.11 oder neuer manuell von https://www.python.org/downloads/
        echo ^(beim Installieren "Add python.exe to PATH" ankreuzen^) und starte diese Datei danach erneut.
        echo.
        pause
        exit /b 1
    )

    winget install --id Python.Python.3.13 -e --silent --accept-source-agreements --accept-package-agreements
    if errorlevel 1 (
        echo.
        echo Automatische Installation ist fehlgeschlagen.
        echo Bitte installiere Python 3.11 oder neuer manuell von https://www.python.org/downloads/
        echo ^(beim Installieren "Add python.exe to PATH" ankreuzen^) und starte diese Datei danach erneut.
        echo.
        pause
        exit /b 1
    )

    echo.
    echo Python wurde installiert. Bitte starte diese Datei jetzt noch einmal,
    echo damit Windows den neuen PATH-Eintrag uebernimmt.
    echo.
    pause
    exit /b 0
)

rem --- Virtuelle Umgebung anlegen, falls noch nicht vorhanden ---
if not exist ".venv\Scripts\python.exe" (
    echo Erstelle virtuelle Umgebung ...
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 (
        echo Konnte keine virtuelle Umgebung erstellen.
        pause
        exit /b 1
    )
)

rem --- Abhaengigkeiten installieren/aktualisieren ---
echo Installiere/aktualisiere benoetigte Pakete ...
".venv\Scripts\python.exe" -m pip install --quiet --upgrade pip
".venv\Scripts\python.exe" -m pip install --quiet -r requirements.txt
if errorlevel 1 (
    echo.
    echo Fehler beim Installieren der Pakete. Bitte Internetverbindung pruefen.
    pause
    exit /b 1
)

rem --- .env pruefen ---
if not exist ".env" (
    echo.
    echo Keine .env-Datei gefunden -- lege sie aus der Vorlage an ...
    copy ".env.example" ".env" >nul
    echo.
    echo ============================================
    echo   WICHTIG: Bitte trage deine Zugangsdaten ein
    echo ============================================
    echo In der sich gleich oeffnenden Datei .env musst du eintragen:
    echo   - OPENAI_API_KEY
    echo   - AIRTABLE_API_TOKEN
    echo   - AIRTABLE_BASE_ID
    echo.
    echo Datei speichern, dann diese Datei hier noch einmal starten.
    echo.
    notepad ".env"
    pause
    exit /b 0
)

rem --- Server starten ---
echo.
echo Starte Albert ...
start "Albert Server" ".venv\Scripts\python.exe" server.py

timeout /t 3 /nobreak >nul

rem --- Browser oeffnen (normales Fenster) ---
start "" "http://127.0.0.1:8000"

echo.
echo Albert laeuft jetzt im Fenster "Albert Server".
echo Dieses Fenster kann geschlossen werden -- der Server laeuft weiter,
echo bis du das Fenster "Albert Server" schliesst.
echo.
timeout /t 5 >nul
exit /b 0
