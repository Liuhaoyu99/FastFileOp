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

:: Support running this script either from project root or from inside the dist folder
:: If the exe is next to the script (e.g. running from dist), use that; otherwise use dist\FastFileOp.exe
set "SRC_EXE=%SCRIPT_DIR%dist\FastFileOp.exe"
set "SRC_DLL=%SCRIPT_DIR%dist\FastFileOpShim.dll"
if exist "%SCRIPT_DIR%FastFileOp.exe" (
    set "SRC_EXE=%SCRIPT_DIR%FastFileOp.exe"
)
if exist "%SCRIPT_DIR%FastFileOpShim.dll" (
    set "SRC_DLL=%SCRIPT_DIR%FastFileOpShim.dll"
)

echo Installing to: %INSTALL_DIR%
echo.

:: Prepare install log
set "INSTALL_LOG=%TEMP%\fastfileop_install.log"
echo ===== FastFileOp install started: %DATE% %TIME% =====>> "%INSTALL_LOG%"
echo Installing to: %INSTALL_DIR% >> "%INSTALL_LOG%"

:: ============================================================
:: Step 1: Check source files
:: ============================================================
echo [Step 1/5] Checking source files...

if not exist "%SRC_EXE%" (
    echo ERROR: %SRC_EXE% not found!
    echo Please run build.bat first.
    echo ERROR: %SRC_EXE% not found! >> "%INSTALL_LOG%"
    pause
    exit /b 1
)

if not exist "%SRC_DLL%" (
    echo WARNING: %SRC_DLL% not found, skipping shell extension.
    echo WARNING: %SRC_DLL% not found, skipping shell extension. >> "%INSTALL_LOG%"
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

copy /Y "%SRC_EXE%" "%INSTALL_DIR%\" >nul
if %errorlevel% neq 0 (
    echo ERROR: Failed to copy FastFileOp.exe!
    pause
    exit /b 1
)

if not defined SKIP_DLL (
    copy /Y "%SRC_DLL%" "%INSTALL_DIR%\" >nul
    if %errorlevel% neq 0 (
        echo ERROR: Failed to copy FastFileOpShim.dll!
        pause
        exit /b 1
    )
    if exist "%SCRIPT_DIR%dist\libwinpthread-1.dll" (
        copy /Y "%SCRIPT_DIR%dist\libwinpthread-1.dll" "%INSTALL_DIR%\" >nul
    )
    if exist "%SCRIPT_DIR%libwinpthread-1.dll" (
        copy /Y "%SCRIPT_DIR%libwinpthread-1.dll" "%INSTALL_DIR%\" >nul
    )
)

echo Files copied successfully.
echo.

:: Copy documentation files
if exist "%SCRIPT_DIR%README.md" copy /Y "%SCRIPT_DIR%README.md" "%INSTALL_DIR%\" >nul
if exist "%SCRIPT_DIR%README_zh.md" copy /Y "%SCRIPT_DIR%README_zh.md" "%INSTALL_DIR%\" >nul
if exist "%SCRIPT_DIR%LICENSE" copy /Y "%SCRIPT_DIR%LICENSE" "%INSTALL_DIR%\" >nul
if exist "%SCRIPT_DIR%benchmark.png" copy /Y "%SCRIPT_DIR%benchmark.png" "%INSTALL_DIR%\" >nul

:: ============================================================
:: Step 4: Register shell extension
:: Try both 64-bit and 32-bit regsvr32, then fall back to the shim installer
:: ============================================================
echo [Step 4/5] Registering shell extension...

if not defined SKIP_DLL (
    set "DLL_PATH=%INSTALL_DIR%\FastFileOpShim.dll"

    echo Attempting to register (System32 regsvr32 - 64-bit)...
    "%WINDIR%\System32\regsvr32.exe" /s "%DLL_PATH%" >nul 2>&1
    if %errorlevel% equ 0 (
        echo Shell extension registered (64-bit regsvr32).
        echo Shell extension registered (64-bit regsvr32). >> "%INSTALL_LOG%"
    ) else (
        echo 64-bit registration failed, trying 32-bit regsvr32 (SysWOW64)...
        echo 64-bit registration failed -> trying SysWOW64 regsvr32. >> "%INSTALL_LOG%"
        "%WINDIR%\SysWOW64\regsvr32.exe" /s "%DLL_PATH%" >nul 2>&1
        if %errorlevel% equ 0 (
            echo Shell extension registered (32-bit regsvr32).
            echo Shell extension registered (32-bit regsvr32). >> "%INSTALL_LOG%"
        ) else (
            echo Both regsvr32 attempts failed.
            echo Both regsvr32 attempts failed. >> "%INSTALL_LOG%"
            echo Trying bundled FastFileOpShim installer as a fallback...
            echo Trying bundled FastFileOpShim installer as a fallback... >> "%INSTALL_LOG%"
            if exist "%INSTALL_DIR%\install.bat" (
                call "%INSTALL_DIR%\install.bat" >> "%INSTALL_LOG%" 2>&1
            ) else if exist "%SCRIPT_DIR%FastFileOpShim\install.bat" (
                call "%SCRIPT_DIR%FastFileOpShim\install.bat" >> "%INSTALL_LOG%" 2>&1
            ) else (
                echo No bundled shim installer found to try.
                echo No bundled shim installer found to try. >> "%INSTALL_LOG%"
            )

            :: After fallback attempt, try regsvr32 once more (best-effort)
            "%WINDIR%\System32\regsvr32.exe" /s "%DLL_PATH%" >> "%INSTALL_LOG%" 2>&1
            if %errorlevel% equ 0 (
                echo Shell extension registered after fallback (64-bit regsvr32).
                echo Shell extension registered after fallback (64-bit regsvr32). >> "%INSTALL_LOG%"
            ) else (
                "%WINDIR%\SysWOW64\regsvr32.exe" /s "%DLL_PATH%" >> "%INSTALL_LOG%" 2>&1
                if %errorlevel% equ 0 (
                    echo Shell extension registered after fallback (32-bit regsvr32).
                    echo Shell extension registered after fallback (32-bit regsvr32). >> "%INSTALL_LOG%"
                ) else (
                    echo WARNING: Failed to register shell extension.
                    echo The application will still work, but drag-and-drop interception may not function.
                    echo WARNING: Failed to register shell extension. >> "%INSTALL_LOG%"
                )
            )
        )
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
