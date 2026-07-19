# Product Requirements Document (PRD)

## Bot SIAKAD — Auto Course Selection

| Field | Detail |
|-------|--------|
| **Project Name** | Bot-SIAKAD |
| **Version** | 1.0.0 |
| **Platform** | SIAKAD Universitas Trunojoyo Madura |
| **URL** | `https://siakad.trunojoyo.ac.id/index.php?pModule=zabIzKI=&pSub=zabIzKI=&pAct=16DG2g==` |
| **Tech Stack** | Python + Playwright + Hermes Agent Skill |
| **Target Semester** | Semester 5 |
| **Target SKS** | 23 SKS |
| **Hermes Integration** | Skill wrapper + CLI + optional cron |

---

## 1. Background & Problem Statement

Mahasiswa semester 5 perlu mengambil 8 mata kuliah (23 SKS) secara manual melalui SIAKAD. Proses ini memakan waktu dan berisiko kehabisan kuota jika terlambat. Dibutuhkan bot yang dapat secara otomatis memilih dan mendaftarkan mata kuliah sesuai prioritas, tanpa jadwal bentrok, hingga mencapai target SKS.

---

## 2. Goals & Objectives

| Goal | Description |
|------|-------------|
| **G1** | Otomatis login ke SIAKAD |
| **G2** | Scraping daftar mata kuliah + jadwal + kuota |
| **G3** | Memilih mata kuliah sesuai priority list tanpa bentrok |
| **G4** | Mencapai target 23 SKS |
| **G5** | Auto-submit KRS |
| **G6** | Logging semua aktivitas dan hasil |
| **G7** | Bisa dijalankan via Hermes Agent (skill + CLI + Telegram/Discord) |
| **G8** | Support dry-run, status check, dan optional cron scheduling |

---

## 3. Target Mata Kuliah (Semester 5 — 23 SKS)

### 3.1 MK yang Diambil (Priority Order)

| No | Nama MK | Kode | SKS | Tipe |
|----|---------|------|-----|------|
| 1 | Sistem Terdistribusi | IF2228 | 3 | Wajib |
| 2 | Proyek Perangkat Lunak | IF2229 | 3 | Wajib |
| 3 | Pembelajaran Mesin | IF2230 | 3 | Wajib |
| 4 | Proyek Sains Data | IF2231 | 3 | Wajib |
| 5 | Metodologi Penelitian | IF2232 | 2 | Wajib |
| 6 | Pemodelan Proses Bisnis | IF2260 | 3 | Pilihan |
| 7 | Keamanan Data & Aplikasi | IF2254 | 3 | Pilihan |
| 8 | Pengolahan Citra | IF2259 | 3 | Pilihan |

**Total: 23 SKS**

### 3.2 MK Cadangan (Fallback)

| Nama MK | Kode | SKS |
|---------|------|-----|
| Technopreneurship | IF2255 | 2 |
| Komputasi Numerik | IF2256 | 3 |
| Pemrograman Game | IF2257 | 3 |
| Basis Data III | IF2258 | 3 |

### 3.3 Fallback Policy (WAJIB DIPATUHI)

| Rule | Value |
|------|-------|
| Default | `USE_FALLBACK=false` |
| Target utama | 8 MK di section 3.1 saja (23 SKS) |
| Fallback dipakai | Hanya jika `USE_FALLBACK=true` **DAN** total SKS dari priority < 23 setelah selection |
| Semester lain | **Dilarang** — bot tidak pernah ambil MK di luar list semester 5 di config |
| Preferensi user | Fokus semester 5; fallback hanya safety net opsional |

---

## 4. Functional Requirements

### FR-1: Authentication

| ID | Requirement |
|----|-------------|
| FR-1.1 | Bot membaca credentials dari file `.env` (SIAKAD_USERNAME, SIAKAD_PASSWORD) |
| FR-1.2 | Bot melakukan login otomatis ke SIAKAD |
| FR-1.3 | Bot menyimpan session cookies untuk request selanjutnya |
| FR-1.4 | Bot menangani login gagal dengan retry (max 3 kali) dan notifikasi error |
| FR-1.5 | Bot menangani CAPTCHA jika ada (prompt user untuk input manual) |

### FR-2: Scraping Mata Kuliah

