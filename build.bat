@echo off
:: ============================================================
:: FastFileOp Build Script
:: Compiles C++ DLL and packages Python application
:: ============================================================

setlocal enabledelayedexpansion

echo ============================================================
echo FastFileOp Build Script
echo ============================================================
echo.

:: Get script directory
set "SCRIPT_DIR=%~dp0"
set "PROJECT_DIR=%SCRIPT_DIR%"

:: ============================================================
:: Step 1: Compile C++ DLL
:: ============================================================
echo [Step 1/3] Compiling C++ DLL...
echo.

set "DLL_DIR=%PROJECT_DIR%FastFileOpShim"
set "DLL_OUTPUT=%PROJECT_DIR%dist\FastFileOpShim.dll"

:: Create output directory
if not exist "%PROJECT_DIR%dist" mkdir "%PROJECT_DIR%dist"

:: Check for MinGW (g++.exe)
where g++.exe >nul 2>&1
if %errorlevel% equ 0 (
    echo Found MinGW compiler (g++.exe)
    goto :build_mingw
)

:: Check for MSVC (cl.exe)
where cl.exe >nul 2>&1
if %errorlevel% equ 0 (
    echo Found MSVC compiler (cl.exe)
    goto :build_msvc
)

:: No compiler found
echo ERROR: No C++ compiler found!
echo Please install MinGW-w64 or Visual Studio with C++ tools.
echo.
pause
exit /b 1

:build_mingw
echo.
echo Compiling with MinGW...
echo.

cd /d "%DLL_DIR%"

g++.exe -shared -o "..\dist\FastFileOpShim.dll" ^
    -I. -DBUILDING_DLL -DNDEBUG -O2 ^
    -static-libgcc -static-libstdc++ ^
    stdafx.cpp PipeClient.cpp Utils.cpp CopyHook.cpp DropTarget.cpp ContextMenu.cpp ExplorerCommand.cpp dllmain.cpp ^
    -lshell32 -lole32 -loleaut32 -luser32 -ladvapi32 -luuid

if %errorlevel% neq 0 (
    echo.
    echo ERROR: MinGW compilation failed!
    pause
    exit /b 1
)

echo.
echo C++ DLL compiled successfully: dist\FastFileOpShim.dll
goto :step2

:build_msvc
echo.
echo Compiling with MSVC...
echo.

cd /d "%DLL_DIR%"

cl.exe /nologo /c /EHsc /MD /DNDEBUG /Fo"..\build\" ^
    stdafx.cpp PipeClient.cpp Utils.cpp CopyHook.cpp DropTarget.cpp ContextMenu.cpp ExplorerCommand.cpp dllmain.cpp

if %errorlevel% neq 0 (
    echo.
    echo ERROR: MSVC compilation failed!
    pause
    exit /b 1
)

link.exe /nologo /DLL /OUT:"..\dist\FastFileOpShim.dll" ^
    "..\build\stdafx.obj" "..\build\PipeClient.obj" ^
    "..\build\Utils.obj" "..\build\CopyHook.obj" "..\build\DropTarget.obj" ^
    "..\build\ContextMenu.obj" "..\build\ExplorerCommand.obj" ^
    "..\build\dllmain.obj" ^
    shell32.lib ole32.lib oleaut32.lib user32.lib advapi32.lib uuid.lib

if %errorlevel% neq 0 (
    echo.
    echo ERROR: DLL linking failed!
    pause
    exit /b 1
)

echo.
echo C++ DLL compiled successfully: dist\FastFileOpShim.dll
goto :step2

:step2
:: ============================================================
:: Step 2: Package Python Application
:: ============================================================
echo.
echo [Step 2/3] Packaging Python application...
echo.

cd /d "%PROJECT_DIR%"

:: Check for PyInstaller
python -c "import PyInstaller" >nul 2>&1
if %errorlevel% neq 0 (
    echo PyInstaller not found, installing...
    pip install pyinstaller
    if %errorlevel% neq 0 (
        echo ERROR: Failed to install PyInstaller!
        pause
        exit /b 1
    )
)

:: Check for other dependencies
echo Checking Python dependencies...
pip install -r requirements.txt -q

:: Build with PyInstaller
echo.
echo Building executable with PyInstaller...
pyinstaller --onefile --noconsole --name FastFileOp ^
    --distpath dist --workpath build ^
    --clean main.py

if %errorlevel% neq 0 (
    echo.
    echo ERROR: PyInstaller build failed!
    pause
    exit /b 1
)

echo.
echo Python executable created: dist\FastFileOp.exe

:: ============================================================
:: Step 3: Output completion info
:: ============================================================
echo.
echo [Step 3/3] Build complete!
echo.
echo ============================================================
echo Build successful!
echo ============================================================
echo.
echo Output files:
echo   - dist\FastFileOp.exe      (Main application)
echo   - dist\FastFileOpShim.dll  (Shell extension)
echo.
echo To install, run install.bat as Administrator.
echo.

pause
