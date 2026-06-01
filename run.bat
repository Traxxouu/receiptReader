@echo off
REM Receipt Reader - lanceur unique (Windows, sans .exe)
setlocal enabledelayedexpansion
cd /d "%~dp0"

REM --- Setup des couleurs ANSI ---
for /f %%a in ('echo prompt $E^| cmd') do set "ESC=%%a"
set "GREEN=%ESC%[92m"
set "PINK=%ESC%[95m"
set "CYAN=%ESC%[96m"
set "RED=%ESC%[91m"
set "BOLD=%ESC%[1m"
set "RESET=%ESC%[0m"

REM --- Python installe ? ---
where python >nul 2>&1
if errorlevel 1 (
  echo %RED%[!] Python n'est pas installe.%RESET%
  echo     Telecharge-le sur https://www.python.org/downloads/
  echo     IMPORTANT : coche "Add Python to PATH" pendant l'installation.
  pause
  exit /b 1
)

REM --- 1. venv + dependances (premiere fois seulement) ---
if not exist "venv" (
  echo [Setup] Premier lancement : creation de l'environnement Python...
  python -m venv venv
  call venv\Scripts\activate.bat
  python -m pip install --upgrade pip
  echo [Setup] Installation des dependances ^(quelques minutes^)...
  python -m pip install -r requirements.txt
) else (
  call venv\Scripts\activate.bat
)

REM --- 2. Ollama installe ? ---
set "OLLAMA_OK=0"
where ollama >nul 2>&1
if not errorlevel 1 set "OLLAMA_OK=1"

REM --- 3. Modele present ? ---
set "MODEL_OK=0"
if "%OLLAMA_OK%"=="1" (
  ollama list | findstr /C:"llama3.2" >nul 2>&1
  if not errorlevel 1 set "MODEL_OK=1"
  if "!MODEL_OK!"=="0" (
    echo [Setup] Telechargement du modele llama3.2 ^(~2 Go, une seule fois^)...
    ollama pull llama3.2
    ollama list | findstr /C:"llama3.2" >nul 2>&1
    if not errorlevel 1 set "MODEL_OK=1"
  )
)

REM --- 4. Ecran final ---
cls
echo.
echo %GREEN%%BOLD%  ============================================%RESET%
echo %GREEN%%BOLD%            INSTALLATION TERMINEE%RESET%
echo %GREEN%%BOLD%  ============================================%RESET%
echo.

if "%OLLAMA_OK%"=="1" (
  echo %PINK%   [OK] Ollama est installe sur ta machine.%RESET%
) else (
  echo %RED%   [X] Ollama n'est PAS installe : https://ollama.com/download%RESET%
)
if "%MODEL_OK%"=="1" (
  echo %PINK%   [OK] Le modele llama3.2 est present.%RESET%
) else (
  echo %RED%   [X] Le modele llama3.2 est absent : ollama pull llama3.2%RESET%
)
echo %PINK%   -^> Verifie qu'Ollama tourne en arriere-plan%RESET%
echo %PINK%      (icone dans la barre des taches).%RESET%
echo.
echo %CYAN%%BOLD%   Pour lancer l'application, tape :%RESET%
echo.
echo %CYAN%%BOLD%        python app.py%RESET%
echo.
echo   (puis Entree)
echo.

REM --- 5. On laisse un terminal pret : bon dossier + venv deja active ---
cmd /k