| ID | Requirement |
|----|-------------|
| FR-2.1 | Bot navigate ke halaman KRS/pengisian KRS setelah login |
| FR-2.2 | Bot scrape semua mata kuliah yang tersedia untuk semester 5 |
| FR-2.3 | Data yang di-scrape: Nama MK, Kode MK, SKS, Kelas/Section, Jadwal (hari + jam), Sisa Kuota |
| FR-2.4 | Bot menyimpan hasil scraping ke JSON/CSV untuk debugging |
| FR-2.5 | Bot memfilter hanya MK yang ada di priority list |

### FR-3: Schedule Conflict Detection

| ID | Requirement |
|----|-------------|
| FR-3.1 | Bot menyimpan jadwal semua MK yang sudah dipilih |
| FR-3.2 | Bot mendeteksi bentrok jadwal: hari sama DAN waktu overlap |
| FR-3.3 | Untuk MK yang sama dengan multiple kelas, bot mencoba semua kelas |
| FR-3.4 | Bot memilih kelas pertama yang tidak bentrok dan masih ada kuota |
| FR-3.5 | Jika semua kelas bentrok/penuh, bot skip MK tersebut dan log warning |

### FR-4: Course Selection Algorithm

| ID | Requirement |
|----|-------------|
| FR-4.1 | Algoritma greedy berdasarkan priority list (urutan = prioritas) |
| FR-4.2 | Untuk setiap MK, cek semua kelas/section |
| FR-4.3 | Urutan pengecekan: kuota tersedia → jadwal tidak bentrok → SKS tidak melebihi 23 |
| FR-4.4 | Jika MK terpilih, tambahkan ke daftar KRS dan update jadwal terisi |
| FR-4.5 | Stop jika total SKS mencapai 23 |
| FR-4.6 | Jika total SKS < 23 setelah priority list habis: jika `USE_FALLBACK=true` coba fallback list; else laporkan sisa SKS |
| FR-4.7 | Exact boundary waktu (contoh 10:30 end & 10:30 start) = **tidak bentrok** |
| FR-4.8 | Satu MK hanya boleh dipilih 1 kelas (tidak double-enroll) |

### FR-4B: Idempotent Re-run (KRS Existing)

| ID | Requirement |
|----|-------------|
| FR-4B.1 | Sebelum selection, bot scrape **KRS yang sudah terisi** (jika ada) |
| FR-4B.2 | MK yang sudah ada di KRS → skip (anggap sudah diambil) |
| FR-4B.3 | Jadwal MK existing dimasukkan ke `taken_schedules` untuk cek bentrok |
| FR-4B.4 | Bot hanya menambahkan MK yang masih missing dari priority list |
| FR-4B.5 | Mode `--status` menampilkan KRS existing + report terakhir bot |
| FR-4B.6 | Bot tidak menghapus MK yang sudah ada di KRS kecuali flag eksplisit (default: tidak hapus) |

### FR-5: Auto Submit KRS

| ID | Requirement |
|----|-------------|
| FR-5.1 | Bot menampilkan ringkasan MK yang akan di-submit sebelum eksekusi |
| FR-5.2 | User bisa confirm/cancel sebelum submit (optional, configurable) |
| FR-5.3 | Bot submit KRS secara otomatis ke SIAKAD |
| FR-5.4 | Bot verifikasi submit berhasil (cek response/confirmation) |
| FR-5.5 | Bot screenshot halaman KRS setelah submit sebagai bukti |
| FR-5.6 | Production submit **hanya** diizinkan jika preflight checklist lulus (lihat section 10) |
| FR-5.7 | Default production path: dry-run dulu → review → baru run submit |

### FR-6: Logging & Reporting

| ID | Requirement |
|----|-------------|
| FR-6.1 | Semua aktivitas di-log ke console dan file (`logs/bot.log`) |
| FR-6.2 | Log berisi: timestamp, action, status (success/fail/warning), detail |
| FR-6.3 | Output summary: daftar MK berhasil diambil, total SKS, MK yang gagal + alasan |
| FR-6.4 | Screenshot disimpan di folder `logs/screenshots/` |

### FR-7: Hermes Agent Integration

| ID | Requirement |
|----|-------------|
| FR-7.1 | Bot tetap standalone: bisa dijalankan lewat `python main.py` tanpa Hermes |
| FR-7.2 | Tersedia Hermes skill `bot-siakad` di folder `hermes-skill/` (SKILL.md + scripts) |
| FR-7.3 | Skill bisa dipanggil via slash command `/bot-siakad` atau natural language di Hermes |
| FR-7.4 | Skill mendukung mode: `run`, `dry-run`, `status`, `report` |
| FR-7.5 | Hermes menjalankan bot lewat tool `terminal` (bukan browser tools Hermes) |
| FR-7.6 | Credentials dibaca dari `.env` project (bukan di-hardcode di skill) |
| FR-7.7 | Output bot (summary + path screenshot) dikembalikan ke user di chat Hermes |
| FR-7.8 | Optional: support cron scheduling lewat Hermes (`cronjob`) untuk auto-run saat KRS buka |
| FR-7.9 | Optional: delivery notifikasi hasil KRS ke Telegram/Discord via Hermes gateway |

