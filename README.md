<div align="center">

# BOT-SIAKAD

### Auto KRS Selection & War Mode

**SIAKAD Universitas Trunojoyo Madura — Semester 5, Target 23 SKS**

![Python](https://img.shields.io/badge/Python-3.11+-3776ab?style=flat-square&logo=python&logoColor=white)
![Playwright](https://img.shields.io/badge/Playwright-Automation-2ead33?style=flat-square&logo=playwright&logoColor=white)
![Tests](https://img.shields.io/badge/Tests-40_Passed-1c69d4?style=flat-square&logo=pytest&logoColor=white)

</div>

---

## Apa Ini?

Bot otomatis untuk **war KRS** di SIAKAD UTM. Bot login, buka halaman KRS, centang mata kuliah yang sudah ditentukan, lalu submit — semua otomatis dalam hitungan detik.

**Fitur utama:**
- **War mode** — polling sampai KRS buka, lalu langsung serang
- **Backtracking solver** — cari kombinasi kelas tanpa bentrok, bukan greedy
- **Preferred class** — kamu tentukan kelas mana yang mau diambil, bot ikuti persis
- **Auto-retry** — kalau gagal, coba lagi sampai 3 ronde
- **Cache jadwal** — jadwal di-scrape sebelumnya supaya saat war tidak buang waktu

---

## Target MK (23 SKS, 0 Bentrok)

| Hari | Jam | Mata Kuliah | Kelas | SKS |
|------|-----|-------------|-------|-----|
| Senin | 09:30-12:00 | Proyek Perangkat Lunak | IF 5A | 3 |
| Selasa | 09:30-12:00 | Proyek Sains Data | IF 5C | 3 |
| Selasa | 13:00-15:30 | Pengolahan Citra | IF 7B | 3 |
| Rabu | 07:00-09:30 | Basis Data III | IF 7A | 3 |
| Rabu | 09:30-12:00 | Pembelajaran Mesin | IF 5E | 3 |
| Kamis | 07:00-08:40 | Metodologi Penelitian | IF 5D | 2 |
| Kamis | 09:30-12:00 | Pemodelan Proses Bisnis | IF 7B | 3 |
| Kamis | 13:00-15:30 | Sistem Terdistribusi | IF 5C | 3 |
| | | **TOTAL** | | **23** |

---

## Instalasi (Pertama Kali)

### 1. Clone repo

```bash
git clone https://github.com/renocrypt/Bot-SIAKAD.git
cd Bot-SIAKAD
```

### 2. Buat virtual environment & install dependencies

```bash
python -m venv .venv

# Windows (CMD):
.venv\Scripts\activate

# Windows (PowerShell):
.venv\Scripts\Activate.ps1

# Linux/Mac:
source .venv/bin/activate
```

```bash
pip install -r requirements.txt
playwright install chromium
```

### 3. Buat file `.env`

Copy dari template:
```bash
copy .env.example .env
```

Isi dengan kredensial SIAKAD kamu:
```env
SIAKAD_USERNAME=240411100020
SIAKAD_PASSWORD=passwordkamu

HEADLESS=false
LOG_LEVEL=INFO
AUTO_CONFIRM=true
ALLOW_SUBMIT=true
USE_FALLBACK=false
```

> **PENTING:** `ALLOW_SUBMIT=true` dan `AUTO_CONFIRM=true` harus di-set agar bot bisa submit otomatis.

### 4. Verifikasi instalasi

```bash
python main.py --dry-run
```

Harus muncul: `Status: SUCCESS` dan `Total SKS: 23 / 23`.

---

## Panduan War KRS

### Persiapan Malam Sebelumnya

1. **Matikan auto-sleep laptop** — Settings > System > Power & Sleep > Sleep: **Never**
2. **Pastikan laptop tercharger**
3. **Test dry-run** untuk memastikan bot jalan:
   ```bash
   python main.py --dry-run --headed
   ```

### H-Day: Prosedur War

#### Jam 07:25 — Buka Terminal

```bash
cd "C:\Users\renos\Downloads\github coding\Bot-SIAKAD"
.venv\Scripts\activate
```

#### Jam 07:30 — Jalankan War Mode

```bash
python main.py --war --at 08:00 --headed
```

**Selesai.** Duduk dan pantau.

#### Apa yang Terjadi:

| Waktu | Bot Melakukan |
|-------|---------------|
| 07:30 | Login ke SIAKAD, load cache jadwal |
| 07:30-07:59 | Tidur (menunggu jam target) |
| 07:59 | Bangun, mulai polling halaman KRS tiap 3 detik |
| 08:00 (KRS buka) | Klik "Tambah Matakuliah" |
| +1 detik | Centang 8 checkbox MK |
| +2 detik | Klik "Tambah" |
| +3 detik | Verifikasi KRS, tampilkan hasil |
| Kalau gagal | Retry otomatis (maks 3 ronde) |

#### Hasil Sukses

Di terminal akan muncul:
```
Status: SUCCESS
Total SKS: 23 / 23
```

Cek juga di browser — halaman KRS harus menampilkan 8 MK kamu.

---

## CLI Reference

### Mode Utama

| Perintah | Fungsi |
|----------|--------|
| `python main.py --dry-run` | Test tanpa submit (aman) |
| `python main.py --run --auto-confirm --headed` | Submit langsung tanpa war |
| `python main.py --war --at 08:00 --headed` | War mode: tunggu jam 08:00 lalu serang |
| `python main.py --status` | Lihat report terakhir |

### Opsi War Mode

| Flag | Default | Keterangan |
|------|---------|------------|
| `--at HH:MM` | sekarang | Jam mulai war |
| `--led N` | 60 | Bangun N detik sebelum jam target |
| `--interval N` | 3.0 | Jeda polling dalam detik |
| `--max-minutes N` | 90 | Batas waktu polling |
| `--rounds N` | 3 | Maksimum ronde retry submit |
| `--fallback` | false | Izinkan MK cadangan kalau prioritas gagal |
| `--headed` | - | Tampilkan browser (rekomendasi untuk war) |
| `--headless` | - | Sembunyikan browser |
| `--refresh-schedules` | - | Scrape ulang jadwal (lambat, abaikan cache) |

### Utility Scripts

```bash
# Bangun cache jadwal (jalankan sebelum war)
python scripts/build_schedule_cache.py

# Simulasi selection tanpa browser
python scripts/simulate_selection.py

# Tampilkan jadwal dari cache
python scripts/show_schedules.py

# Recon mendalam halaman KRS
python scripts/recon_krs_page.py
```

---

## Struktur Proyek

```
Bot-SIAKAD/
├── bot/                        # Core automation
│   ├── cli.py                  # CLI + war mode entry
│   ├── config.py               # MK prioritas + preferred class
│   ├── login.py                # Login SIAKAD (handle MD5 hash)
│   ├── scraper.py              # Scrape KRS + jadwal kelas
│   ├── selector.py             # Backtracking solver (bukan greedy)
│   ├── submitter.py            # Submit KRS (alur 2-langkah)
│   ├── autodetect.py           # Auto-detect checkbox/tombol submit
│   ├── war.py                  # War mode: polling + auto-fire
│   ├── reporter.py             # Report generation
│   └── utils.py                # Jadwal parser, conflict check
│
├── config/
│   ├── selectors.json          # CSS selectors SIAKAD (dari recon)
│   └── selectors.example.json  # Template
│
├── scripts/
│   ├── build_schedule_cache.py # Pre-build cache jadwal
│   ├── simulate_selection.py   # Simulasi offline
│   ├── show_schedules.py       # Tampilkan jadwal cache
│   ├── recon.py                # Recon halaman SIAKAD
│   └── recon_krs_page.py       # Recon detail halaman KRS
│
├── ui/                         # Web dashboard (Flask)
├── tests/                      # 40 pytest tests
├── logs/                       # Runtime logs + screenshots
│
├── main.py                     # Entry point
├── requirements.txt            # Dependencies
├── .env                        # Kredensial (JANGAN commit)
└── .env.example                # Template .env
```

---

## Cara Kerja Bot

### Alur SIAKAD (Hasil Recon)

```
Login
  ↓
Halaman KRS
  ↓
Klik "Tambah Matakuliah" (btnProses)
  ↓
Halaman Daftar MK Ditawarkan
  - 130 checkbox (kodeMkul[])
  - Tabel: No | checkbox | Kelas | Mata Kuliah | Jadwal | SKS
  ↓
Centang checkbox MK yang dipilih
  ↓
Klik "Tambah" (btnAdd)
  ↓
Kembali ke Halaman KRS (MK sudah masuk)
```

### Selection Engine

Bot tidak pakai greedy first-fit (yang bisa gagal). Bot pakai **backtracking solver**:

1. Kumpulkan semua MK + kelas yang layak (ada kuota, ada jadwal)
2. Urutkan preferred class ke depan
3. Coba semua kombinasi, pangkas cabang mati (pruning)
4. Pilih kombinasi dengan SKS tertinggi + prioritas terbaik
5. Jamin 0 bentrok jadwal

### Cache Jadwal

Jadwal kelas di-scrape dari halaman detail (40 halaman) dan disimpan ke `logs/schedule_cache.json`. Saat war, bot pakai cache ini supaya tidak perlu buka 40 halaman — hemat ~2 menit.

---

## Konfigurasi MK

MK dan kelas yang diambil didefinisikan di `bot/config.py`:

```python
PRIORITY_COURSES = [
    {"code": "IF2229", "name": "Proyek Perangkat Lunak", "sks": 3, "preferred_class": "IF 5A"},
    {"code": "IF2231", "name": "Proyek Sains Data",      "sks": 3, "preferred_class": "IF 5C"},
    {"code": "IF2259", "name": "Pengolahan Citra",        "sks": 3, "preferred_class": "IF 7B"},
    {"code": "IF2258", "name": "Basis Data III",          "sks": 3, "preferred_class": "IF 7A"},
    {"code": "IF2230", "name": "Pembelajaran Mesin",      "sks": 3, "preferred_class": "IF 5E"},
    {"code": "IF2232", "name": "Metodologi Penelitian",   "sks": 2, "preferred_class": "IF 5D"},
    {"code": "IF2260", "name": "Pemodelan Proses Bisnis", "sks": 3, "preferred_class": "IF 7B"},
    {"code": "IF2228", "name": "Sistem Terdistribusi",    "sks": 3, "preferred_class": "IF 5C"},
]
```

Kalau mau ganti kelas, edit `preferred_class`. Kalau preferred penuh/bentrok, bot otomatis pilih kelas alternatif.

---

## Troubleshooting

<details>
<summary><b>Bot gagal login</b></summary>

- Cek username/password di `.env`
- Pastikan SIAKAD bisa diakses manual di browser
- Coba `python main.py --dry-run --headed` untuk lihat browser

</details>

<details>
<summary><b>"KRS belum terbuka" terus menerus</b></summary>

- Masa KRS memang belum dibuka, bot polling terus otomatis
- Pastikan `--max-minutes` cukup besar (default 90 menit)
- Kalau sudah lewat 90 menit, restart bot

</details>

<details>
<summary><b>MK tidak tercentang / checkbox not found</b></summary>

- Nama MK di SIAKAD mungkin beda sedikit dari config
- Jalankan `python scripts/recon_krs_page.py` untuk lihat daftar MK terbaru
- Update `bot/config.py` sesuai nama persis di SIAKAD

</details>

<details>
<summary><b>Internet putus di tengah war</b></summary>

- Jalankan ulang: `python main.py --war --headed`
- Bot akan login ulang dan lanjut dari awal

</details>

<details>
<summary><b>Mau submit manual saja</b></summary>

- Buka SIAKAD di browser biasa
- Halaman KRS > Tambah Matakuliah > centang manual > Tambah

</details>

---

## Testing

```bash
# Jalankan semua test (harus 40 pass)
python -m pytest -q

# Test selection engine saja
python -m pytest tests/test_selection.py -v

# Simulasi selection dengan data live
python scripts/simulate_selection.py
```

---

## Requirements

- Python 3.11+
- Windows / Linux / macOS
- Internet stabil
- Akun SIAKAD aktif

Dependencies:
```
playwright>=1.40.0
python-dotenv>=1.0.0
loguru>=0.7.0
pytest>=8.0.0
```

---

## Ringkasan Perintah untuk War Besok

```bash
# 1. Buka terminal di folder Bot-SIAKAD
cd "C:\Users\renos\Downloads\github coding\Bot-SIAKAD"

# 2. Aktifkan virtual environment
.venv\Scripts\activate

# 3. (Opsional) Verifikasi dulu
python main.py --dry-run

# 4. Jalankan war mode
python main.py --war --at 08:00 --headed

# 5. Duduk, pantau browser, tunggu "Status: SUCCESS"
```

---

<div align="center">

**Bot-SIAKAD** — Auto KRS Universitas Trunojoyo Madura

Made by Reno Syaelendra | 240411100020 | Teknik Informatika

</div>
