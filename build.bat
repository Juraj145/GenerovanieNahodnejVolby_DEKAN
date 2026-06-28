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
"%PYTHON%" -m pip install --quiet pyinstaller

echo Zostavujem .exe ...
"%PYTHON%" -m PyInstaller --noconfirm --onefile --windowed --name "VolbaPoradiaDekana" volba_poradia.py

echo.
echo Hotovo. Novy subor najdes v: dist\VolbaPoradiaDekana.exe
pause
endlocal