### FR-8: DOM Recon & Selector Map (Pre-Build Gate)

| ID | Requirement |
|----|-------------|
| FR-8.1 | Sebelum implement scraper/submit final, wajib ada file `selectors.json` hasil recon |
| FR-8.2 | Selector map minimal cover: login form, login button, error login, CAPTCHA (jika ada), menu/nav KRS, table/list MK, kelas, jadwal, kuota, checkbox/select MK, tombol simpan/submit, pesan sukses/gagal |
| FR-8.3 | Recon dilakukan via headed browser + dry-run login (bukan guess selector) |
| FR-8.4 | Jika HTML SIAKAD berubah, update `selectors.json` dulu baru ubah logic |
| FR-8.5 | Simpan sample HTML anonymized ke `logs/recon/` (opsional, jangan commit credentials) |

---

## 5. Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| NFR-1 | Bot harus berjalan di Windows (PowerShell compatible) |
| NFR-2 | Bot menggunakan Playwright (Python) sebagai browser automation |
| NFR-3 | Bot support headless mode (tanpa buka browser) dan headed mode (untuk debugging) |
| NFR-4 | Bot harus menangani network timeout dengan retry mechanism |
| NFR-5 | Credentials tidak boleh di-hardcode (gunakan `.env`) |
| NFR-6 | Bot harus bisa dijalankan berulang kali (idempotent) |
| NFR-7 | Response time: bot harus cepat, terutama saat scraping dan submit |
| NFR-8 | Hermes skill harus follow format agentskills.io / Hermes SKILL.md |
| NFR-9 | Core bot tidak depend ke Hermes runtime (Hermes opsional, bukan required) |
| NFR-10 | CLI bot support flags: `--dry-run`, `--status`, `--headless`, `--auto-confirm` |
| NFR-11 | Unit test wajib untuk schedule conflict algorithm (tanpa browser) |
| NFR-12 | Production submit diblokir kecuali `ALLOW_SUBMIT=true` di `.env` (safety lock) |
| NFR-13 | Semua path file relative ke project root; Hermes skill wajib set cwd ke project root |

---

