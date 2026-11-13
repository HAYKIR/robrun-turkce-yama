@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (
    where python >nul 2>nul && set "PY=python"
)
if not defined PY (
    echo [HATA] Python bulunamadi.
    echo https://www.python.org/downloads/ adresinden Python 3 kurun.
    echo Kurulumda "Add python.exe to PATH" kutusunu isaretleyin.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Ilk kurulum: sanal ortam olusturuluyor...
    %PY% -m venv .venv || (echo [HATA] Sanal ortam olusturulamadi. & pause & exit /b 1)
)

".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements.txt
if errorlevel 1 (
    echo [HATA] Gerekli kutuphaneler kurulamadi. Internet baglantinizi kontrol edin.
    pause
    exit /b 1
)

set PYTHONIOENCODING=utf-8
".venv\Scripts\python.exe" robrun_tr.py %*
if errorlevel 1 pause
endlocal
