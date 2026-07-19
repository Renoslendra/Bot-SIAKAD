# Task Breakdown & Milestones

## Bot SIAKAD — Auto Course Selection

---

## Milestone Overview

| Milestone | Description | Tasks |
|-----------|-------------|-------|
| M1 | Project Setup & Configuration | 5 tasks |
| M2 | Login Module | 4 tasks |
| M3 | Scraping Module | 4 tasks |
| M4 | Selection Engine | 4 tasks |
| M5 | Auto Submit Module | 4 tasks |
| M6 | Logging & Reporting | 3 tasks |
| M7 | Integration & Testing | 4 tasks |

---

## M1: Project Setup & Configuration

### Task 1.1: Initialize Project Structure
- Buat folder structure sesuai Guideline.md
- Buat `requirements.txt` dengan dependencies:
  - `playwright`
  - `python-dotenv`
  - `loguru` (logging)
- Install dependencies: `pip install -r requirements.txt`
- Install Playwright browsers: `playwright install chromium`

### Task 1.2: Create `.env` Template
- Buat `.env.example` dengan fields:
  ```
  SIAKAD_USERNAME=
  SIAKAD_PASSWORD=
  HEADLESS=true
  LOG_LEVEL=INFO
  ```
- Buat `.gitignore` yang exclude `.env`, `logs/`, `__pycache__/`

### Task 1.3: Create Configuration File
- Buat `config.py` berisi:
  - Priority list MK (nama, kode, SKS)
  - Fallback MK list
  - Target SKS = 23
  - SIAKAD URL
  - Timeout settings
  - Retry settings

### Task 1.4: Create Utility Helpers
- Buat `utils.py` berisi:
  - Logger setup (loguru)
  - Time parser (convert "Senin 08:00-10:30" ke structured format)
  - Schedule conflict checker function
  - SKS calculator function

### Task 1.5: Create Main Entry Point
- Buat `main.py` sebagai orchestrator:
  - Load config dari `.env`
  - Run modules secara berurutan: login → scrape → select → submit
  - Error handling global
  - CLI arguments (optional: `--headless`, `--dry-run`)

**Status:** [ ] Pending

---

## M2: Login Module

### Task 2.1: Implement Login Flow
- Buat `login.py`
- Launch Playwright browser (chromium)
- Navigate ke SIAKAD login URL
- Input username dan password dari `.env`
- Klik tombol login
- Wait untuk redirect ke dashboard

### Task 2.2: Handle Login Failures
- Detect login gagal (check error message di halaman)
- Retry login maksimal 3 kali dengan delay
- Raise exception jika login gagal setelah 3 retry
- Log setiap attempt (success/fail)

### Task 2.3: Handle CAPTCHA (if exists)
- Detect apakah ada CAPTCHA di halaman login
- Jika ada: screenshot CAPTCHA, pause execution, prompt user input manual
- Jika tidak ada: lanjut normal

### Task 2.4: Save Session State
- Setelah login berhasil, simpan cookies/storage state
- Save ke `logs/session.json`
- Support reuse session untuk run berikutnya (optional optimization)

**Status:** [ ] Pending

---

## M3: Scraping Module

### Task 3.1: Navigate to KRS Page
- Buat `scraper.py`
- Setelah login, navigate ke halaman pengisian KRS
- URL: `https://siakad.trunojoyo.ac.id/index.php?pModule=zabIzKI=&pSub=zabIzKI=&pAct=16DG2g==`
- Wait untuk page load complete

### Task 3.2: Scrape Course Data
- Parse HTML halaman KRS
- Extract data untuk setiap MK:
  - Nama MK
  - Kode MK
  - SKS
  - Daftar kelas/section (nama kelas)
  - Jadwal per kelas (hari, jam mulai, jam selesai)
  - Sisa kuota per kelas
- Store sebagai list of dictionaries

### Task 3.3: Filter Target Courses
- Filter scraped data: hanya MK yang ada di priority list (`config.py`)
- Log MK yang ditemukan vs tidak ditemukan
- Log total MK dan total SKS yang tersedia

### Task 3.4: Save Scraped Data
- Export scraped data ke `logs/scraped_courses.json`
- Format: structured JSON dengan timestamp
- Print summary ke console

**Status:** [ ] Pending

---

## M4: Selection Engine

### Task 4.1: Implement Greedy Selection Algorithm
- Buat `selector.py`
- Input: scraped course data + priority list + target SKS
- Untuk setiap MK di priority list (berurutan):
  - Ambil semua kelas/section MK tersebut
  - Loop setiap kelas:
    1. Cek kuota > 0
    2. Cek jadwal tidak bentrok dengan MK yang sudah terpilih
    3. Cek total SKS + SKS MK ini <= 23
    4. Jika lolos semua → pilih kelas ini, break
  - Jika semua kelas gagal → skip MK, log warning