## 6. Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│  USER INTERFACE                                              │
│  • CLI: python main.py                                       │
│  • Hermes CLI: /bot-siakad run                               │
│  • Telegram/Discord (via Hermes gateway)                     │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│  HERMES SKILL LAYER (optional wrapper)                       │
│  hermes-skill/SKILL.md                                       │
│  • Parse user intent (run / dry-run / status / report)       │
│  • Call terminal: python main.py [flags]                     │
│  • Relay summary + screenshots back to user                  │
│  • Optional: cron schedule                                   │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│  CORE BOT (Python + Playwright) — standalone                 │
│  main.py → login → scrape → select → submit → report         │
└─────────────────────────────────────────────────────────────┘
```

**Prinsip desain:** Core bot independent. Hermes hanya remote control + notifikasi.

---

## 7. Constraints & Assumptions

### Constraints
- Bot hanya mengambil MK semester 5 yang ada di `config.py`
- Bot tidak mengambil MK dari semester lain
- Target SKS adalah 23 (bukan 24)
- Bot tidak menghapus MK existing di KRS (default)
- Bot tidak memodifikasi data di SIAKAD selain pengisian KRS
- Hermes browser tools **tidak** dipakai untuk core automation (Playwright di core bot)
- Submit production butuh `ALLOW_SUBMIT=true` + confirm/`AUTO_CONFIRM`

### Assumptions
- SIAKAD accessible via web browser
- User memiliki hak akses untuk mengisi KRS pada masa KRS
- Structure HTML SIAKAD tidak berubah drastis setelah recon
- MK semester 5 tersedia di SIAKAD saat bot dijalankan
- User sudah install Hermes Agent jika ingin fitur skill/messaging/cron
- Python + Playwright tersedia di environment yang dipakai Hermes terminal
- User mengisi `.env` sebelum run

### Open Items (wajib diselesaikan di M0, sebelum production)
| Item | Owner | Status gate |
|------|-------|-------------|
| DOM recon + `selectors.json` | Developer + login live | Blocker M3/M5 |
| Credentials `.env` | User | Blocker all live tests |
| Jadwal buka KRS (opsional cron) | User | Blocker M8 cron only |
| Konfirmasi `USE_FALLBACK` | User (default false) | Config only |

---

## 8. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| SIAKAD ada CAPTCHA | Bot tidak bisa login | Prompt user untuk input CAPTCHA manual; headed mode |
| SIAKAD ada rate limiting | Request di-block | Delay antar request (`ACTION_DELAY`) |
| HTML structure berubah | Scraping gagal | `selectors.json` terpusat + recon ulang |
| Kuota MK habis | MK tidak bisa diambil | Log warning, skip MK; optional fallback |
| Session expired mid-process | Submit gagal | Re-login otomatis jika session expired |
| Network timeout | Request gagal | Retry + exponential backoff |
| Hermes terminal path salah | Skill gagal run bot | Skill set cwd + verify `main.py` exists |
| Headless CAPTCHA di remote chat | Tidak bisa input CAPTCHA | Force headed / dry-run local dulu |
| Credential bocor via chat | Security risk | Password hanya di `.env` lokal |
| Double submit / re-run | KRS rusak / error | Idempotent: baca KRS existing dulu |
| Accidental production submit | KRS terisi tanpa review | `ALLOW_SUBMIT=false` default + dry-run first |

---

## 9. Success Criteria

| Criteria | Definition |
|----------|-----------|
| Login berhasil | Bot masuk ke dashboard SIAKAD |
| Scraping berhasil | Semua MK priority ter-scrape (kode, kelas, jadwal, kuota) |
| Selection berhasil | MK terpilih tanpa bentrok, total SKS = 23 (atau partial jelas alasannya) |
| Submit berhasil | KRS tersubmit dan terkonfirmasi di SIAKAD |
| Re-run aman | Menjalankan bot 2x tidak double-enroll MK yang sama |
| Log lengkap | Semua aktivitas tercatat dengan jelas |
| Standalone run | `python main.py --dry-run` berjalan tanpa Hermes |
| Unit test conflict | Test conflict algorithm lulus |
| Hermes skill run | `/bot-siakad dry-run` berhasil (setelah M8) |
| Report relay | Summary hasil KRS tampil di Hermes chat (setelah M8) |

---

## 10. Preflight Checklist (100% Ready Gate)

### 10.1 Docs Ready (planning)
- [x] PRD.md lengkap
- [x] Task.md lengkap
- [x] Guideline.md lengkap
- [x] flowchart.html ada
- [x] Fallback policy jelas
- [x] Re-run / idempotent policy jelas
- [x] Hermes integration spec jelas

### 10.2 Scaffolding Ready (sebelum coding core)
- [x] `.env.example`
- [x] `.gitignore`
- [x] `requirements.txt`
- [x] `README.md`
- [x] `hermes-skill/SKILL.md` draft
- [x] `selectors.example.json` template
- [x] `PREFLIGHT.md` / readiness gate

### 10.3 Live Ready (sebelum dry-run)
- [ ] User mengisi `.env` (username/password)
- [ ] `pip install -r requirements.txt` + `playwright install chromium`
- [ ] M0 DOM recon selesai → `selectors.json` terisi
- [ ] Unit test conflict lulus
- [ ] Dry-run login + scrape + select sukses

### 10.4 Production Ready (sebelum submit beneran)
- [ ] Dry-run menghasilkan 23 SKS / partial acceptable dengan alasan jelas
- [ ] User review selection report
- [ ] `ALLOW_SUBMIT=true` diset sadar
- [ ] Confirm / `AUTO_CONFIRM` diset sadar
- [ ] Screenshot evidence path ready
- [ ] Masa KRS sedang buka

**Aturan:** Coding boleh mulai setelah 10.1 + 10.2. Production submit hanya setelah 10.3 + 10.4.

---

## 11. Execution Phases (Safe Order)

| Phase | What | Submit? |
|-------|------|---------|
| P0 | Docs + scaffolding | No |
| P1 | M1 setup + unit tests conflict | No |
| P2 | M0 recon selectors (headed login) | No |
| P3 | M2–M4 login/scrape/select + dry-run | No |
| P4 | M5 submit (local confirm) | Yes (controlled) |
| P5 | M6–M7 polish + tests | Optional |
| P6 | M8 Hermes skill + optional cron | Optional |
