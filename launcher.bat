@echo off
setlocal EnableExtensions

REM Pindah ke folder tempat launcher .bat berada
cd /d "%~dp0"

echo =====================================
echo    INITIALIZING VIRTUAL ENVIRONMENT
echo =====================================
echo.

REM Check if python is available
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python tidak ditemukan di sistem Anda!
    echo Silakan install Python terlebih dahulu dan pastikan masuk ke PATH.
    pause
    exit /b 1
)

REM Setup virtual environment if not exists
if not exist "venv" (
    echo [INFO] Virtual environment venv tidak ditemukan.
    echo Membuat virtual environment baru di folder "venv"...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Gagal membuat virtual environment!
        pause
        exit /b 1
    )
    
    echo [INFO] Mengaktifkan venv dan memasang dependensi dari requirements.txt...
    call "venv\Scripts\activate.bat"
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [WARNING] Ada beberapa dependensi yang gagal dipasang!
        echo Silakan periksa pesan error di atas.
        pause
    ) else (
        echo [SUCCESS] Virtual environment berhasil dibuat dan semua dependensi terpasang!
        echo.
        pause
    )
) else (
    echo [INFO] Mengaktifkan virtual environment venv...
    call "venv\Scripts\activate.bat"
)

:menu
cls
echo =====================================
echo        MANGA TOOL LAUNCHER
echo =====================================
echo.
echo [1] Jalankan main.py saja
echo [2] Jalankan Inpainting saja
echo [3] Jalankan KEDUANYA (Inpainting + main.py)
echo [4] Keluar
echo.
set "choice="
set /p choice=Pilih menu [1-4]: 

if "%choice%"=="1" goto run_main
if "%choice%"=="2" goto run_inpainting
if "%choice%"=="3" goto run_both
if "%choice%"=="4" goto exit_app

echo.
echo Pilihan tidak valid!
pause
goto menu

REM ================================
REM Jalankan main.py
REM ================================
:run_main
cls
echo ================================
echo Menjalankan main.py ...
echo ================================
echo.

python main.py
set "EXITCODE=%ERRORLEVEL%"
goto after_run

REM ================================
REM Jalankan Inpainting (venv sendiri)
REM ================================
:run_inpainting
call :start_inpainting_window
set "EXITCODE=%ERRORLEVEL%"
goto after_run

REM ================================
REM Jalankan KEDUANYA
REM ================================
:run_both
cls
echo ================================
echo Menjalankan Inpainting + main.py ...
echo ================================
echo.

REM 1) Start inpainting di window baru (tidak ngeblok)
call :start_inpainting_window

REM 2) Kasih jeda dikit biar server sempat naik (ubah kalau perlu)
echo.
echo Menunggu 3 detik...
timeout /t 3 /nobreak >nul

REM 3) Lanjut jalankan main.py di window ini
echo.
echo ================================
echo Menjalankan main.py ...
echo ================================
echo.

python main.py
set "EXITCODE=%ERRORLEVEL%"
goto after_run

REM ================================
REM Helper: start inpainting pada window baru
REM ================================
:start_inpainting_window
set "INPAINT_PATH=E:\Gabut\Manga\Project\Inpainting"
set "INPAINT_VENV=%INPAINT_PATH%\venv\Scripts\activate.bat"
set "INPAINT_BAT=%INPAINT_PATH%\run.bat"

if not exist "%INPAINT_PATH%" (
    echo [ERROR] Folder Inpainting tidak ditemukan:
    echo %INPAINT_PATH%
    pause
    goto :eof
)

if not exist "%INPAINT_VENV%" (
    echo [ERROR] venv Inpainting tidak ditemukan:
    echo %INPAINT_VENV%
    pause
    goto :eof
)

if not exist "%INPAINT_BAT%" (
    echo [ERROR] File BAT Inpainting tidak ditemukan:
    echo %INPAINT_BAT%
    echo.
    echo Ubah baris INPAINT_BAT sesuai nama file .bat inpainting kamu.
    pause
    goto :eof
)

echo Membuka Inpainting di window baru...
REM /k supaya window inpainting tetap hidup (server tetap jalan)
start "Inpainting Server" cmd /k ^
"cd /d ""%INPAINT_PATH%"" ^& call ""%INPAINT_VENV%"" ^& call ""%INPAINT_BAT%"""

goto :eof

REM ================================
REM Setelah program selesai
REM ================================
:after_run
echo.
echo ================================
echo Program berhenti dengan code %EXITCODE%
echo ================================
echo.
echo Ketik R lalu ENTER untuk balik ke menu.
echo Tekan ENTER saja untuk balik ke menu.
set "choice="
set /p choice=Perintah: 

goto menu

REM ================================
REM Keluar
REM ================================
:exit_app
echo.
echo Keluar...
pause
endlocal
exit /b 0
