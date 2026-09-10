@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python 3.11 launcher가 필요합니다.
  exit /b 1
)

if not exist .venv py -3.11 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

pyinstaller --noconfirm --clean --onedir ^
  --name RevisionLens ^
  --add-data "app.py;." ^
  --add-data ".streamlit;.streamlit" ^
  --collect-all streamlit ^
  --collect-all altair ^
  --collect-all pypdfium2 ^
  --hidden-import approval_app.core ^
  --hidden-import approval_app.exporters ^
  run_app.py

if errorlevel 1 exit /b 1
echo.
echo 완료: dist\RevisionLens\RevisionLens.exe
endlocal

