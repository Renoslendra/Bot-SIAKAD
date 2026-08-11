<div align="center">

# BOT-SIAKAD

### Automasi KRS SIAKAD Universitas Trunojoyo Madura

![Python](https://img.shields.io/badge/Python-3.11+-3776ab?style=flat-square&logo=python&logoColor=white)
![Playwright](https://img.shields.io/badge/Playwright-Automation-2ead33?style=flat-square&logo=playwright&logoColor=white)
![Tests](https://img.shields.io/badge/Tests-44_Passed-1c69d4?style=flat-square&logo=pytest&logoColor=white)

</div>

---

## Ringkasan

Bot ini mengotomatisasi alur KRS yang sama dengan UI resmi SIAKAD: login, membuka **Kartu Rencana Studi**, membuka **Tambah Matakuliah**, membuka **Paket Semester 5**, memilih kelas, kemudian submit dan memverifikasi hasil akhir KRS.

Bot tidak membypass aturan SIAKAD. Kuota kelas, prasyarat, batas SKS, dan keputusan akhir tetap ditentukan server SIAKAD.

## Fitur yang Sudah Diuji Live

- Login SIAKAD dengan alur hash MD5 halaman login.
- Navigasi ke Kartu Rencana Studi dan tombol `Tambah Matakuliah`.
- Membuka accordion `Paket Semester 5` sebelum memilih kelas.
- Memilih seluruh mata kuliah dalam **satu batch**, bukan submit satu per satu.
- Pencocokan checkbox dengan **nama mata kuliah + kelas persis**, mencegah MK bernama mirip tertukar.
- Membaca hasil respons SIAKAD per mata kuliah, termasuk `Kelas sudah penuh` dan kegagalan prasyarat.
- Verifikasi ulang KRS setelah submit; bot tidak menyatakan sukses bila KRS belum tersimpan.
- Cache jadwal dan solver bebas bentrok.
- War mode dan Windows Scheduled Task.

---

## Alur Submit SIAKAD

```text
Login
  -> Kartu Rencana Studi
  -> Tambah Matakuliah
  -> Paket Semester 5
  -> centang seluruh MK target dalam satu batch
  -> Tambah
  -> baca hasil berhasil/gagal dari SIAKAD
  -> verifikasi KRS akhir
```

Halaman pilihan MK SIAKAD berisi 130 checkbox dengan tabel:

```text
No | checkbox | Kelas | Mata Kuliah | Jadwal Kuliah | Jadwal Ujian | SKS | Keterangan
```

## Target Planning Saat Ini

| Kode | Mata Kuliah | Kelas | Jadwal | SKS |
|---|---|---|---|---:|
| IF2229 | Proyek Perangkat Lunak | IF 5A | Senin 09:30-12:00 | 3 |
| IF2231 | Proyek Sain Data | IF 5C | Selasa 09:30-12:00 | 3 |
| IF2259 | Pengolahan Citra | IF 7B | Selasa 13:00-15:30 | 3 |
| IF2258 | Basis Data III | IF 7A | Rabu 07:00-09:30 | 3 |
| IF2230 | Pembelajaran Mesin | IF 5E | Rabu 09:30-12:00 | 3 |
| IF2232 | Metodologi Penelitian | IF 5D | Kamis 07:00-08:40 | 2 |
| IF2260 | Pemodelan Proses Bisnis | IF 7B | Kamis 09:30-12:00 | 3 |
| IF2228 | Sistem Terdistribusi | IF 5C | Kamis 13:00-15:30 | 3 |
| | **Total planning** | | | **23** |

### Hasil Uji Server Terbaru

Target di atas adalah planning jadwal bebas bentrok, **bukan jaminan dapat diambil**. Submit live ke SIAKAD telah membuktikan server dapat menolak MK karena aturan berikut:

| Mata Kuliah | Hasil server saat diuji |
|---|---|
| IF2228, IF2229, IF2230, IF2231, IF2232, IF2259, IF2260 | Kelas pilihan saat itu penuh |
| IF2258 Basis Data III | Prasyarat `IF2228 Sistem Terdistribusi` belum tercatat sebagai mata kuliah yang pernah diambil |
| IF2257 Pemrograman Game | Prasyarat `IF2251 Grafika Komputer` belum tercatat |

Prasyarat tidak dapat diatasi dengan memilih mata kuliah prasyarat dalam batch yang sama. Selalu gunakan hasil respons SIAKAD sebagai sumber kebenaran.

---

## Instalasi

```powershell
git clone https://github.com/Renoslendra/Bot-SIAKAD.git
cd Bot-SIAKAD

python -m venv .venv
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
python -m playwright install chromium

Copy-Item .env.example .env
```

Isi `.env` dengan akun SIAKAD sendiri:

```env
SIAKAD_USERNAME=nim_kamu
SIAKAD_PASSWORD=password_kamu

HEADLESS=false
LOG_LEVEL=INFO
ALLOW_SUBMIT=false
AUTO_CONFIRM=false
USE_FALLBACK=false
```

`ALLOW_SUBMIT` dan `AUTO_CONFIRM` harus tetap `false` sampai kamu benar-benar menyetujui submit nyata.

## Perintah Utama

| Perintah | Fungsi |
|---|---|
| `python main.py --dry-run --headed` | Login, scrape, dan selection tanpa submit |
| `python main.py --status` | Tampilkan report terakhir |
| `python main.py --run --auto-confirm --headed` | Submit nyata sekarang |
| `python main.py --war --at 08:00 --lead 0 --headed` | Mulai war pada jam target |
| `python scripts/audit_war.py` | Audit live tanpa submit: buka Paket Semester 5 dan cek checkbox target |
| `python scripts/build_schedule_cache.py` | Bangun ulang cache jadwal |

## War KRS Manual

Jalankan sekitar 07:55. Dengan `--lead 0`, bot tidak mulai alur submit sebelum jam 08:00.

```powershell
cd "C:\path\ke\Bot-SIAKAD"
.venv\Scripts\python.exe main.py --war --at 08:00 --lead 0 --headed
```

Saat war:

1. Gunakan satu instance bot dan satu sesi SIAKAD.
2. Jangan menjalankan banyak tab atau banyak request paralel.
3. Jangan klik browser bot ketika proses berjalan.
4. Gunakan koneksi stabil; matikan VPN, download, streaming, dan cloud sync.
5. Cek hasil akhir pada KRS, bukan hanya log klik tombol.

## Windows Scheduled Task

Untuk Windows, wrapper tersedia di:

```text
scripts\run_war_scheduled.ps1
```

Wrapper menjalankan:

```powershell
.venv\Scripts\python.exe main.py --war --at 08:00 --lead 0 --headless
```

Task yang dibuat hanya tersimpan di komputer lokal, **tidak ikut ke GitHub**. Agar task dapat berjalan otomatis:

- Laptop menyala dan tidak sleep/hibernate.
- Windows tetap login pada user yang mendaftarkan task.
- Charger dan internet aktif.
- Jangan `Sign out`, restart, atau menjalankan task kedua.

Log wrapper otomatis disimpan di:

```text
logs\scheduled_war.log
```

## Verifikasi Hasil

Setelah submit, cek dua sumber berikut:

```text
logs\selection_report.json
logs\existing_krs.json
```

Kondisi sukses hanya bila:

```text
KRS existing > 0 MK
total_sks sesuai hasil yang benar-benar disimpan server
```

Contoh respons gagal yang akan direkam bot:

```text
SIAKAD menolak IF2229: Kelas sudah penuh.
SIAKAD menolak IF2258: Anda belum mengambil matakuliah prasyarat IF2228.
```

## Testing

```powershell
python -m pytest -q
python scripts/simulate_selection.py
python scripts/audit_war.py
```

Status saat README ini diperbarui: **44 test lulus**. Audit live memverifikasi alur Paket Semester 5 serta pencocokan dan pemilihan 8 checkbox target, tanpa mengirim submit.

## Struktur Proyek

```text
bot/
  cli.py              # CLI
  login.py            # Login SIAKAD
  scraper.py          # KRS dan jadwal
  selector.py         # Solver kelas bebas bentrok
  submitter.py        # Batch submit dan parser respons SIAKAD
  war.py              # War mode
  autodetect.py       # Deteksi kontrol halaman KRS

scripts/
  audit_war.py              # Audit pre-submit
  build_schedule_cache.py   # Cache jadwal
  run_war_scheduled.ps1     # Wrapper Scheduled Task Windows
  simulate_selection.py     # Simulasi offline

logs/                 # Report, screenshot, dan log runtime (gitignored)
tests/                # Test suite
```

---

<div align="center">

Bot-SIAKAD menggunakan UI resmi SIAKAD dan tidak dapat melewati kuota atau prasyarat yang diberlakukan server.

</div>
