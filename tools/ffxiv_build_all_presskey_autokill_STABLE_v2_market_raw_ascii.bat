@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

REM ==========================================================
REM CHERANGBOT FFXIV DATA PIPELINE : ONE-CLICK BUILD (ASCII SAFE)
REM - Auto-kill SaintCoinach after target CSVs appear
REM - Exports market raw CSVs to data\ffxiv\market\raw
REM - ASCII only to avoid cmd UTF-8 parsing issues
REM ==========================================================

set "ROOT=%~dp0.."

set "GAME=G:\FINAL FANTASY XIV - KOREA"
set "SC_EXE=%ROOT%\tools\sc\SaintCoinach.Cmd.exe"
set "PY=py -3"

set "DATAJS_URL=https://raw.githubusercontent.com/icykoneko/ff14-fish-tracker-app/master/js/app/data.js"
set "XIVAPI_EN_BASE=https://raw.githubusercontent.com/xivapi/ffxiv-datamining/master/csv/en"
set "XIVAPI_EN_ITEM=%XIVAPI_EN_BASE%/Item.csv"

set "FISH_RAW=%ROOT%\data\ffxiv\fish\raw"
set "FISH_CSV=%FISH_RAW%\csv"
set "FISH_KO=%FISH_CSV%\ko"
set "FISH_EN=%FISH_CSV%\en"

set "WEATHER_RAW=%ROOT%\data\ffxiv\weather\raw"
set "WEATHER_KO=%WEATHER_RAW%\ko"
set "WEATHER_EN=%WEATHER_RAW%\en"

set "MARKET_RAW=%ROOT%\data\ffxiv\market\raw"

if not exist "%FISH_RAW%" mkdir "%FISH_RAW%"
if not exist "%FISH_CSV%" mkdir "%FISH_CSV%"
if not exist "%FISH_KO%" mkdir "%FISH_KO%"
if not exist "%FISH_EN%" mkdir "%FISH_EN%"
if not exist "%WEATHER_RAW%" mkdir "%WEATHER_RAW%"
if not exist "%WEATHER_KO%" mkdir "%WEATHER_KO%"
if not exist "%WEATHER_EN%" mkdir "%WEATHER_EN%"

if not exist "%SC_EXE%" (
  echo ERROR: SaintCoinach.Cmd.exe not found: %SC_EXE%
  pause
  exit /b 10
)
if not exist "%GAME%" (
  echo ERROR: Game path not found: %GAME%
  pause
  exit /b 11
)

set "SC_HELPER=%~dp0sc_waitkill_v2.ps1"
if not exist "%SC_HELPER%" (
  echo ERROR: Missing helper: %SC_HELPER%
  echo Put sc_waitkill_v2.ps1 next to this bat file.
  pause
  exit /b 12
)

echo.
echo ==========================================================
echo RUN  %date% %time%
echo ROOT = %ROOT%
echo GAME = %GAME%
echo SC   = %SC_EXE%
echo ==========================================================
echo.

set "PSDL=powershell -NoProfile -ExecutionPolicy Bypass -Command"
goto :START

:DL
set "URL=%~1"
set "OUT=%~2"
echo [DL] %URL%
%PSDL% ^
  "$u='%URL%'; $o='%OUT%';" ^
  "for($i=1;$i -le 4;$i++){" ^
  "  try { Invoke-WebRequest -Uri $u -OutFile $o -UseBasicParsing; exit 0 }" ^
  "  catch { Start-Sleep -Seconds 1 }" ^
  "}; exit 2"
if errorlevel 1 (
  echo ERROR: Download failed: %URL%
  exit /b 2
)
exit /b 0

:START
echo =======================
echo [1] FISH raw: data.js + EN Item.csv
echo =======================

call :DL "%DATAJS_URL%" "%FISH_RAW%\data.js"
if errorlevel 1 (
  echo ERROR: data.js download failed
  pause
  exit /b 21
)

call :DL "%XIVAPI_EN_ITEM%" "%FISH_EN%\Item.csv"
if errorlevel 1 (
  echo ERROR: EN Item.csv download failed
  pause
  exit /b 22
)

echo OK: fish raw downloads done
echo.

echo =======================
echo [2] FISH raw: SaintCoinach KO export
echo =======================

