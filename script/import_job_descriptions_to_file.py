import os
import pyperclip
from datetime import datetime
from dotenv import load_dotenv


# === CONFIGURATION ===
load_dotenv()

SAVE_FOLDER = os.getenv("SAVE_FOLDER")

# Make sure the folder exists
os.makedirs(SAVE_FOLDER, exist_ok=True)

# === GET USER INPUT ===
job_title = input("Enter the job title: ").strip()
company_name = input("Enter the company name: ").strip()

# === GET CLIPBOARD CONTENT ===
job_description = pyperclip.paste()

if not job_description.strip():
    print("Clipboard is empty. Please copy the job description first.")
    exit()

# === CREATE SAFE FILE NAME ===
def sanitize_filename(name):
    return "".join(c for c in name if c.isalnum() or c in (" ", "-", "_")).rstrip()

file_name = f"{sanitize_filename(company_name)} - {sanitize_filename(job_title)}.txt"

# Optional: Add timestamp to avoid overwriting
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
file_name = f"{sanitize_filename(company_name)} - {sanitize_filename(job_title)} - {timestamp}.txt"

# === SAVE FILE ===
file_path = os.path.join(SAVE_FOLDER, file_name)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(job_description)

print(f"Job description saved to: {file_path}")