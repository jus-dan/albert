@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ============================================
echo   Albert auf Produktionsmodus umstellen
echo ============================================
echo.
echo Das braucht es nur einmal, wenn eine Kopie dieses Ordners (samt
echo .git-Ordner) auf eine neue Maschine gezogen wurde und dort noch ein
echo Entwicklungs-Branch aktiv ist. Danach startet "Albert-starten.bat"
echo wieder ganz normal: Versionsauswahl beim Start, automatisches
echo Update auf die jeweils neueste veroeffentlichte Version.
echo.

if not exist ".git" (
    echo Kein Git-Repo an diesem Ort gefunden -- hier gibt es nichts umzustellen.
    echo.
    pause
    exit /b 1
)

where git >nul 2>nul
if errorlevel 1 (
    echo Git wurde auf diesem Rechner nicht gefunden. Bitte zuerst Git
    echo installieren ^(oder einmal "Albert-starten.bat" ausfuehren, das
    echo installiert Git bei Bedarf automatisch^).
    echo.
    pause
    exit /b 1
)

for /f "delims=" %%b in ('git rev-parse --abbrev-ref HEAD 2^>nul') do set "GIT_BRANCH=%%b"
if "!GIT_BRANCH!"=="main" (
    echo Laeuft bereits auf 'main' -- nichts zu tun.
    echo.
    pause
    exit /b 0
)

echo Aktueller Branch: !GIT_BRANCH!
echo.
echo Verwerfe lokale Aenderungen an diesem Ort und wechsle auf 'main' ...
git checkout -- . >nul 2>nul
git checkout main
if errorlevel 1 (
    echo.
    echo FEHLER beim Wechsel auf 'main' ^(siehe Meldung oben^).
    echo.
    pause
    exit /b 1
)

echo.
echo Fertig! Dieser Rechner laeuft jetzt im Produktionsmodus. Naechster
echo Schritt: "Albert-starten.bat" ausfuehren.
echo.
pause
