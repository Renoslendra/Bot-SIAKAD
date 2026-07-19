# Development Guidelines & Standards

## Bot SIAKAD — Auto Course Selection

---

## 1. Tech Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| Language | Python | 3.10+ |
| Browser Automation | Playwright | Latest |
| Environment Config | python-dotenv | Latest |
| Logging | loguru | Latest |
| Runtime | Windows PowerShell 5.1 | - |

---

## 2. Project Structure

```
Bot-SIAKAD/
├── .env                    # Credentials (JANGAN commit)
├── .env.example            # Template .env
├── .gitignore              # Git ignore rules
├── config.py               # Konfigurasi MK & settings
├── main.py                 # Entry point / orchestrator
├── login.py                # Module: authentication
├── scraper.py              # Module: scraping mata kuliah
├── selector.py             # Module: course selection algorithm
├── submitter.py            # Module: auto-submit KRS
├── utils.py                # Shared utilities & helpers
├── requirements.txt        # Python dependencies
├── PRD.md                  # Product Requirements Document
├── Task.md                 # Task breakdown & milestones
├── Guideline.md            # This file
├── README.md               # User-facing documentation
└── logs/                   # Output directory (JANGAN commit)
    ├── bot.log             # Activity log
    ├── session.json        # Saved session cookies
    ├── scraped_courses.json# Scraped course data
    ├── selection_report.json# Selection results
    └── screenshots/        # Browser screenshots
        ├── login.png
        ├── krs_before.png
        └── krs_after.png
```

---

## 3. Coding Standards

### 3.1 General Rules

- **No comments** unless explicitly requested
- Use English for all code (variable names, function names, etc.)
- Use Indonesian only for log messages and user-facing output
- Follow PEP 8 style guide
- Maximum line length: 120 characters
- Use type hints untuk semua function signatures

### 3.2 Naming Conventions

| Type | Convention | Example |
|------|-----------|---------|
| File/module | snake_case | `scraper.py` |
| Function | snake_case | `scrape_courses()` |
| Variable | snake_case | `course_list` |
| Class | PascalCase | `CourseSelector` |
| Constant | UPPER_SNAKE_CASE | `TARGET_SKS = 23` |
| Private | _prefix | `_internal_state` |

### 3.3 Function Signature Pattern

```python
def scrape_courses(page: Page, target_codes: list[str]) -> list[dict]:
    ...

def check_schedule_conflict(new_schedule: dict, existing: list[dict]) -> bool:
    ...

def select_courses(courses: list[dict], priority: list[str], target_sks: int) -> dict:
    ...
```

---

## 4. Configuration Standards

### 4.1 Environment Variables (`.env`)

```
SIAKAD_USERNAME=your_username
SIAKAD_PASSWORD=your_password
HEADLESS=true
LOG_LEVEL=INFO
AUTO_CONFIRM=false
```

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| SIAKAD_USERNAME | string | (required) | Username SIAKAD |
| SIAKAD_PASSWORD | string | (required) | Password SIAKAD |
| HEADLESS | bool | true | Run browser tanpa GUI |
| LOG_LEVEL | string | INFO | Logging level |
| AUTO_CONFIRM | bool | false | Auto-confirm submit tanpa prompt |

### 4.2 Config File (`config.py`)

```python
TARGET_SKS = 23

PRIORITY_COURSES = [
    {"code": "IF2228", "name": "Sistem Terdistribusi", "sks": 3},
    {"code": "IF2229", "name": "Proyek Perangkat Lunak", "sks": 3},
    {"code": "IF2230", "name": "Pembelajaran Mesin", "sks": 3},
    {"code": "IF2231", "name": "Proyek Sains Data", "sks": 3},
    {"code": "IF2232", "name": "Metodologi Penelitian", "sks": 2},
    {"code": "IF2260", "name": "Pemodelan Proses Bisnis", "sks": 3},
    {"code": "IF2254", "name": "Keamanan Data & Aplikasi", "sks": 3},
    {"code": "IF2259", "name": "Pengolahan Citra", "sks": 3},
]

FALLBACK_COURSES = [
    {"code": "IF2255", "name": "Technopreneurship", "sks": 2},
    {"code": "IF2256", "name": "Komputasi Numerik", "sks": 3},
    {"code": "IF2257", "name": "Pemrograman Game", "sks": 3},
    {"code": "IF2258", "name": "Basis Data III", "sks": 3},
]

SIAKAD_URL = "https://siakad.trunojoyo.ac.id"
SIAKAD_KRS_URL = "https://siakad.trunojoyo.ac.id/index.php?pModule=zabIzKI=&pSub=zabIzKI=&pAct=16DG2g=="

MAX_LOGIN_RETRIES = 3
MAX_SUBMIT_RETRIES = 2
REQUEST_TIMEOUT = 30000
ACTION_DELAY = 1.0
```

---

## 5. Error Handling Standards

### 5.1 Exception Hierarchy

```python
class BotSIAKADError(Exception):
    """Base exception"""

class LoginError(BotSIAKADError):
    """Login gagal"""

class ScrapingError(BotSIAKADError):
    """Scraping gagal"""

class SelectionError(BotSIAKADError):
    """Selection algorithm gagal"""

class SubmitError(BotSIAKADError):
    """Submit KRS gagal"""
```

### 5.2 Error Handling Rules

- Semua external calls (network, browser) harus di-wrap try/except
- Log error SEBELUM raise exception
- Use specific exception types, bukan generic `Exception`
- Retry untuk transient errors (timeout, network)
- Fail fast untuk permanent errors (wrong credentials, invalid data)

