@echo off
:: FastFileOpShim Installation Script
:: Requires Administrator privileges

echo ========================================
echo FastFileOpShim Shell Extension Installer
echo ========================================
echo.

:: Check for Administrator privileges
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Please run this script as Administrator!
    echo Right-click this file and select "Run as administrator"
    pause
    exit /b 1
)

:: Get current directory
set "DLL_PATH=%~dp0FastFileOpShim.dll"

:: Check if DLL exists
if not exist "%DLL_PATH%" (
    echo ERROR: FastFileOpShim.dll not found!
    echo Please ensure the DLL file is in the same directory as this script.
    pause
    exit /b 1
)

echo Registering FastFileOpShim.dll...
echo.

:: Register DLL using regsvr32
regsvr32 /s "%DLL_PATH%"

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo Installation successful!
    echo ========================================
    echo.
    echo Registered Shell extensions:
    echo   - CopyHook (Folder copy/move interception)
    echo   - ContextMenu (Right-click paste menu)
    echo   - DropTarget (Drag and drop operations)
    echo   - DeleteCommand (Right-click delete menu)
    echo.
    echo NOTE: You may need to restart Explorer or log off for changes to take effect.
    echo.
) else (
    echo.
    echo ERROR: Registration failed!
    echo Please verify that the DLL is a 64-bit build.
    echo.
)

pause
