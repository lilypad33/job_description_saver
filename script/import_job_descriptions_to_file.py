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
    "Engineer","Developer","Manager","Analyst","Designer","Scientist","Architect",
    "Administrator","Specialist","Consultant","Coordinator","Lead","Director","Intern",
    "Operator","Technician","Writer","Producer","Editor","Marketer","Researcher",
    "Software","Data","Backend","Frontend","Full Stack","Machine Learning","ML","AI",
    "Security","Cloud","DevOps","SRE","Product","Project","Program","QA","Quality",
    "Support","Sales","Marketing","Finance","HR","People","Operations","IT","UX","UI"
]

BANNED_TITLES = {
    "seniority", "seniority level", "employment", "employment type",
    "job", "title", "position", "role", "location", "locations",
    "department", "division", "schedule", "shift", "vacancy"
}

# Roles you want to strongly prefer if found in the title
PREFERRED_TITLES = {
    "software developer",
    "software engineer",
    "data analyst",
    "data scientist",
    "backend developer",
    "frontend developer",
    "full stack developer",
    "full stack engineer",
    "web developer",
    "application developer"
}

COMMON_FILLER_START = re.compile(r"^(the|a|an|our|we|i)\b", re.IGNORECASE)

def debug(msg):
    if DEBUG:
        print(f"[DEBUG] {msg}")

def has_role_keyword(text):
    t = text.lower()
    return any(kw.lower() in t for kw in ROLE_KEYWORDS)

def looks_title_cased(text):
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
            caps += 1
    return caps >= max(1, int(0.6 * len(words)))

def sanitize_filename(name):
    return "".join(c for c in name if c.isalnum() or c in (" ", "-", "_")).rstrip()

# === TITLE CLEAN/EXTRACT ===
def clean_title(title):
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
        r"\s+in\s+[^/\\,:;–—-]+$",
    ]
    for pat in stop_phrases:
        title = re.sub(pat, "", title, flags=re.IGNORECASE)
    title = re.sub(r"\s*[-–—:]\s+[a-z].*", "", title)
    title = re.sub(r"^(Hiring|Role|Position)\s*[:\-–]\s*", "", title, flags=re.IGNORECASE)
    title = re.split(r"[.|;]\s", title)[0]
    words = title.split()
    if len(words) > 8:
        title = " ".join(words[:8])
    return title.strip(" \t-–—:,.").replace("  ", " ")

# === COMPANY CLEAN/SCORING ===
EMAIL_OR_URL = re.compile(r"(https?://\S+|\b\w+@\w+\.\w+)", re.IGNORECASE)
TRAILING_DEPT = re.compile(r"\b(team|department|group|program|studio|lab|labs)\b\.?$", re.IGNORECASE)
LEADING_JUNK = re.compile(r"^(company|employer|organization|org)\s*[:\-–]\s*", re.IGNORECASE)
NON_NAME_VERBS = re.compile(r"\b(is|are|seeking|hiring|looking|need|needs|join|build|help|drive|lead)\b", re.IGNORECASE)

def clean_company(name):
    name = EMAIL_OR_URL.sub("", name)
    name = name.replace("®", "").replace("™", "").replace("©", "")
    name = LEADING_JUNK.sub("", name).strip()
    name = re.sub(r"\s*[-–—:|]\s+[a-z].*", "", name)
    name = TRAILING_DEPT.sub("", name).strip()
    name = re.sub(r"\s+", " ", name).strip(" \t-–—:,.")
    name = re.split(r"[|,/]", name)[0].strip()
    return name

def is_probable_company(name):
    if not name or len(name) < 2:
        return False
    if EMAIL_OR_URL.search(name):
        return False
    if COMMON_FILLER_START.match(name):
        return False
    if NON_NAME_VERBS.search(name):
        return False
    words = name.split()
    if len(words) > 6:
        return False
    if not any(w and w[0].isupper() for w in words):
        return False
    if not re.search(r"[A-Za-z]", name):
        return False
    return True

def company_score(name):
    score = 0
    if re.search(r"\b(Inc|LLC|Ltd|Limited|Corporation|Corp|GmbH|PLC|Pte|BV|S\.A\.|SAS)\b\.?", name):
        score += 3
    if looks_title_cased(name):
        score += 2
    if len(name.split()) > 4:
        score -= 2
    if TRAILING_DEPT.search(name):
        score -= 2
    if name.isupper() or name.islower():
        score -= 1
    return score

# === LINES PREP ===
lines = [ln.strip() for ln in job_description.splitlines() if ln.strip()]
debug(f"Total lines: {len(lines)}")

# === TITLE CANDIDATES ===
title_candidates = []

def add_title_candidate(val, score, why):
    val = re.sub(r"\s+", " ", val).strip()
    if not val:
        return
    title_candidates.append((val, score, why))
    debug(f"Title candidate (+{score}): '{val}' via {why}")

# 1) Explicit labels
m = re.search(r"(?:Job\s*Title|Position|Role|Title)\s*[:\-–]\s*([^\n]+)", job_description, flags=re.IGNORECASE)
if m: add_title_candidate(m.group(1), 6, "label")