### 5.3 Retry Pattern

```python
async def with_retry(func, max_retries: int = 3, delay: float = 2.0):
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(delay * (attempt + 1))
            else:
                raise
```

---

## 6. Logging Standards

### 6.1 Log Levels

| Level | Usage | Example |
|-------|-------|---------|
| DEBUG | Detail teknis, HTML snippets | "Found 15 course elements" |
| INFO | Major actions & results | "Login berhasil" |
| WARNING | Non-fatal issues | "Kelas A penuh, coba kelas B" |
| ERROR | Failures that stop execution | "Login gagal setelah 3 retry" |
| CRITICAL | System-level failures | "Browser crash" |

### 6.2 Log Format

```
[2026-07-19 10:30:00] [INFO] [login] Login berhasil — user: student123
[2026-07-19 10:30:05] [INFO] [scraper] Ditemukan 12 mata kuliah semester 5
[2026-07-19 10:30:06] [WARNING] [selector] IF2228 Kelas A bentrok — coba Kelas B
[2026-07-19 10:30:06] [INFO] [selector] IF2228 Kelas B terpilih — Senin 13:00-15:30
[2026-07-19 10:30:10] [INFO] [submitter] KRS berhasil disubmit — Total: 23 SKS
```

### 6.3 Screenshot Rules

- Screenshot diambil di setiap major milestone:
  - Setelah login berhasil
  - Sebelum submit KRS
  - Setelah submit KRS
  - Saat error terjadi
- Naming: `{module}_{action}_{timestamp}.png`
- Storage: `logs/screenshots/`

---

## 7. Playwright Best Practices

### 7.1 Browser Setup

```python
from playwright.async_api import async_playwright

async def create_browser(headless: bool = True):
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=headless)
    context = await browser.new_context(
        viewport={"width": 1920, "height": 1080},
        locale="id-ID"
    )
    page = await context.new_page()
    return pw, browser, context, page
```

### 7.2 Waiting Strategy

- **ALWAYS** gunakan explicit waits, JANGAN pakai `time.sleep()` untuk waiting elements
- Gunakan `page.wait_for_selector()` untuk menunggu element muncul
- Gunakan `page.wait_for_load_state("networkidle")` untuk menunggu network selesai
- Timeout default: 30 detik, configurable

### 7.3 Selector Strategy

- Prioritas selector: `data-testid` > `id` > CSS selector > XPath
- Gunakan text-based selectors untuk button/link (`page.get_by_role("button", name="Simpan")`)
- Fallback ke XPath hanya jika CSS selector tidak bisa

### 7.4 Anti-Detection

- Set realistic User-Agent
- Tambah random delay antar actions (0.5 - 2 detik)
- Jangan lakukan request terlalu cepat (rate limit: min 1 detik antar page navigation)

---

## 8. Security Standards

| Rule | Description |
|------|-------------|
| No hardcoded secrets | Semua credentials di `.env`, JANGAN di source code |
| `.env` in `.gitignore` | Pastikan `.env` tidak pernah ter-commit |
| No logging credentials | JANGAN log username/password di log file |
| Session cleanup | Hapus `session.json` setelah selesai (optional) |
| Minimal permissions | Bot hanya mengakses halaman KRS, tidak explore halaman lain |

---

## 9. Testing Guidelines

### 9.1 Dry Run Mode

- Bot support `--dry-run` flag
- Di dry-run mode: lakukan semua step KECUALI submit KRS
- Print hasil selection tanpa submit

### 9.2 Manual Testing Checklist

- [ ] Login berhasil dengan credentials valid
- [ ] Login gagal ditangani dengan benar (3 retry + error message)
- [ ] Scraping return data lengkap dan akurat
- [ ] Schedule conflict detection benar (bentrok & tidak bentrok)
- [ ] Selection algorithm menghasilkan 23 SKS tanpa bentrok
- [ ] Submit KRS berhasil dan terverifikasi
- [ ] Logging output lengkap dan readable
- [ ] Screenshots tersimpan dengan benar
- [ ] Error handling works untuk semua known failure modes

---

## 10. Git Standards

### 10.1 `.gitignore`

```
.env
__pycache__/
*.pyc
logs/
*.png
session.json
.venv/
venv/
```

### 10.2 Commit Message Format

```
<type>: <short description>

Types: feat, fix, refactor, docs, test, chore
```

**Examples:**
```
feat: implement login module
feat: add schedule conflict detection
fix: handle timeout on KRS page
docs: update README with setup instructions
```

---

## 11. Schedule Conflict Algorithm Reference

### Logic

```python
def is_conflict(schedule_a: dict, schedule_b: dict) -> bool:
    if schedule_a["day"] != schedule_b["day"]:
        return False
    return (
        schedule_a["start"] < schedule_b["end"] and
        schedule_a["end"] > schedule_b["start"]
    )
```

### Time Parsing

- Format input: `"Senin 08:00-10:30"`
- Parse ke: `{"day": "Senin", "start": "08:00", "end": "10:30"}`
- Convert time ke minutes untuk comparison: `"08:00"` → `480`, `"10:30"` → `630`

### Conflict Examples

| MK A | MK B | Conflict? |
|------|------|-----------|
| Senin 08:00-10:30 | Senin 09:00-11:00 | YES (overlap) |
| Senin 08:00-10:30 | Senin 10:30-12:00 | NO (exact boundary) |
| Senin 08:00-10:30 | Selasa 08:00-10:30 | NO (different day) |
| Rabu 13:00-15:00 | Rabu 14:00-16:00 | YES (overlap) |
