@echo off
:: ============================================================
:: FastFileOp Installation Script
:: Installs FastFileOp to Program Files and registers shell extension
:: Requires Administrator privileges
:: ============================================================

setlocal enabledelayedexpansion

echo ============================================================
echo FastFileOp Installation Script
echo ============================================================
echo.

:: Check for Administrator privileges
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Requesting Administrator privileges...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

:: Get script directory
set "SCRIPT_DIR=%~dp0"
set "INSTALL_DIR=%ProgramFiles%\FastFileOp"

echo Installing to: %INSTALL_DIR%
echo.

:: ============================================================
:: Step 1: Check source files
:: ============================================================
echo [Step 1/5] Checking source files...

if not exist "%SCRIPT_DIR%dist\FastFileOp.exe" (
    echo ERROR: dist\FastFileOp.exe not found!
    echo Please run build.bat first.
    pause
    exit /b 1
)

if not exist "%SCRIPT_DIR%dist\FastFileOpShim.dll" (
    echo WARNING: dist\FastFileOpShim.dll not found, skipping shell extension.
    set "SKIP_DLL=1"
)

echo Source files OK.
echo.

:: ============================================================
:: Step 2: Create installation directory
:: ============================================================
echo [Step 2/5] Creating installation directory...

if not exist "%INSTALL_DIR%" (
    mkdir "%INSTALL_DIR%"
    if %errorlevel% neq 0 (
        echo ERROR: Failed to create installation directory!
        pause
        exit /b 1
    )
)

echo Installation directory created.
echo.

:: ============================================================
:: Step 3: Copy files
:: ============================================================
echo [Step 3/5] Copying files...

copy /Y "%SCRIPT_DIR%dist\FastFileOp.exe" "%INSTALL_DIR%\" >nul
if %errorlevel% neq 0 (
    echo ERROR: Failed to copy FastFileOp.exe!
    pause
    exit /b 1
)

if not defined SKIP_DLL (
    copy /Y "%SCRIPT_DIR%dist\FastFileOpShim.dll" "%INSTALL_DIR%\" >nul
    if %errorlevel% neq 0 (
        echo ERROR: Failed to copy FastFileOpShim.dll!
        pause
        exit /b 1
    )
)

echo Files copied successfully.
echo.

:: ============================================================
:: Step 4: Register shell extension
:: ============================================================
echo [Step 4/5] Registering shell extension...

if not defined SKIP_DLL (
    regsvr32 /s "%INSTALL_DIR%\FastFileOpShim.dll"
    if %errorlevel% neq 0 (
        echo WARNING: Failed to register shell extension.
        echo The application will still work, but drag-and-drop interception may not function.
    ) else (
        echo Shell extension registered.
    )
) else (
    echo Skipping shell extension registration.
)

:: ============================================================
:: Step 5: Register auto-start and launch
:: ============================================================
echo [Step 5/5] Configuring auto-start and launching...

:: Register auto-start
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" ^
    /v "FastFileOp" /t REG_SZ /d "\"%INSTALL_DIR%\FastFileOp.exe\" --silent" /f >nul

if %errorlevel% equ 0 (
    echo Auto-start configured.
) else (
    echo WARNING: Failed to configure auto-start.
)

:: Launch application
echo.
echo Starting FastFileOp...
start "" "%INSTALL_DIR%\FastFileOp.exe"

:: Wait a moment for the app to start
timeout /t 2 /nobreak >nul

echo.
echo ============================================================
echo Installation complete!
echo ============================================================
echo.
echo FastFileOp is now running in the system tray.
echo.
echo Location: %INSTALL_DIR%
echo.
echo To uninstall, run uninstall.bat as Administrator.
echo.

pause
