"""Dump SEMUA baris di halaman pilih MK ke JSON supaya bisa analisa matching.

Jalankan: python scripts/dump_pilih_mk.py
Output  : logs/recon/pilih_mk_rows.json
"""

from __future__ import annotations

import asyncio
import io
import json
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from bot.config import RECON_DIR, SIAKAD_URL, ensure_runtime_dirs, load_selectors
from bot.login import login
from bot.scraper import navigate_to_krs
from bot.utils import setup_logger


async def main():
    setup_logger("WARNING")
    ensure_runtime_dirs()
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900}, locale="id-ID")
        page = await context.new_page()
        page.set_default_timeout(30000)

        await page.goto(SIAKAD_URL, wait_until="domcontentloaded")
        await login(page, screenshot_on_success=False)
        selectors = load_selectors()
        await navigate_to_krs(page, selectors)

        await page.locator("input[name='btnProses'][value='Tambah Matakuliah']").first.click()
        await page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(2)

        rows = await page.evaluate("""() => {
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
                        cbClass: cb.className,
                        onclick: cb.getAttribute('onclick'),
                        no: (tds[0].innerText || '').trim(),
                        kelas: (tds[2].innerText || '').trim(),
                        namaMK: (tds[3].innerText || '').trim(),
                        jadwal: (tds[4].innerText || '').trim(),
                        sks: (tds[6].innerText || '').trim(),
                    });
                }
            }
            return out;
        }""")

        await browser.close()

    out_path = RECON_DIR / "pilih_mk_rows.json"
    out_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Total rows: {len(rows)}")
    print(f"Saved: {out_path}")

    # Tampilkan MK yang relevan dengan target
    keywords = ["proyek", "sain", "citra", "basis data", "pembelajaran", "metodologi",
                "pemodelan", "terdistribusi", "perangkat"]
    print("\nBaris yang relevan dengan target:")
    for r in rows:
        low = r["namaMK"].lower()
        if any(k in low for k in keywords):
            print(f"  [{r['no']:>3}] {r['kelas']:8s} | {r['namaMK']:40s} | {r['jadwal']:35s} | {r['sks']} sks | {r['cbClass']}")


if __name__ == "__main__":
    asyncio.run(main())
