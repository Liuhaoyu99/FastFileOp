@echo off
:: ============================================================
:: FastFileOp Uninstallation Script
:: Removes FastFileOp from the system
:: Requires Administrator privileges
:: ============================================================

setlocal enabledelayedexpansion

echo ============================================================
echo FastFileOp Uninstallation Script
echo ============================================================
echo.

:: Check for Administrator privileges
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Requesting Administrator privileges...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

set "INSTALL_DIR=%ProgramFiles%\FastFileOp"

echo.
echo WARNING: This will remove FastFileOp from your system.
echo.
pause

:: ============================================================
:: Step 1: Stop running process
:: ============================================================
echo [Step 1/4] Stopping FastFileOp process...

taskkill /f /im "FastFileOp.exe" >nul 2>&1
if %errorlevel% equ 0 (
    echo FastFileOp process stopped.
) else (
    echo No running FastFileOp process found.
)

:: Wait for process to fully terminate
timeout /t 2 /nobreak >nul

:: ============================================================
:: Step 2: Unregister shell extension
:: ============================================================
echo [Step 2/4] Unregistering shell extension...

if exist "%INSTALL_DIR%\FastFileOpShim.dll" (
    regsvr32 /u /s "%INSTALL_DIR%\FastFileOpShim.dll"
    echo Shell extension unregistered.
)

:: Clean up registry entries (in case regsvr32 missed some)
reg delete "HKCR\Directory\ShellEx\CopyHookHandlers\FastFileOp" /f >nul 2>&1
reg delete "HKCR\Folder\ShellEx\CopyHookHandlers\FastFileOp" /f >nul 2>&1
reg delete "HKCR\*\ShellEx\ContextMenuHandlers\FastFileOp" /f >nul 2>&1
reg delete "HKCR\Directory\ShellEx\ContextMenuHandlers\FastFileOp" /f >nul 2>&1
reg delete "HKCR\Folder\ShellEx\ContextMenuHandlers\FastFileOp" /f >nul 2>&1
reg delete "HKCR\Directory\ShellEx\DragDropHandlers\FastFileOp" /f >nul 2>&1
reg delete "HKCR\Folder\ShellEx\DragDropHandlers\FastFileOp" /f >nul 2>&1
reg delete "HKCR\*\ShellEx\ContextMenuHandlers\FastFileOpDelete" /f >nul 2>&1
reg delete "HKCR\Directory\ShellEx\ContextMenuHandlers\FastFileOpDelete" /f >nul 2>&1
reg delete "HKCR\CLSID\{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}" /f >nul 2>&1
reg delete "HKCR\CLSID\{B2C3D4E5-F6A7-8901-BCDE-F12345678901}" /f >nul 2>&1
reg delete "HKCR\CLSID\{C3D4E5F6-A7B8-9012-CDEF-123456789012}" /f >nul 2>&1
reg delete "HKCR\CLSID\{D4E5F6A7-B8C9-0123-DEF0-234567890123}" /f >nul 2>&1

:: ============================================================
:: Step 3: Remove auto-start entry
:: ============================================================
echo [Step 3/4] Removing auto-start entry...

reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "FastFileOp" /f >nul 2>&1
if %errorlevel% equ 0 (
    echo Auto-start entry removed.
) else (
    echo No auto-start entry found.
)

:: ============================================================
:: Step 4: Remove installation directory
:: ============================================================
echo [Step 4/4] Removing installation directory...

if exist "%INSTALL_DIR%" (
    rmdir /s /q "%INSTALL_DIR%"
    if %errorlevel% equ 0 (
        echo Installation directory removed.
    ) else (
        echo WARNING: Could not remove installation directory.
        echo Some files may be in use. Please restart your computer and try again.
    )
) else (
    echo Installation directory not found.
)

echo.
echo ============================================================
echo Uninstallation complete!
echo ============================================================
echo.
echo FastFileOp has been removed from your system.
echo.
echo Note: User data in %APPDATA%\FastFileOp has been preserved.
echo Delete manually if desired.
echo.

pause
