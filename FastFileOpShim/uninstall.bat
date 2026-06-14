@echo off
:: FastFileOpShim Uninstallation Script
:: Requires Administrator privileges

echo ========================================
echo FastFileOpShim Shell Extension Uninstaller
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
    echo WARNING: FastFileOpShim.dll not found, attempting to unregister from registry...
)

echo Unregistering FastFileOpShim.dll...
echo.

:: Unregister DLL using regsvr32
regsvr32 /s /u "%DLL_PATH%" 2>nul

:: Manual registry cleanup (in case regsvr32 fails)
echo Cleaning registry entries...
reg delete "HKCR\Directory\ShellEx\CopyHookHandlers\FastFileOp" /f 2>nul
reg delete "HKCR\Folder\ShellEx\CopyHookHandlers\FastFileOp" /f 2>nul
reg delete "HKCR\*\ShellEx\ContextMenuHandlers\FastFileOp" /f 2>nul
reg delete "HKCR\Directory\ShellEx\ContextMenuHandlers\FastFileOp" /f 2>nul
reg delete "HKCR\Folder\ShellEx\ContextMenuHandlers\FastFileOp" /f 2>nul
reg delete "HKCR\Directory\ShellEx\DragDropHandlers\FastFileOp" /f 2>nul
reg delete "HKCR\Folder\ShellEx\DragDropHandlers\FastFileOp" /f 2>nul
reg delete "HKCR\*\ShellEx\ContextMenuHandlers\FastFileOpDelete" /f 2>nul
reg delete "HKCR\Directory\ShellEx\ContextMenuHandlers\FastFileOpDelete" /f 2>nul
reg delete "HKCR\CLSID\{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}" /f 2>nul
reg delete "HKCR\CLSID\{B2C3D4E5-F6A7-8901-BCDE-F12345678901}" /f 2>nul
reg delete "HKCR\CLSID\{C3D4E5F6-A7B8-9012-CDEF-123456789012}" /f 2>nul
reg delete "HKCR\CLSID\{D4E5F6A7-B8C9-0123-DEF0-234567890123}" /f 2>nul

:: Remove auto-start registry key
echo Removing auto-start entry...
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "FastFileOp" /f 2>nul

echo.
echo ========================================
echo Uninstallation complete!
echo ========================================
echo.
echo NOTE: You may need to restart Explorer or log off for changes to take effect.
echo.

pause
