import os
import re
import pyperclip
from datetime import datetime
from docx import Document
from dotenv import load_dotenv

# === SETTINGS ===
DEBUG = True  # Set to False to hide extraction logs

# === LOAD ENVIRONMENT VARIABLES ===
# .env should include: SAVE_FOLDER=C:\path\to\your\folder
load_dotenv()
SAVE_FOLDER = os.getenv("SAVE_FOLDER")
if not SAVE_FOLDER:
    print("Error: SAVE_FOLDER not set in .env")
    exit(1)
os.makedirs(SAVE_FOLDER, exist_ok=True)

# === GET CLIPBOARD CONTENT ===
job_description = pyperclip.paste()
if not job_description.strip():
    print("Clipboard is empty. Copy a job description first.")
    exit(1)

# === UTILITIES ===
ROLE_KEYWORDS = [
    # common role nouns
    "Engineer","Developer","Manager","Analyst","Designer","Scientist","Architect",
    "Administrator","Specialist","Consultant","Coordinator","Lead","Director","Intern",
    "Operator","Technician","Writer","Producer","Editor","Marketer","Researcher",
    # domain terms often in titles
    "Software","Data","Backend","Frontend","Full Stack","Machine Learning","ML","AI",
    "Security","Cloud","DevOps","SRE","Product","Project","Program","QA","Quality",
    "Support","Sales","Marketing","Finance","HR","People","Operations","IT","UX","UI"
]

def has_role_keyword(text):
    t = text.lower()
    for kw in ROLE_KEYWORDS:
        if kw.lower() in t:
            return True
    return False

def looks_title_cased(text):
    # Allow words like "of", "and", "for" to be lowercase, most others capitalized
    small = {"of","and","for","to","in","on","with","the","a","an","or"}
    words = [w for w in re.split(r"\s+", text.strip()) if w]
    if not words:
        return False
    caps = 0
    for i, w in enumerate(words):
        if re.match(r"^[A-Za-z]+$", w):
            if w[0].isupper() or (i > 0 and w.lower() in small):
                caps += 1
        else:
            caps += 1  # allow symbols like C++, SRE
    return caps >= max(1, int(0.6 * len(words)))  # majority look proper

def clean_title(title):
    # Remove trailing fluff after common phrases
    stop_phrases = [
        r"\s+who\s+is\s+.*",
        r"\s+that\s+is\s+.*",
        r"\s+with\s+experience\s+.*",
        r"\s+to\s+join\s+our\s+team.*",
        r"\s+to\s+help\s+.*",
        r"\s+as\s+part\s+of\s+.*",
        r"\s+needed\s+.*",
        r"\s+ASAP.*",
        r"\s+immediately.*",
        r"\s+based\s+in\s+.*",
        r"\s+in\s+[^/\\,:;–—-]+$",  # trailing "in City"
    ]
    for pat in stop_phrases:
        title = re.sub(pat, "", title, flags=re.IGNORECASE)

    # Cut at punctuation if followed by lowercase descriptive text
    title = re.sub(r"\s*[-–—:]\s+[a-z].*", "", title)

    # Trim leading filler if present
    title = re.sub(r"^(Hiring|Role|Position)\s*[:\-–]\s*", "", title, flags=re.IGNORECASE)

    # Hard cut at sentence punctuation if very long
    title = re.split(r"[.|;]\s", title)[0]

    # Limit words to keep it tight
    words = title.split()
    if len(words) > 8:
        title = " ".join(words[:8])

    return title.strip(" \t-–—:,.").replace("  ", " ")

def sanitize_filename(name):
    return "".join(c for c in name if c.isalnum() or c in (" ", "-", "_")).rstrip()

def debug(msg):
    if DEBUG:
        print(f"[DEBUG] {msg}")

# === PREPROCESS LINES ===
lines = [ln.strip() for ln in job_description.splitlines() if ln.strip()]
debug(f"Total lines: {len(lines)}")

# === COLLECT TITLE CANDIDATES ===
title_candidates = []

def add_candidate(val, score, why):
    val = re.sub(r"\s+", " ", val).strip()
    if not val:
        return
    title_candidates.append((val, score, why))
    debug(f"Title candidate (+{score}): '{val}' via {why}")

# 1) Explicit labels
m = re.search(r"(?:Job\s*Title|Position|Role|Title)\s*[:\-–]\s*([^\n]+)", job_description, flags=re.IGNORECASE)
if m:
    add_candidate(m.group(1), 6, "label")

# 2) Looking for a/an ...
m = re.search(r"(?i)looking\s+for\s+a[n]?\s+([^\n]+)", job_description)
if m:
    add_candidate(m.group(1), 5, "looking for a/an")

