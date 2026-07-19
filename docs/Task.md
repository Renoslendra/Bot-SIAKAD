# Task Breakdown & Milestones

## Bot SIAKAD — Auto Course Selection

---

## Milestone Overview

| Milestone | Description | Tasks |
|-----------|-------------|-------|
| M0 | DOM Recon & Preflight Gates | 4 tasks |
| M1 | Project Setup & Configuration | 6 tasks |
| M2 | Login Module | 4 tasks |
| M3 | Scraping Module | 5 tasks |
| M4 | Selection Engine | 5 tasks |
| M5 | Auto Submit Module | 5 tasks |
| M6 | Logging & Reporting | 3 tasks |
| M7 | Integration & Testing | 5 tasks |
| M8 | Hermes Agent Skill Integration | 5 tasks |

---

## Readiness Gates (WAJIB)

| Gate | Syarat lulus | Blocker untuk |
|------|--------------|---------------|
| **G-DOC** | PRD + Task + Guideline + flowchart + scaffolding | Mulai M1 coding |
| **G-SETUP** | deps install, `.env` filled, unit tests conflict pass | Live browser work |
| **G-RECON** | `selectors.json` valid dari recon live | Final M3/M5 |
| **G-DRY** | dry-run login→scrape→select sukses + report 23 SKS / partial jelas | M5 submit |
| **G-PROD** | user review report + `ALLOW_SUBMIT=true` + masa KRS buka | Production submit |
| **G-HERMES** | skill dry-run via Hermes OK | Cron/messaging optional |

---

## M0: DOM Recon & Preflight Gates

### Task 0.1: Fill Credentials (User)
- Copy `.env.example` → `.env`
- Isi `SIAKAD_USERNAME` dan `SIAKAD_PASSWORD`
- Biarkan `ALLOW_SUBMIT=false` sampai G-PROD
- Biarkan `USE_FALLBACK=false` (default sesuai preferensi user)

### Task 0.2: Live DOM Recon (Headed)
- Login manual/headed ke SIAKAD
- Catat selector untuk:
  - Username input, password input, login button
  - Login error message
  - CAPTCHA element (jika ada)
  - Navigasi ke halaman KRS
  - Container list MK / table rows
  - Field: kode, nama, SKS, kelas, hari, jam, kuota
  - Control pilih kelas (checkbox/radio/select)
  - Tombol simpan/submit KRS
  - Success/error message setelah submit
  - Area KRS existing (jika sudah ada MK terisi)
- Isi `selectors.json` dari template `selectors.example.json`
- Screenshot halaman login + KRS ke `logs/recon/` (jangan commit)

### Task 0.3: Validate Selector Map
- Pastikan semua key required di `selectors.json` terisi (bukan `TODO`)
- Review ulang jika ada iframe / multi-page KRS flow
- Document notes khusus SIAKAD di `logs/recon/NOTES.md` (opsional)

### Task 0.4: Preflight Sign-off
- Centang checklist di `PREFLIGHT.md`
- Jangan lanjut production submit sebelum G-DRY lulus

**Status:** [ ] Pending  
**Depends on:** scaffolding files exist (G-DOC)

---

## M1: Project Setup & Configuration

### Task 1.1: Initialize Project Structure
- Buat folder structure sesuai Guideline.md
- Pastikan `logs/`, `logs/screenshots/`, `logs/recon/` ada (atau dibuat runtime)
- Buat `requirements.txt` dengan dependencies:
  - `playwright`
  - `python-dotenv`
  - `loguru`
  - `pytest` (dev/test)
- Install dependencies: `pip install -r requirements.txt`
- Install Playwright browsers: `playwright install chromium`

### Task 1.2: Create `.env` Template
- [x] Scaffolding sudah ada: `.env.example`, `.gitignore`, `requirements.txt`
- Verify fields lengkap:
  ```
  SIAKAD_USERNAME=
  SIAKAD_PASSWORD=
  HEADLESS=true
  LOG_LEVEL=INFO
  AUTO_CONFIRM=false
  ALLOW_SUBMIT=false
  USE_FALLBACK=false
  ```

### Task 1.3: Create Configuration File
- Buat `config.py` berisi:
  - Priority list MK (nama, kode, SKS)
  - Fallback MK list
  - `TARGET_SKS = 23`
  - `USE_FALLBACK` dari env
  - `ALLOW_SUBMIT` dari env
  - SIAKAD URL + KRS URL
  - Timeout / retry / delay settings
  - Loader `selectors.json`

### Task 1.4: Create Utility Helpers
- Buat `utils.py` berisi:
  - Logger setup (loguru)
  - Time parser (`"Senin 08:00-10:30"` → structured)
  - Schedule conflict checker (exact boundary = no conflict)
  - SKS calculator
  - Project path helpers
  - JSON load/save helpers

