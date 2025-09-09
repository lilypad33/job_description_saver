# 📄 Job Description Saver

This script extracts job titles and company names from copied job descriptions and saves the full text to a timestamped file. It uses smart pattern matching to clean up noisy data (like LinkedIn artifacts) and supports saving as either `.txt` or `.docx`.

---

## 🖥️ Platform Support

- ✅ **Windows**: Fully supported via `run.bat`
- ❌ **Mac/Linux**: Not currently supported, but versions can be created on request

> ⚠️ When you first run the `.bat` files, you'll see a message confirming that this setup is Windows-only.

---

## 🚀 Setup Instructions (Windows)

1. **Install Python**  
   Download and install Python from [https://www.python.org](https://www.python.org).  
   ✅ Be sure to check “Add Python to PATH” during installation.

2. **Install Dependencies**  
   Run the included `setup_dependencies.bat` file to install required Python packages:
   ```bat
   @echo off
   python -m pip install --upgrade pip
   python -m pip install pyperclip python-dotenv python-docx
   pause
   ```

3. **Create a `.env` File**  
   In the same folder as the script, create a file named `.env` and add:
   ```
   SAVE_FOLDER=C:\Path\To\Your\SummaryFolder
   ```
   Replace the path with the folder where you want saved job descriptions to go.

---

## 🖱️ How to Use

1. **Copy a job description**  
   Highlight and copy the full job description from any source (LinkedIn, job board, email, etc.).

2. **Run the script**  
   Double-click `run.bat`. The script will:
   - Automatically detect the job title and company name
   - Ask you to confirm or correct them
   - Prompt you to choose a file format (`txt` or `docx`)
   - Save the full description to your specified folder

3. **Find your saved file**  
   The filename will look like:
   ```
   ABCD Corp - JobTitle Example Role - 2025-09-08_19-55.txt
   ```

---

## ⚙️ Customization

- **Default format**: You can change the default save format by editing this line in the script:
  ```python
  DEFAULT_FORMAT = "txt"
  ```
  Change `"txt"` to `"docx"` if you prefer Word documents by default.

- **Command-line arguments**: Not currently implemented. The script will always prompt you to choose between `.txt` and `.docx`.

---

## 🧠 Smart Features

- Cleans noisy titles like “Seniority level” or “Employment type”
- Boosts developer-type roles like “Software Engineer” or “Data Analyst”
- Removes LinkedIn artifacts like “logo” or “view profile”
- Lets you confirm and correct extracted fields before saving

---

## 🐧 Mac/Linux Setup (Experimental)

The script is written in Python and should work on macOS or Linux with minimal changes. It has not been formally tested, but here's how to try it:

1. **Install Python**  
   ```bash
   brew install python3      # macOS
   sudo apt install python3  # Ubuntu/Debian
   ```

2. **Install Dependencies**  
   ```bash
   pip install pyperclip python-dotenv python-docx
   ```

3. **Create a `.env` File**  
   In the same folder as the script:
   ```
   SAVE_FOLDER=/path/to/your/summary/folder
   ```

4. **Run the script manually**  
   ```bash
   python your_script.py
   ```

> If you'd like a shell script version (`run.sh`), feel free to request it.

---

## 📬 Feedback & Contributions

If you’d like to contribute, request Mac/Linux support, or suggest improvements, feel free to reach out. This project is designed to be simple, smart, and easy to extend.