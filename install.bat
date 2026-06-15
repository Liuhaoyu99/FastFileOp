@echo off
:: ============================================================
:: FastFileOp Installation Script
:: Uses bundled install.exe (PyInstaller) if available,
:: otherwise falls back to python -c
:: Requires Administrator privileges
:: ============================================================

setlocal enabledelayedexpansion

:: Check for Administrator privileges
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Requesting Administrator privileges...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

set "SCRIPT_DIR=%~dp0"

:: Use bundled install.exe if available
if exist "%SCRIPT_DIR%install.exe" (
    "%SCRIPT_DIR%install.exe"
    exit /b %errorlevel%
)

:: Fallback: use Python
set "INSTALL_DIR=%ProgramFiles%\FastFileOp"

echo ============================================================
echo FastFileOp Installation Script
echo ============================================================
echo.

set "SRC_EXE=%SCRIPT_DIR%dist\FastFileOp.exe"
set "SRC_DLL=%SCRIPT_DIR%dist\FastFileOpShim.dll"
if exist "%SCRIPT_DIR%FastFileOp.exe" set "SRC_EXE=%SCRIPT_DIR%FastFileOp.exe"
if exist "%SCRIPT_DIR%FastFileOpShim.dll" set "SRC_DLL=%SCRIPT_DIR%FastFileOpShim.dll"

echo Installing to: %INSTALL_DIR%
echo.

set "INSTALL_LOG=%TEMP%\fastfileop_install.log"
echo ===== FastFileOp install started: %DATE% %TIME% =====>> "%INSTALL_LOG%"
echo Installing to: %INSTALL_DIR% >> "%INSTALL_LOG%"

echo [Step 1/5] Checking source files...
if not exist "%SRC_EXE%" (
    echo ERROR: %SRC_EXE% not found!
    echo Please run build.bat first.
    echo ERROR: %SRC_EXE% not found! >> "%INSTALL_LOG%"
    pause & exit /b 1
)
if not exist "%SRC_DLL%" (
    echo WARNING: %SRC_DLL% not found, skipping shell extension.
    echo WARNING: %SRC_DLL% not found, skipping shell extension. >> "%INSTALL_LOG%"
    set "SKIP_DLL=1"
)
echo Source files OK. & echo.

echo [Step 2/5] Creating installation directory...
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
if %errorlevel% neq 0 ( echo ERROR: Failed to create installation directory! & pause & exit /b 1 )
echo Installation directory created. & echo.

echo [Step 3/5] Copying files...
copy /Y "%SRC_EXE%" "%INSTALL_DIR%\" >nul
if %errorlevel% neq 0 ( echo ERROR: Failed to copy FastFileOp.exe! & pause & exit /b 1 )

if not defined SKIP_DLL (
    copy /Y "%SRC_DLL%" "%INSTALL_DIR%\" >nul
    if %errorlevel% neq 0 ( echo ERROR: Failed to copy FastFileOpShim.dll! & pause & exit /b 1 )
    for %%f in (libgcc_s_dw2-1.dll libwinpthread-1.dll) do (
        if exist "%SCRIPT_DIR%dist\%%f" copy /Y "%SCRIPT_DIR%dist\%%f" "%INSTALL_DIR%\" >nul
        if exist "%SCRIPT_DIR%%%f" copy /Y "%SCRIPT_DIR%%%f" "%INSTALL_DIR%\" >nul
    )
)
echo Files copied successfully. & echo.

for %%f in (README.md README_zh.md LICENSE benchmark.png) do (
    if exist "%SCRIPT_DIR%%%f" copy /Y "%SCRIPT_DIR%%%f" "%INSTALL_DIR%\" >nul
)

echo [Step 4/5] Registering shell extension...
if defined SKIP_DLL ( echo Skipping shell extension registration. & goto :step5 )

set "DLL_DIR=%INSTALL_DIR%"
set "DLL_PATH=%DLL_DIR%\FastFileOpShim.dll"

python -c "import ctypes, os, sys; os.environ['PATH'] = r'%DLL_DIR%' + os.pathsep + os.environ['PATH']; dll = ctypes.WinDLL(r'%DLL_PATH%'); r = getattr(dll, 'DllRegisterServer@0')(); sys.exit(r)"
if %errorlevel% equ 0 (
    echo Shell extension registered.
    echo Shell extension registered. >> "%INSTALL_LOG%"
) else (
    echo WARNING: Failed to register shell extension. >> "%INSTALL_LOG%"
    echo WARNING: Failed to register shell extension.
    echo The application will still work, but drag-and-drop interception may not function.
)

:step5
echo [Step 5/5] Configuring auto-start and launching...
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" ^
    /v "FastFileOp" /t REG_SZ /d "\"%INSTALL_DIR%\FastFileOp.exe\" --silent" /f >nul
if %errorlevel% equ 0 ( echo Auto-start configured. ) else ( echo WARNING: Failed to configure auto-start. )

echo. & echo Starting FastFileOp...
start "" "%INSTALL_DIR%\FastFileOp.exe"
timeout /t 2 /nobreak >nul

echo. & echo ============================================================
echo Installation complete!
echo ============================================================
echo.
echo FastFileOp is now running in the system tray.
echo Location: %INSTALL_DIR%
echo.
pause
