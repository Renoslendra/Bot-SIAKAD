# Product Requirements Document (PRD)

## Bot SIAKAD — Auto Course Selection

| Field | Detail |
|-------|--------|
| **Project Name** | Bot-SIAKAD |
| **Version** | 1.0.0 |
| **Platform** | SIAKAD Universitas Trunojoyo Madura |
| **URL** | `https://siakad.trunojoyo.ac.id/index.php?pModule=zabIzKI=&pSub=zabIzKI=&pAct=16DG2g==` |
| **Tech Stack** | Python + Playwright |
| **Target Semester** | Semester 5 |
| **Target SKS** | 23 SKS |

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

### 3.2 MK Cadangan (Fallback — tidak diambil kecuali diperlukan)

| Nama MK | Kode | SKS |
|---------|------|-----|
| Technopreneurship | IF2255 | 2 |
| Komputasi Numerik | IF2256 | 3 |
| Pemrograman Game | IF2257 | 3 |
| Basis Data III | IF2258 | 3 |

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
| FR-4.6 | Jika total SKS < 23 setelah semua MK di-check, laporkan sisa SKS |

### FR-5: Auto Submit KRS

| ID | Requirement |
|----|-------------|
| FR-5.1 | Bot menampilkan ringkasan MK yang akan di-submit sebelum eksekusi |
| FR-5.2 | User bisa confirm/cancel sebelum submit (optional, configurable) |
| FR-5.3 | Bot submit KRS secara otomatis ke SIAKAD |
| FR-5.4 | Bot verifikasi submit berhasil (cek response/confirmation) |
| FR-5.5 | Bot screenshot halaman KRS setelah submit sebagai bukti |

### FR-6: Logging & Reporting

| ID | Requirement |
|----|-------------|
| FR-6.1 | Semua aktivitas di-log ke console dan file (`logs/bot.log`) |
| FR-6.2 | Log berisi: timestamp, action, status (success/fail/warning), detail |
| FR-6.3 | Output summary: daftar MK berhasil diambil, total SKS, MK yang gagal + alasan |
| FR-6.4 | Screenshot disimpan di folder `logs/screenshots/` |

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

---

## 6. Constraints & Assumptions

### Constraints
- Bot hanya mengambil MK semester 5
- Bot tidak mengambil MK dari semester lain
- Target SKS adalah 23 (bukan 24)
- Bot tidak memodifikasi data di SIAKAD selain pengisian KRS

### Assumptions
- SIAKAD accessible via web browser
- User memiliki hak akses untuk mengisi KRS
- Structure HTML SIAKAD tidak berubah drastis
- MK semester 5 tersedia di SIAKAD saat bot dijalankan

---

## 7. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| SIAKAD ada CAPTCHA | Bot tidak bisa login | Prompt user untuk input CAPTCHA manual |
| SIAKAD ada rate limiting | Request di-block | Tambah delay antar request |
| HTML structure berubah | Scraping gagal | Modular scraper, mudah di-update |
| Kuota MK habis | MK tidak bisa diambil | Log warning, skip MK tersebut |
| Session expired mid-process | Submit gagal | Re-login otomatis jika session expired |
| Network timeout | Request gagal | Retry mechanism dengan exponential backoff |

---

## 8. Success Criteria

| Criteria | Definition |
|----------|-----------|
| Login berhasil | Bot masuk ke dashboard SIAKAD |
| Scraping berhasil | Semua MK semester 5 ter-scrape dengan data lengkap |
| Selection berhasil | MK terpilih tanpa bentrok, total SKS = 23 |
| Submit berhasil | KRS tersubmit dan terkonfirmasi di SIAKAD |
| Log lengkap | Semua aktivitas tercatat dengan jelas |
