@echo off
REM Receipt Reader - lanceur unique (Windows, sans .exe)
REM Une seule commande : la 1ere fois ca installe tout, ensuite ca lance direct.
REM   Double-clic sur run.bat   OU   run.bat dans un terminal
setlocal
cd /d "%~dp0"

REM --- Python installe ? ---
where python >nul 2>&1
if errorlevel 1 (
  echo [!] Python n'est pas installe.
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
where ollama >nul 2>&1
if errorlevel 1 (
  echo.
  echo [!] Ollama n'est pas installe. Telecharge-le puis relance run.bat :
  echo     https://ollama.com/download
  pause
  exit /b 1
)

REM --- 3. Modele present ? (Ollama Windows lance son serveur tout seul) ---
ollama list | findstr /C:"llama3.2" >nul 2>&1
if errorlevel 1 (
  echo [Setup] Telechargement du modele llama3.2 ^(~2 Go, une seule fois^)...
  ollama pull llama3.2
)

REM --- 4. Lancement ---
echo [Run] Lancement de receiptReader...
python app.py
