@echo off
REM ====================================================================
REM  Zostavenie spustitelneho suboru VolbaPoradiaDekana.exe
REM  Spusti tento subor dvojklikom alebo prikazom: build.bat
REM ====================================================================

setlocal

REM Najdi Python (uprav cestu ak je u teba inde)
set PYTHON=python
where %PYTHON% >nul 2>&1 || set PYTHON=C:\Python312\python.exe

echo Pouzivam Python: %PYTHON%
echo Instalujem PyInstaller (ak chyba)...
"%PYTHON%" -m pip install --quiet pyinstaller certifi

echo Zostavujem .exe ...
"%PYTHON%" -m PyInstaller --noconfirm --onefile --windowed --icon app.ico --add-data "app.ico;." --name "VolbaPoradiaDekana" volba_poradia.py

echo.
echo Hotovo. Novy subor najdes v: dist\VolbaPoradiaDekana.exe
echo.
echo (Volitelne) Pre zostavenie instalatora nainstaluj Inno Setup a spusti:
echo   "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
pause
endlocal