### Task 1.5: Create Main Entry Point
- Buat `main.py` sebagai orchestrator:
  - Load config dari `.env`
  - Safety: block submit jika `ALLOW_SUBMIT=false`
  - Flow: login → scrape existing KRS → scrape available → select → (optional) submit → report
  - CLI: `--headless`, `--dry-run`, `--status`, `--auto-confirm`
  - Exit code: `0` success, `1` partial/fail

### Task 1.6: Unit Tests for Conflict Algorithm
- Buat `tests/test_schedule_conflict.py`
- Cover: overlap, no-overlap, beda hari, exact boundary, multi-slot
- Command: `pytest tests/ -q`
- Gate G-SETUP partial: unit test harus hijau

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
- Pakai selector dari `selectors.json` (bukan hardcode tebak-tebakan)
- URL: `https://siakad.trunojoyo.ac.id/index.php?pModule=zabIzKI=&pSub=zabIzKI=&pAct=16DG2g==`
- Wait untuk page load complete

### Task 3.2: Scrape Course Data
- Parse HTML halaman KRS
- Extract data untuk setiap MK:
  - Nama MK, Kode MK, SKS
  - Daftar kelas/section
  - Jadwal per kelas (hari, jam mulai, jam selesai)
  - Sisa kuota per kelas
- Store sebagai list of dictionaries (schema di Guideline)

### Task 3.3: Scrape Existing KRS (Idempotent)
- Scrape MK yang sudah terisi di KRS (jika ada)
- Export ke `logs/existing_krs.json`
- Feed ke selector sebagai already-selected

### Task 3.4: Filter Target Courses
- Filter scraped data: hanya MK di priority list (+ fallback jika enabled)
- Log MK ditemukan vs tidak ditemukan
- Log total MK dan total SKS tersedia

### Task 3.5: Save Scraped Data
- Export ke `logs/scraped_courses.json` + timestamp
- Print summary ke console

**Status:** [ ] Pending  
**Blocked by:** G-RECON (`selectors.json` valid)

---

## M4: Selection Engine

### Task 4.1: Implement Greedy Selection Algorithm
- Buat `selector.py`
- Input: available courses + existing KRS + priority + target SKS
- Skip MK yang sudah ada di existing KRS
- Untuk setiap MK di priority list:
  - Loop semua kelas:
    1. kuota > 0
    2. tidak bentrok dengan existing + newly selected
    3. total SKS + SKS MK <= 23
    4. lolos → pilih, break
  - Semua kelas gagal → skip + log reason

### Task 4.2: Implement Schedule Conflict Detection
- Function: `is_schedule_conflict(new_schedule, existing_schedules)`
- Beda hari → no conflict
- Same day overlap: `start < other_end AND end > other_start`
- Exact boundary (end == other_start) → **no conflict**
- Support multi-slot schedule per kelas jika ada

### Task 4.3: Implement SKS Tracking + Fallback Policy
- Track selected + total SKS
- Stop at 23
- Skip MK yang bikin > 23
- Jika priority habis & total < 23 & `USE_FALLBACK=true` → process fallback list
- Else report remaining SKS

### Task 4.4: Generate Selection Report
- Save `logs/selection_report.json`
- Include: selected, skipped(+reason), existing, total_sks, status
- Print human summary ke console (untuk Hermes)

### Task 4.5: Selection Unit Tests (no browser)
- Test greedy with mock course data
- Test skip existing
- Test fallback on/off
- Test SKS cap

**Status:** [ ] Pending

---

## M5: Auto Submit Module

### Task 5.1: Safety Lock + Pre-Submit Confirmation
- Buat `submitter.py`
- Abort jika `ALLOW_SUBMIT=false` (default)
- Abort jika `--dry-run`
- Tampilkan ringkasan MK yang akan di-submit
- Prompt `Submit KRS? (y/n)` kecuali `AUTO_CONFIRM=true` / `--auto-confirm`

### Task 5.2: Submit KRS to SIAKAD
- Hanya submit MK **baru** (bukan yang sudah existing)
- Select kelas via `selectors.json`
- Verify UI state selected
- Klik simpan/submit
- Wait confirmation

### Task 5.3: Verify Submission
- Check success/error message
- Re-scrape KRS untuk verifikasi
- Screenshot before/after ke `logs/screenshots/`

### Task 5.4: Handle Submission Errors
- Detect SIAKAD error messages
- Retry max 2
- Partial result save + notify

### Task 5.5: Production Gate Check
- Hard-require G-DRY passed (documented in PREFLIGHT)
- Log warning jika total SKS < 23 sebelum submit

**Status:** [ ] Pending  
**Blocked by:** G-DRY

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

### Task 7.1: End-to-End Dry-run Integration Test
- Full flow: login → scrape existing → scrape available → select → report
- `--dry-run` must never submit
- Verify modules together

