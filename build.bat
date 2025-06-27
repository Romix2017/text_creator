@echo off
echo Creating Text Creator executable...

:: Remove previous build and dist directories if they exist
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul

:: Run PyInstaller
pyinstaller --noconfirm --clean --windowed --onefile ^
    --name "TextCreator" ^
    --add-data "C:\Users\RVK-PC\AppData\Local\Programs\Python\Python311\Lib\site-packages\PyQt6\Qt6\plugins\*;PyQt6/Qt6/plugins" ^
    text_creator.py

echo.
echo Build complete! The executable is in the 'dist' folder.
pause
