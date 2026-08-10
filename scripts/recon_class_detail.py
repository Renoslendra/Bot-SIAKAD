"""Recon halaman detail kelas untuk menemukan struktur jadwal + kuota.

SIAKAD menolak navigasi langsung (goto) ke URL kelas — harus klik link
dari halaman Informasi Matakuliah agar module access lolos.

Jalankan: python scripts/recon_class_detail.py
Output  : logs/recon/class_detail_*.json + .html
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from playwright.async_api import async_playwright

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from bot.config import RECON_DIR, SIAKAD_URL, ensure_runtime_dirs, priority_codes
from bot.login import login


def _slug() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


async def dump(page, label: str) -> dict:
    stamp = _slug()
    html_path = RECON_DIR / f"class_{label}_{stamp}.html"
    html_path.write_text(await page.content(), encoding="utf-8")
    await page.screenshot(path=str(RECON_DIR / f"class_{label}_{stamp}.png"), full_page=True)

    tables = await page.evaluate(
        """() => Array.from(document.querySelectorAll('table')).map((t, i) => ({
            idx: i,
            className: (t.className || '').toString() || null,
            headers: Array.from(t.querySelectorAll('th')).map(th => (th.innerText||'').trim()),
            rows: Array.from(t.querySelectorAll('tr')).slice(0, 30).map(tr =>
                Array.from(tr.querySelectorAll('th,td')).map(td =>
                    (td.innerText||'').trim().replace(/\\s+/g,' ').slice(0,150))
            ),
        }))"""
    )
    body = " ".join((await page.locator("body").inner_text()).split())
    return {
        "label": label,
        "url": page.url,
        "title": await page.title(),
        "html": str(html_path),
        "tables": tables,
        "body": body[:4000],
    }


async def goto_info_mk(page) -> None:
    await page.get_by_role("link", name="Informasi Matakuliah").first.click()
    await page.wait_for_load_state("domcontentloaded")
    await page.wait_for_timeout(1200)


async def main() -> None:
    ensure_runtime_dirs()
    wanted = set(priority_codes())
    results: list[dict] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900}, locale="id-ID")
        page = await context.new_page()
        page.set_default_timeout(30000)

        print("[1] login")
        await page.goto(SIAKAD_URL, wait_until="domcontentloaded")
        await login(page, screenshot_on_success=False)

        print("[2] Informasi Matakuliah")
        await goto_info_mk(page)
        results.append(await dump(page, "info_mk_list"))

        # Kumpulkan (kode, teks kelas) untuk MK prioritas
        pairs = await page.evaluate(
            """(codes) => {
                const out = [];
                document.querySelectorAll('table.table-common tr').forEach(tr => {
                    const tds = tr.querySelectorAll('td');
                    if (tds.length < 5) return;
                    const code = (tds[1].innerText||'').trim().toUpperCase();
                    if (!codes.includes(code)) return;
                    const a = tds[4].querySelector('a');
                    if (!a) return;
                    out.push({code, kelas: (a.innerText||'').trim()});
                });
                return out;
            }""",
            sorted(wanted),
        )
        print(f"    ditemukan {len(pairs)} link kelas untuk MK prioritas")

        # Ambil sample: 1 kelas per MK, maksimal 3 MK
        seen: set[str] = set()
        sample: list[dict] = []
        for pair in pairs:
            if pair["code"] in seen:
                continue
            seen.add(pair["code"])
            sample.append(pair)
            if len(sample) >= 3:
                break

        for pair in sample:
            label = f"{pair['code']}_{pair['kelas'].replace(' ', '')}"
            print(f"[+] klik {pair['code']} kelas {pair['kelas']}")
            try:
                await goto_info_mk(page)
                # Link kelas berada di tabel collapsible (hidden) -> klik via JS
                clicked = await page.evaluate(
                    """({code, kelas}) => {
                        const rows = document.querySelectorAll('table.table-common tr');
                        for (const tr of rows) {
                            const tds = tr.querySelectorAll('td');
                            if (tds.length < 5) continue;
                            if ((tds[1].innerText||'').trim().toUpperCase() !== code) continue;
                            const a = tds[4].querySelector('a');
                            if (!a) continue;
                            if (kelas && (a.innerText||'').trim() !== kelas) continue;
                            a.click();
                            return true;
                        }
                        return false;
                    }""",
                    {"code": pair["code"], "kelas": pair["kelas"]},
                )
                if not clicked:
                    raise RuntimeError("link kelas tidak ditemukan via JS")
                await page.wait_for_load_state("domcontentloaded")
                await page.wait_for_timeout(1500)
                results.append(await dump(page, label))
            except Exception as exc:
                print(f"    gagal: {exc}")
                results.append({"label": label, "error": str(exc)})

        await browser.close()

    out = RECON_DIR / f"class_detail_report_{_slug()}.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[done] {out}")

    for item in results:
        print("=" * 74)
        print(f"{item.get('label')} -> {item.get('title')} | {item.get('url','')[:80]}")
        if item.get("error"):
            print(f"  ERROR: {item['error']}")
            continue
        for table in item.get("tables", []):
            print(f"  table[{table['idx']}] class={table['className']} headers={table['headers']}")
            for row in table["rows"][:8]:
                print(f"    {row}")


if __name__ == "__main__":
    asyncio.run(main())