### Task 7.2: Error Handling Test
- Wrong credentials
- Network timeout
- Kuota penuh
- Semua kelas bentrok
- Missing selectors.json
- `ALLOW_SUBMIT=false` blocks submit

### Task 7.3: Idempotent Re-run Test
- Jalankan dry-run 2x
- Pastikan MK existing tidak dipilih ulang
- Pastikan report konsisten

### Task 7.4: Documentation
- README: install, config, run modes, Hermes, troubleshooting, safety locks

### Task 7.5: Final Review & Cleanup
- Code review, remove debug, performance, final dry-run sign-off

**Status:** [ ] Pending

---

## M8: Hermes Agent Skill Integration

### Task 8.1: Create Hermes Skill Structure
- Buat folder `hermes-skill/` (atau `.hermes/skills/bot-siakad/` sesuai install target)
- Buat `SKILL.md` mengikuti format Hermes/agentskills.io:
  - YAML frontmatter: `name`, `description`, `version`, `author`
  - Body: kapan skill dipakai, cara run, safety notes, examples
- Skill name: `bot-siakad`
- Description harus include trigger phrases: "ambil KRS", "siakad", "course selection", "dry-run KRS"

### Task 8.2: Implement Skill Commands
- Document & support command modes di skill:
  | Mode | Command | Deskripsi |
  |------|---------|-----------|
  | run | `python main.py --auto-confirm` | Full run + submit |
  | dry-run | `python main.py --dry-run` | Login + scrape + select, tanpa submit |
  | status | `python main.py --status` | Baca report terakhir |
  | report | baca `logs/selection_report.json` | Ringkas hasil terakhir |
- Skill instruction: Hermes **wajib** pakai tool `terminal` untuk eksekusi bot
- Jangan pakai Hermes browser tools untuk core automation

### Task 8.3: CLI Hardening for Hermes
- Pastikan `main.py` output machine/human friendly summary di stdout
- Exit codes konsisten (`0` / `1`)
- Support env flags yang sudah ada di `.env`
- Pastikan path kerja: skill set cwd ke root project Bot-SIAKAD
- Handle long-running process (KRS bot bisa >1 menit)

### Task 8.4: Optional Cron + Messaging
- Document cara schedule via Hermes cron, contoh:
  - "Setiap hari jam 08:00 saat masa KRS, jalankan dry-run dulu"
  - "Saat jam buka KRS, jalankan run mode"
- Document delivery hasil ke Telegram/Discord (via Hermes gateway) jika user enable
- Safety: default cron = dry-run dulu, submit tetap butuh confirm kecuali `AUTO_CONFIRM=true`

### Task 8.5: Hermes Integration Testing
- Test skill load di Hermes (`/skills` atau skill search)
- Test natural language: "tolong dry-run ambil KRS semester 5"
- Test slash: `/bot-siakad dry-run`
- Test report mode setelah bot pernah dijalankan
- Test failure path: wrong cwd, missing `.env`, login fail
- Update README.md section "Hermes Agent Integration"

**Status:** [ ] Pending

---

## Task Dependency Graph

```
G-DOC (docs + scaffolding)
  │
  ├──→ M1 (Setup + unit tests)
  │      │
  │      ├──→ M0 (DOM recon + selectors.json)  [needs .env]
  │      │      │
  │      │      └──→ G-RECON
  │      │
  │      ├──→ M2 (Login)
  │      │      │
  │      │      ├──→ M3 (Scraping)  [needs G-RECON]
  │      │      │      │
  │      │      │      ├──→ M4 (Selection + tests)
  │      │      │      │      │
  │      │      │      │      ├──→ G-DRY
  │      │      │      │      │      │
  │      │      │      │      │      ├──→ M5 (Submit) [needs G-PROD]
  │      │      │      │      │      │
  │      │      │      │      │      ├──→ M6 (Logging)
  │      │      │      │      │      │
  │      │      │      │      │      └──→ M7 (Integration)
  │      │      │      │      │             │
  │      │      │      │      │             └──→ M8 (Hermes Skill)
```

## Timeline Estimate

| Milestone | Estimated Time |
|-----------|---------------|
| M0: Recon & preflight | 1–2 hours |
| M1: Setup + unit tests | 1.5 hours |
| M2: Login | 2 hours |
| M3: Scraping | 3 hours |
| M4: Selection | 2.5 hours |
| M5: Submit | 2 hours |
| M6: Logging | 1 hour |
| M7: Testing | 2 hours |
| M8: Hermes Skill | 2 hours |
| **Total** | **~17–18 hours** |

## Definition of Done (Project)

- [ ] Unit tests conflict + selection mock lulus
- [ ] `selectors.json` dari recon live
- [ ] `python main.py --dry-run` menghasilkan report valid
- [ ] Re-run dry-run idempotent
- [ ] Production submit hanya dengan safety locks
- [ ] README + PREFLIGHT terisi
- [ ] (Optional) Hermes skill dry-run works