set "SCLOG=%ROOT%\tools\sc\_sc_fish_ko.log"
start "" /b cmd /c ""%SC_EXE%" "%GAME%" --no-update --lang ko --out "%FISH_KO%" --exd FishingSpot FishParameter Item PlaceName TerritoryType > "%SCLOG%" 2>&1"

set /a WAIT=0
:WAIT_FISH
set "OK=1"
for %%F in (FishingSpot.csv FishParameter.csv Item.csv PlaceName.csv TerritoryType.csv) do (
  if not exist "%FISH_KO%\%%F" set "OK=0"
)
if "%OK%"=="1" goto FISH_DONE
timeout /t 1 /nobreak >nul
set /a WAIT+=1
if %WAIT% GEQ 600 goto FISH_TIMEOUT
goto WAIT_FISH

:FISH_DONE
taskkill /im SaintCoinach.Cmd.exe /f >nul 2>&1
echo OK: fish ko csv done
echo.
goto AFTER_FISH

:FISH_TIMEOUT
echo ERROR: Fish KO export timeout. log: %SCLOG%
type "%SCLOG%"
pause
exit /b 23

:AFTER_FISH
echo =======================
echo [3] WEATHER raw: EN downloads
echo =======================

call :DL "%XIVAPI_EN_BASE%/Weather.csv" "%WEATHER_EN%\Weather.csv"
if errorlevel 1 (
  pause
  exit /b 31
)
call :DL "%XIVAPI_EN_BASE%/WeatherRate.csv" "%WEATHER_EN%\WeatherRate.csv"
if errorlevel 1 (
  pause
  exit /b 32
)
call :DL "%XIVAPI_EN_BASE%/TerritoryType.csv" "%WEATHER_EN%\TerritoryType.csv"
if errorlevel 1 (
  pause
  exit /b 33
)
call :DL "%XIVAPI_EN_BASE%/PlaceName.csv" "%WEATHER_EN%\PlaceName.csv"
if errorlevel 1 (
  pause
  exit /b 34
)

echo OK: weather en downloads done
echo.

echo =======================
echo [4] WEATHER raw: SaintCoinach KO export
echo =======================

set "SCLOG=%ROOT%\tools\sc\_sc_weather_ko.log"
start "" /b cmd /c ""%SC_EXE%" "%GAME%" --no-update --lang ko --out "%WEATHER_KO%" --exd Weather WeatherRate TerritoryType PlaceName > "%SCLOG%" 2>&1"

set /a WAIT=0
:WAIT_WEATHER
set "OK=1"
for %%F in (Weather.csv WeatherRate.csv TerritoryType.csv PlaceName.csv) do (
  if not exist "%WEATHER_KO%\%%F" set "OK=0"
)
if "%OK%"=="1" goto WEATHER_DONE
timeout /t 1 /nobreak >nul
set /a WAIT+=1
if %WAIT% GEQ 600 goto WEATHER_TIMEOUT
goto WAIT_WEATHER

:WEATHER_DONE
taskkill /im SaintCoinach.Cmd.exe /f >nul 2>&1
echo OK: weather ko csv done
echo.
goto AFTER_WEATHER

:WEATHER_TIMEOUT
echo ERROR: Weather KO export timeout. log: %SCLOG%
type "%SCLOG%"
pause
exit /b 43

:AFTER_WEATHER
echo =======================
echo [5] BUILD compiled DBs
echo =======================

call :RUNPY "%ROOT%\data\ffxiv\weather\tools" "build_weather_types.py"
if errorlevel 1 goto :PYFAIL
call :RUNPY "%ROOT%\data\ffxiv\fish\tools" "build_fish_db.py"
if errorlevel 1 goto :PYFAIL
call :RUNPY "%ROOT%\data\ffxiv\market\tools" "build_items_index.py"
if errorlevel 1 goto :PYFAIL

echo.
echo ALL DONE
echo weather: %ROOT%\data\ffxiv\weather\compiled\
echo fish:    %ROOT%\data\ffxiv\fish\compiled\
echo market:  %ROOT%\data\ffxiv\market\compiled\
echo.
pause
exit /b 0

:PYFAIL
echo ERROR: python build step failed.
pause
exit /b 50

:RUNPY
set "WD=%~1"
set "SCRIPT=%~2"
pushd "%WD%" >nul
echo --- running: %WD%\%SCRIPT%
%PY% "%SCRIPT%" <nul
set "EC=%ERRORLEVEL%"
popd >nul
if not "%EC%"=="0" exit /b %EC%
exit /b 0