### Task 4.2: Implement Schedule Conflict Detection
- Function: `is_schedule_conflict(new_schedule, existing_schedules)`
- Logic:
  - Parse hari dan waktu
  - Jika hari berbeda → no conflict
  - Jika hari sama → cek overlap waktu (start < other_end AND end > other_start)
- Return: boolean (True = bentrok, False = aman)

### Task 4.3: Implement SKS Tracking
- Track total SKS terpilih
- Track daftar MK terpilih (dengan kelas dan jadwal)
- Stop jika total SKS == 23
- Handle edge case: MK terakhir yang bikin > 23 SKS → skip

### Task 4.4: Generate Selection Report
- Output: list of selected courses dengan detail
- Calculate total SKS
- List MK yang gagal diambil + alasan (bentrok/kuota penuh/SKS exceed)
- Save report ke `logs/selection_report.json`
- Print summary ke console

**Status:** [ ] Pending

---

## M5: Auto Submit Module

### Task 5.1: Pre-Submit Confirmation
- Buat `submitter.py`
- Tampilkan ringkasan MK yang akan di-submit:
  - Daftar MK + kelas + jadwal + SKS
  - Total SKS
- Prompt user: "Submit KRS? (y/n)" — configurable di config (auto_confirm = True/False)

### Task 5.2: Submit KRS to SIAKAD
- Untuk setiap MK terpilih:
  - Select/pilih kelas MK di halaman KRS
  - Verify MK terpilih (check UI state)
- Klik tombol submit/simpan KRS
- Wait untuk confirmation

### Task 5.3: Verify Submission
- Check response dari SIAKAD (success/error message)
- Verify KRS tersimpan (navigate ke halaman lihat KRS)
- Screenshot halaman KRS sebagai bukti
- Save screenshot ke `logs/screenshots/`

### Task 5.4: Handle Submission Errors
- Detect error messages dari SIAKAD
- Retry submit jika gagal (max 2 kali)
- Log detail error
- Jika tetap gagal, save partial result dan notify user

**Status:** [ ] Pending

---

## M6: Logging & Reporting

### Task 6.1: Setup Logging Infrastructure
- Configure loguru logger di `utils.py`:
  - Console output (colored)
  - File output ke `logs/bot.log`
  - Log level configurable dari `.env`
  - Format: `[timestamp] [level] [module] message`

### Task 6.2: Implement Activity Logging
- Log setiap major action:
  - Login attempt/result
  - Scraping progress
  - Course selection decisions
  - Submit progress/result
- Include timestamps

### Task 6.3: Generate Final Report
- Buat `reporter.py` (optional, bisa digabung di utils)
- Final summary output:
  ```
  ========================================
  BOT SIAKAD — HASIL AKHIR
  ========================================
  Status: SUCCESS / PARTIAL / FAILED
  
  MK Terambil:
  1. Sistem Terdistribusi (IF2228) - Kelas A - Senin 08:00-10:30 - 3 SKS
  2. Proyek Perangkat Lunak (IF2229) - Kelas B - Senin 13:00-15:30 - 3 SKS
  ...
  
  Total SKS: 23 / 23
  
  MK Gagal:
  - (none)
  ========================================
  ```

**Status:** [ ] Pending

---

## M7: Integration & Testing

### Task 7.1: End-to-End Integration Test
- Run full flow: login → scrape → select → submit
- Test dengan dry-run mode (tanpa submit sebenarnya)
- Verify semua module bekerja bersama

### Task 7.2: Error Handling Test
- Test login gagal (wrong credentials)
- Test network timeout
- Test MK kuota penuh
- Test semua kelas bentrok

### Task 7.3: Documentation
- Update README.md dengan:
  - Cara install
  - Cara konfigurasi
  - Cara menjalankan
  - Troubleshooting

### Task 7.4: Final Review & Cleanup
- Code review
- Remove debug code
- Optimize performance
- Final testing

**Status:** [ ] Pending

---

## Task Dependency Graph

```
M1 (Setup)
  │
  ├──→ M2 (Login)
  │      │
  │      ├──→ M3 (Scraping)
  │             │
  │             ├──→ M4 (Selection)
  │                    │
  │                    ├──→ M5 (Submit)
  │                           │
  │                           ├──→ M6 (Logging)
  │                                  │
  │                                  └──→ M7 (Integration)
```

## Timeline Estimate

| Milestone | Estimated Time |
|-----------|---------------|
| M1: Setup | 1 hour |
| M2: Login | 2 hours |
| M3: Scraping | 3 hours |
| M4: Selection | 2 hours |
| M5: Submit | 2 hours |
| M6: Logging | 1 hour |
| M7: Testing | 2 hours |
| **Total** | **~13 hours** |