# 3) Subject-like first good line: capture before dash/colon if capitalized
for ln in lines[:5]:  # only early lines
    # Common separators
    for sep in [" - ", " – ", " — ", ":", " | "]:
        if sep in ln:
            left, right = ln.split(sep, 1)
            if left and left[0].isupper():
                add_candidate(left, 4, f"before separator '{sep.strip()}'")
            if right and right[0].isupper():
                add_candidate(right, 3, f"after separator '{sep.strip()}'")
    # Whole line if it looks like a title
    if ln and ln[0].isupper() and looks_title_cased(ln):
        add_candidate(ln, 3, "title-cased line")

# 4) Patterns like "Title @ Company" or "Title at Company" (take title side)
m = re.search(r"^([A-Z][A-Za-z0-9/&\-\s]+?)\s*@\s*[A-Z][^\n]+", job_description, flags=re.MULTILINE)
if m:
    add_candidate(m.group(1), 5, "Title @ Company")
m = re.search(r"^([A-Z][A-Za-z0-9/&\-\s]+?)\s+at\s+[A-Z][^\n]+", job_description, flags=re.MULTILINE|re.IGNORECASE)
if m:
    add_candidate(m.group(1), 4, "Title at Company")

# 5) Fallback: first capitalized phrase containing a role keyword
for ln in lines[:10]:
    if has_role_keyword(ln) and ln[0].isupper():
        add_candidate(ln, 4, "contains role keyword")

# Score boosts/penalties and pick best
best_title = None
best_score = -999
for val, base, why in title_candidates:
    score = base
    # Boost if contains role keyword
    if has_role_keyword(val):
        score += 3
    # Boost if looks title-cased
    if looks_title_cased(val):
        score += 2
    # Penalize if starts with lowercase or filler
    if re.match(r"^(the|a|an|our|we|i)\b", val, flags=re.IGNORECASE):
        score -= 4
    # Penalize very long phrases
    if len(val.split()) > 10:
        score -= 3
    # Prefer capitalized first char
    if not val[0].isupper():
        score -= 2

    cleaned = clean_title(val)
    # Slight penalty if cleaning removed a lot
    if len(cleaned) <= max(3, len(val) * 0.5):
        score -= 1

    debug(f"Title score {score} for '{cleaned}' (from '{val}' via {why})")

    if score > best_score:
        best_score = score
        best_title = cleaned

# === COMPANY EXTRACTION ===
company_candidates = []

def add_company(val, score, why):
    val = re.sub(r"\s+", " ", val).strip(" \t-–—:,.")
    if not val:
        return
    # Trim trailing descriptors
    val = re.sub(r"\b(team|department|group)$", "", val, flags=re.IGNORECASE).strip()
    company_candidates.append((val, score, why))
    debug(f"Company candidate (+{score}): '{val}' via {why}")

# 1) Explicit labels
m = re.search(r"(?:Company|Employer|Organization|Hiring\s*Organization)\s*[:\-–]\s*([^\n]+)", job_description, flags=re.IGNORECASE)
if m:
    add_company(m.group(1), 6, "label")

# 2) @ Company
for m in re.finditer(r"@\s*([A-Z][A-Za-z0-9&.,' ]+)", job_description):
    add_company(m.group(1), 5, "@ Company")

# 3) at Company
for m in re.finditer(r"(?i)\bat\s+([A-Z][A-Za-z0-9&.,' ]+)", job_description):
    add_company(m.group(1), 4, "at Company")

# 4) Lines with "Careers at X", "Join X", etc.
for ln in lines[:10]:
    m = re.search(r"(?i)(?:careers\s+at|join)\s+([A-Z][A-Za-z0-9&.,' ]+)", ln)
    if m:
        add_company(m.group(1), 3, "careers/join line")

# Pick best company (prefer shorter, capitalized)
best_company = None
best_company_score = -999
for val, base, why in company_candidates:
    score = base
    # Prefer Inc/LLC/etc. slightly (often real company entities)
    if re.search(r"\b(Inc|LLC|Ltd|Corporation|Corp)\b\.?", val):
        score += 1
    # Penalize overly long names
    if len(val.split()) > 8:
        score -= 2
    # Boost capitalized appearance
    if looks_title_cased(val):
        score += 1
    debug(f"Company score {score} for '{val}' via {why}")
    if score > best_company_score:
        best_company_score = score
        best_company = val

# === CONFIRM/EDIT ===
if not best_title:
    best_title = input("Enter the job title: ").strip()
else:
    user = input(f"Detected job title: '{best_title}'. Press Enter to accept or type a correction: ").strip()
    if user:
        best_title = user

if not best_company:
    best_company = input("Enter the company name: ").strip()
else:
    user = input(f"Detected company: '{best_company}'. Press Enter to accept or type a correction: ").strip()
    if user:
        best_company = user

# === SAVE DOCX ===
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
file_name = f"{sanitize_filename(best_company)} - {sanitize_filename(best_title)} - {timestamp}.docx"
file_path = os.path.join(SAVE_FOLDER, file_name)

doc = Document()
doc.add_heading(best_title, level=1)
doc.add_paragraph(f"Company: {best_company}")
doc.add_paragraph("")  # blank line
doc.add_paragraph(job_description)
doc.save(file_path)

print(f"Job description saved to: {file_path}")