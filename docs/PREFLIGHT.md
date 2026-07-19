# PREFLIGHT — Readiness Gate (100%)

Gunakan checklist ini sebelum dry-run dan production submit.

---

## Gate A — Docs & Scaffolding

- [x] `PRD.md` lengkap
- [x] `Task.md` lengkap
- [x] `Guideline.md` lengkap
- [x] `flowchart.html` ada
- [x] `.env.example` ada
- [x] `.gitignore` ada
- [x] `requirements.txt` ada
- [x] `README.md` ada
- [x] `selectors.example.json` ada
- [x] `hermes-skill/SKILL.md` ada
- [x] Fallback policy default OFF
- [x] Safety lock `ALLOW_SUBMIT=false` default
- [x] Idempotent re-run policy documented

**Gate A status: PASS**

---

## Gate B — Local Setup

- [x] Python 3.10+ installed
- [x] `python -m venv .venv`
- [x] `pip install -r requirements.txt`
- [x] `playwright install chromium`
- [x] Copy `.env.example` → `.env`
- [x] Isi `SIAKAD_USERNAME` + `SIAKAD_PASSWORD`
- [x] `ALLOW_SUBMIT=false`
- [x] `USE_FALLBACK=false`
- [x] `pytest tests/ -q` lulus

**Gate B status: PASS**

---

## Gate C — DOM Recon

- [x] Login SIAKAD berhasil
- [x] Halaman KRS bisa dibuka via menu **Kartu Rencana Studi**
- [x] Selector login + nav + existing KRS di `selectors.json`
- [x] Screenshot/HTML di `logs/recon/`
- [x] Notes di `logs/recon/NOTES.md`
- [ ] **Re-recon saat masa KRS buka** untuk:
  - `krs.select_control`
  - `krs.submit`
  - jadwal/kuota editable
  - success/error message submit

**Gate C status: PARTIAL** — cukup untuk login/scrape/select-engine; **belum** cukup untuk production submit UI.

---

## Gate D — Dry-run Success

- [x] `python main.py --dry-run` selesai tanpa crash
- [x] Login otomatis berhasil
- [x] Scraping existing KRS OK
- [x] Scraping offered (filter priority) OK / partial valid
- [x] Selection report tersimpan di `logs/selection_report.json`
- [x] Selection engine unit tests lulus
- [x] Submit safety locks unit tests lulus
- [x] Di luar masa KRS: status PARTIAL + reason `krs_period_closed` (expected)
- [ ] Saat masa KRS buka: total selected mencapai target 23 SKS semester 5 (belum bisa diverifikasi sekarang)

**Gate D status: PASS (for current closed-period capabilities)**  
Production semester-5 fill still waits for open period + re-recon.

---

## Gate E — Production Submit

- [ ] Gate C complete for select/submit selectors
- [ ] Gate D PASS on open-period dry-run with acceptable selection
- [ ] User review `logs/selection_report.json`
- [ ] Masa KRS sedang buka
- [ ] Set `ALLOW_SUBMIT=true` sadar
- [ ] Confirm / `--auto-confirm` sadar
- [ ] Screenshot before/after
- [ ] Verifikasi KRS di SIAKAD
- [ ] Kembalikan `ALLOW_SUBMIT=false`

**Gate E status: PENDING** (blocked by campus KRS period + missing submit selectors)

---

## Gate F — Hermes

- [x] Core dry-run standalone works
- [x] `hermes-skill/SKILL.md` finalized
- [x] Command reference updated
- [x] Skill installed to Hermes local skills (`bot-siakad` enabled)
- [ ] NL / slash trigger tested in Hermes chat (optional user smoke test)
- [ ] Submit via Hermes only after Gate E

**Gate F status: READY (wrapper installed)** — chat smoke test optional

---

## Decision Matrix

| Mau melakukan | Minimal gate |
|---------------|--------------|
| Dry-run status KRS existing | A + B + C(partial) + D |
| Percaya selection 23 SKS live | A + B + C(full) + D(open period) |
| Submit KRS beneran | A + B + C(full) + D + E |
| Cron auto-submit | Semua di atas + sadar total |

---

## Commands cheat-sheet

```powershell
.\.venv\Scripts\Activate.ps1
pytest tests/ -q
python main.py --dry-run
python main.py --status
# only when ready:
# set ALLOW_SUBMIT=true
# python main.py --run --auto-confirm
```

---

## Sign-off

| Gate | Status | Date |
|------|--------|------|
| A Docs | PASS | 2026-07-19 |
| B Setup | PASS | 2026-07-19 |
| C Recon | PARTIAL | 2026-07-19 |
| D Dry-run | PASS (closed period) | 2026-07-19 |
| E Production | PENDING | - |
| F Hermes wrapper | READY | 2026-07-19 |