# 2) Looking for a/an ...
m = re.search(r"(?i)looking\s+for\s+a[n]?\s+([^\n]+)", job_description)
if m: add_title_candidate(m.group(1), 5, "looking for a/an")

# 3) Early lines with separators and title-cased lines
for ln in lines[:5]:
    for sep in [" - ", " – ", " — ", ":", " | "]:
        if sep in ln:
            left, right = ln.split(sep, 1)
            if left and left[0].isupper():
                add_title_candidate(left, 4, f"before '{sep.strip()}'")
            if right and right[0].isupper():
                add_title_candidate(right, 3, f"after '{sep.strip()}'")
    if ln and ln[0].isupper() and looks_title_cased(ln):
        add_title_candidate(ln, 3, "title-cased line")

# 4) Title @/at Company (take title side)
m = re.search(r"^([A-Z][A-Za-z0-9/&\-\s]+?)\s*@\s*[A-Z][^\n]+", job_description, flags=re.MULTILINE)
if m: add_title_candidate(m.group(1), 5, "Title @ Company")
m = re.search(r"^([A-Z][A-Za-z0-9/&\-\s]+?)\s+at\s+[A-Z][^\n]+", job_description, flags=re.MULTILINE|re.IGNORECASE)
if m: add_title_candidate(m.group(1), 4, "Title at Company")

def clean_and_is_banned(title_text):
    t = clean_title(title_text).strip().lower()
    return t in BANNED_TITLES

def pick_best_title():
    best, best_score = None, -999
    for val, base, why in title_candidates:
        cleaned = clean_title(val)
        # Skip banned titles like "Seniority" etc.
        if cleaned.strip().lower() in BANNED_TITLES:
            debug(f"Rejecting title '{cleaned}' (banned)")
            continue
        score = base
        if has_role_keyword(val):
            score += 3
        if looks_title_cased(val):
            score += 2
        if COMMON_FILLER_START.match(val):
            score -= 4
        if len(val.split()) > 10:
            score -= 3
        if not val[0].isupper():
            score -= 2
        # Boost if it contains a preferred role
        if any(pref in cleaned.lower() for pref in PREFERRED_TITLES):
            score += 5
            debug(f"Boosting '{cleaned}' for matching preferred role")
        # Penalize if cleaning removed too much (indicates junk)
        if len(cleaned) <= max(3, len(val) * 0.5):
            score -= 1
        debug(f"Title score {score} for '{cleaned}' (from '{val}' via {why})")
        if score > best_score:
            best_score, best = score, cleaned
    return best

best_title = pick_best_title()

# === COMPANY CANDIDATES ===
company_candidates = []

def add_company_candidate(val, score, why):
    cleaned = clean_company(val)
    if not cleaned:
        return
    company_candidates.append((cleaned, score, why))
    debug(f"Company candidate (+{score}): '{cleaned}' via {why}")

# 1) Explicit labels
m = re.search(r"(?:Company|Employer|Organization|Hiring\s*Organization)\s*[:\-–]\s*([^\n]+)", job_description, flags=re.IGNORECASE)
if m: add_company_candidate(m.group(1), 7, "label")

# 2) @ Company (stop at punctuation, avoid emails)
for m in re.finditer(r"@\s*([A-Z][A-Za-z0-9&.,' ]+)", job_description):
    add_company_candidate(m.group(1), 6, "@ Company")

# 3) at Company — avoid phrases like 'at scale', 'at the', etc.
for m in re.finditer(r"\bat\s+(?!the\b|scale\b|least\b|most\b)([A-Z][A-Za-z0-9&.,' ]+)", job_description, flags=re.IGNORECASE):
    add_company_candidate(m.group(1), 5, "at Company")

# 4) Lines like "Careers at X", "Join X"
for ln in lines[:12]:
    m = re.search(r"(?i)(?:careers\s+at|join)\s+([A-Z][A-Za-z0-9&.,' ]+)", ln)
    if m: add_company_candidate(m.group(1), 4, "careers/join line")

# 5) Proper-noun-like early lines without verbs (and no role keywords)
for ln in lines[:8]:
    if not NON_NAME_VERBS.search(ln) and looks_title_cased(ln) and not has_role_keyword(ln):
        add_company_candidate(ln, 3, "proper-noun line")

def pick_best_company():
    best, best_score = None, -999
    for val, base, why in company_candidates:
        if not is_probable_company(val):
            debug(f"Reject company '{val}' (fails plausibility) from {why}")
            continue
        score = base + company_score(val)
        # Penalize trailing locations (e.g., "Acme Corp, New York")
        if re.search(r",\s*[A-Z][a-z]+$", val): score -= 2
        # Prefer shorter clean names
        if len(val) > 40: score -= 3
        debug(f"Company score {score} for '{val}' via {why}")
        if score > best_score:
            best_score, best = score, val
    return best

best_company = pick_best_company()

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