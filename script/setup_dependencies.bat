@echo off
echo Installing required Python packages...
python -m pip install --upgrade pip
python -m pip install pyperclip python-docx python-dotenv
echo.
echo All dependencies installed successfully.
pause