@echo off
setlocal
title Building Ayumu's Crafting Buddy with Nuitka
echo ===============================================
echo   Ayumu's Crafting Buddy - EXE Build Script
echo   Using Nuitka + MSVC Build Tools
echo ===============================================
echo.

cd /d "%~dp0"

for %%I in ("C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\Common7\Tools\VsDevCmd.bat") do set "DEV_PROMPT=%%~sI"

if not exist "%DEV_PROMPT%" (
    echo ERROR: Could not find VsDevCmd.bat!
    echo Checked: %DEV_PROMPT%
    pause
    exit /b 1
)

echo [1/2] Launching Visual Studio Developer environment...

call "%DEV_PROMPT%" && python -m nuitka ^
    --onefile ^
    --msvc=latest ^
    --enable-plugin=tk-inter ^
	--windows-console-mode=disable ^
    --windows-icon-from-ico="images\Logo.ico" ^
    --windows-file-version=1.0.1 ^
    --windows-product-version=1.0.1 ^
    --windows-file-description="Ayumu's Crafting Buddy - Made by Ayumu" ^
    --windows-product-name="Ayumu's Crafting Buddy" ^
    --windows-company-name="Retro ReVamped" ^
	--copyright="Copyright (c) 2025 RetroReVamped" ^
    --include-data-dir="images=images" ^
    --include-data-file="recipes.cfg=recipes.cfg" ^
    --output-dir="dist" ^
    "Ayumu's Crafting Buddy.py"

if %errorlevel% neq 0 (
    echo.
    echo Build failed! Check errors above.
    pause
    exit /b 1
)

echo.
echo Build completed successfully!
echo Output EXE is located in the "dist" folder.
echo.
pause
