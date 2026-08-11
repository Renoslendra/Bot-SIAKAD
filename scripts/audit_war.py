"""Audit menyeluruh: simulasikan SELURUH alur war KRS tanpa submit.

Cek:
  1. Login
  2. Navigasi KRS
  3. Tombol Tambah Matakuliah
  4. Klik -> halaman pilih MK
  5. Mapping checkbox ke 8 MK target
  6. Verifikasi nama MK PERSIS cocok
  7. Centang checkbox (tanpa submit)
  8. Screenshot setiap tahap

Jalankan: python scripts/audit_war.py
"""

from __future__ import annotations

import asyncio
import io
import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from bot.config import PRIORITY_COURSES, RECON_DIR, SIAKAD_URL, ensure_runtime_dirs
from bot.login import login
from bot.scraper import navigate_to_krs
from bot.utils import setup_logger

TARGETS = [
    {"code": c["code"], "name": c["name"], "sks": c["sks"],
     "preferred_class": c.get("preferred_class", "")}
    for c in PRIORITY_COURSES
]


def _slug():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _normalize(text):
    return re.sub(r"[^a-z0-9]", "", text.lower())


async def main():
    setup_logger("INFO")
    ensure_runtime_dirs()
    from playwright.async_api import async_playwright

    issues = []
    passed = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900}, locale="id-ID"
        )
        page = await context.new_page()
        page.set_default_timeout(30000)

        # ========== AUDIT 1: LOGIN ==========
        print("=" * 70)
        print("AUDIT 1: LOGIN")
        try:
            await page.goto(SIAKAD_URL, wait_until="domcontentloaded")
            await login(page, screenshot_on_success=False)
            if await page.locator("a:has-text('[ Logout ]')").count() > 0:
                passed.append("Login berhasil")
                print("  [OK] Login berhasil")
            else:
                issues.append("Login: indikator logout tidak ditemukan")
                print("  [FAIL] Indikator logout tidak ditemukan")
        except Exception as exc:
            issues.append(f"Login gagal: {exc}")
            print(f"  [FAIL] {exc}")
            await browser.close()
            return

        # ========== AUDIT 2: NAVIGASI KRS ==========
        print("\nAUDIT 2: NAVIGASI KRS")
        try:
            from bot.config import load_selectors
            selectors = load_selectors()
            await navigate_to_krs(page, selectors)
            passed.append("Navigasi ke halaman KRS")
            print("  [OK] Halaman KRS terbuka")
        except Exception as exc:
            issues.append(f"Navigasi KRS gagal: {exc}")
            print(f"  [FAIL] {exc}")
            await browser.close()
            return

        # ========== AUDIT 3: TOMBOL TAMBAH MATAKULIAH ==========
        print("\nAUDIT 3: TOMBOL TAMBAH MATAKULIAH")
        tambah_sel = "input[name='btnProses'][value='Tambah Matakuliah']"
        if await page.locator(tambah_sel).count() > 0:
            passed.append("Tombol 'Tambah Matakuliah' tersedia")
            print("  [OK] Tombol 'Tambah Matakuliah' ditemukan")
        else:
            issues.append("Tombol 'Tambah Matakuliah' TIDAK ditemukan — mungkin masa KRS belum buka")
            print("  [FAIL] Tombol tidak ditemukan")
            # Lanjut cek apakah ada warning
            body = await page.locator("body").inner_text()
            if "Bukan Periode" in body:
                print("  [INFO] Ada peringatan: Bukan Periode KRS")
            await browser.close()
            return

        # ========== AUDIT 4: KLIK TAMBAH -> HALAMAN PILIH MK ==========
        print("\nAUDIT 4: KLIK TAMBAH MATAKULIAH")
        try:
            await page.locator(tambah_sel).first.click()
            await page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(2)

            shot = RECON_DIR / f"audit_tambah_mk_{_slug()}.png"
            await page.screenshot(path=str(shot), full_page=True)
            passed.append("Halaman pilih MK terbuka")
            print(f"  [OK] Halaman pilih MK terbuka (screenshot: {shot.name})")
        except Exception as exc:
            issues.append(f"Klik Tambah gagal: {exc}")
            print(f"  [FAIL] {exc}")
            await browser.close()
            return

        # ========== AUDIT 4B: BUKA PAKET SEMESTER 5 ==========
        print("\nAUDIT 4B: BUKA PAKET SEMESTER 5")
        semester_5 = page.locator("#semester_5").first
        toggle_5 = page.locator("a:has-text('Paket Semester 5')").first
        try:
            if not await semester_5.is_visible():
                await toggle_5.click()
                await semester_5.wait_for(state="visible")
            passed.append("Paket Semester 5 dibuka")
            print("  [OK] Accordion Paket Semester 5 terbuka")
        except Exception as exc:
            issues.append(f"Paket Semester 5 gagal dibuka: {exc}")
            print(f"  [FAIL] {exc}")
            await browser.close()
            return

        # ========== AUDIT 5: HITUNG CHECKBOX ==========
        print("\nAUDIT 5: CHECKBOX")
        cb_count = await page.locator("input[type='checkbox'][name='kodeMkul[]']").count()
        print(f"  [INFO] Total checkbox: {cb_count}")
        if cb_count > 0:
            passed.append(f"Checkbox tersedia: {cb_count}")
        else:
            issues.append("TIDAK ada checkbox kodeMkul[] di halaman")

        # ========== AUDIT 6: MAPPING CHECKBOX KE 8 MK TARGET ==========
        print("\nAUDIT 6: MAPPING CHECKBOX KE 8 MK TARGET (MATCH KETAT)")
        print("-" * 70)

        # Scrape seluruh tabel
        rows_data = await page.evaluate("""() => {
            const out = [];
            const tables = document.querySelectorAll('table.table-common');
            for (const table of tables) {
                for (const tr of table.querySelectorAll('tr')) {
                    const tds = tr.querySelectorAll('td');
                    if (tds.length < 7) continue;
                    const cb = tds[1].querySelector("input[type='checkbox']");
                    if (!cb) continue;
                    out.push({
                        value: cb.value,
                        cbClass: cb.className || '',
                        kelas: (tds[2].innerText || '').trim(),
                        namaMK: (tds[3].innerText || '').trim(),
                        jadwal: (tds[4].innerText || '').trim(),
                        sks: (tds[6].innerText || '').trim(),
                    });
                }
            }
            return out;
        }""")

        print(f"  [INFO] Total baris MK di tabel: {len(rows_data)}")

        match_results = []
        for target in TARGETS:
            code = target["code"]
            name = target["name"]
            kelas = target["preferred_class"]
            name_norm = _normalize(name)
            kelas_norm = _normalize(kelas)

            # MATCH KETAT: nama persis + kelas persis
            found = None
            for row in rows_data:
                if _normalize(row["namaMK"]) == name_norm and _normalize(row["kelas"]) == kelas_norm:
                    found = row
                    break

            if found:
                match_results.append({
                    "code": code, "target_name": name, "siakad_name": found["namaMK"],
                    "kelas": kelas, "jadwal": found["jadwal"], "sks": found["sks"],
                    "cb_value": found["value"], "match": True,
                })
                print(f"  [OK]   {code} {kelas:8s} -> '{found['namaMK']}' (EXACT)")
                print(f"         Jadwal: {found['jadwal']}  SKS: {found['sks']}")
            else:
                match_results.append({
                    "code": code, "target_name": name, "kelas": kelas, "match": False,
                })
                issues.append(f"{code} kelas {kelas} '{name}': TIDAK match ketat")
                print(f"  [FAIL] {code} {kelas:8s} '{name}' -> TIDAK DITEMUKAN (match ketat)")
                similar = [r for r in rows_data
                           if _normalize(name) in _normalize(r["namaMK"])
                           or _normalize(r["namaMK"]) in _normalize(name)]
                if similar:
                    print(f"         Nama mirip di SIAKAD:")
                    for r in similar[:8]:
                        print(f"           {r['kelas']:8s} '{r['namaMK']}' {r['jadwal']}")

        matched = sum(1 for m in match_results if m["match"])
        print(f"\n  Matched: {matched}/8")

        # ========== AUDIT 7: TEST CENTANG CHECKBOX VIA JS (TANPA SUBMIT) ==========
        print("\nAUDIT 7: TEST CENTANG CHECKBOX (via JS, seperti submitter)")
        checked_count = 0
        for m in match_results:
            if not m.get("match"):
                continue
            ok = await page.evaluate(
                """(value) => {
                    const cbs = document.querySelectorAll("input[type='checkbox'][name='kodeMkul[]']");
                    for (const cb of cbs) {
                        if (cb.value !== value) continue;
                        if (!cb.checked) {
                            cb.checked = true;
                            if (typeof cb.onclick === 'function') { try { cb.onclick(); } catch(e){} }
                            cb.dispatchEvent(new Event('change', {bubbles: true}));
                        }
                        return cb.checked === true;
                    }
                    return false;
                }""",
                m["cb_value"],
            )
            if ok:
                checked_count += 1
                print(f"  [OK]   {m['code']} {m['kelas']}: berhasil dicentang (JS)")
            else:
                issues.append(f"{m['code']}: centang JS gagal")
                print(f"  [FAIL] {m['code']}: centang JS gagal")

        # Verifikasi jumlah checkbox tercentang di DOM
        total_checked = await page.evaluate(
            """() => document.querySelectorAll("input[type='checkbox'][name='kodeMkul[]']:checked").length"""
        )
        print(f"\n  Checked (via JS): {checked_count}/8")
        print(f"  Total tercentang di DOM: {total_checked}")
        if total_checked != checked_count:
            issues.append(
                f"Mismatch: {checked_count} di-set tapi {total_checked} tercentang "
                f"(mungkin exclusiveCheck meng-uncheck yang lain)"
            )
            print(f"  [WARN] exclusiveCheck mungkin meng-uncheck checkbox lain!")

        # Screenshot setelah centang
        shot = RECON_DIR / f"audit_checked_{_slug()}.png"
        await page.screenshot(path=str(shot), full_page=True)
        print(f"  Screenshot: {shot.name}")

        # ========== AUDIT 8: TOMBOL TAMBAH (SUBMIT) ==========
        print("\nAUDIT 8: TOMBOL SUBMIT ('Tambah')")
        submit_sel = "input[name='btnAdd'][value='Tambah']"
        if await page.locator(submit_sel).count() > 0:
            passed.append("Tombol 'Tambah' (submit) tersedia")
            print("  [OK] Tombol 'Tambah' ditemukan")
            # Cek onclick validation
            onclick = await page.locator(submit_sel).first.get_attribute("onclick")
            if onclick:
                print(f"  [INFO] onclick: {onclick}")
        else:
            issues.append("Tombol 'Tambah' (btnAdd) TIDAK ditemukan")
            print("  [FAIL] Tombol 'Tambah' tidak ditemukan")

        # ========== AUDIT 9: CEK NAMA MK CONFIG VS SIAKAD ==========
        print("\nAUDIT 9: CROSS-CHECK NAMA MK")
        name_issues = []
        for m in match_results:
            if not m.get("match"):
                continue
            if _normalize(m["target_name"]) != _normalize(m["siakad_name"]):
                name_issues.append(m)
                print(f"  [WARN] {m['code']}: nama BERBEDA")
                print(f"         Config: '{m['target_name']}'")
                print(f"         SIAKAD: '{m['siakad_name']}'")

        if not name_issues:
            print("  [OK] Semua nama MK cocok")
        else:
            print(f"\n  {len(name_issues)} nama MK perlu diperbaiki di config")

        # ========== TIDAK SUBMIT — klik Batal ==========
        print("\nMembatalkan (klik Batal)...")
        cancel = page.locator("input[name='btnBack'][value='Batal']").first
        if await cancel.count() > 0:
            await cancel.click()
            await page.wait_for_load_state("domcontentloaded")
            print("  [OK] Kembali ke halaman KRS")

        await browser.close()

    # ========== RINGKASAN ==========
    print("\n" + "=" * 70)
    print("RINGKASAN AUDIT")
    print("=" * 70)
    print(f"\nPASSED: {len(passed)}")
    for item in passed:
        print(f"  [OK] {item}")

    print(f"\nISSUES: {len(issues)}")
    if issues:
        for item in issues:
            print(f"  [!!] {item}")
    else:
        print("  Tidak ada masalah")

    print(f"\nCHECKBOX MATCH: {matched}/8")
    print(f"CHECKBOX CENTANG: {checked_count}/8")

    if not issues and matched == 8 and checked_count == 8:
        print("\n>>> VERDICT: SIAP UNTUK WAR KRS BESOK <<<")
        return 0
    else:
        print("\n>>> VERDICT: ADA MASALAH YANG HARUS DIPERBAIKI <<<")
        return 1

    # Save report
    report_path = RECON_DIR / f"audit_report_{_slug()}.json"
    report = {
        "timestamp": datetime.now().isoformat(),
        "passed": passed,
        "issues": issues,
        "match_results": match_results,
        "matched": matched,
        "checked": checked_count,
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
