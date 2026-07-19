from __future__ import annotations

import asyncio
import json
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from playwright.async_api import async_playwright

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from bot.config import FALLBACK_COURSES, PRIORITY_COURSES, SIAKAD_URL
from bot.login import login

PRIORITY_CODES = [c["code"] for c in PRIORITY_COURSES]
FALLBACK_CODES = [c["code"] for c in FALLBACK_COURSES]


async def scrape_all_courses(page) -> list[dict]:
    await page.get_by_role("link", name="Informasi Matakuliah").click()
    await page.wait_for_load_state("domcontentloaded")
    await page.wait_for_timeout(1500)

    prodi = page.locator("select[name='prodi']")
    if await prodi.count() > 0:
        options = await prodi.locator("option").all_text_contents()
        for opt in options:
            if "informatika" in opt.lower() and "manajemen" not in opt.lower() and "pendidikan" not in opt.lower():
                try:
                    await prodi.select_option(label=opt.strip())
                    submit = page.locator("input[type='submit'][value='lihat'], input[type='submit']")
                    if await submit.count() > 0:
                        await submit.first.click()
                        await page.wait_for_load_state("domcontentloaded")
                        await page.wait_for_timeout(2000)
                    print("Prodi selected:", opt.strip())
                except Exception as exc:
                    print("prodi select failed:", exc)
                break

    rows = page.locator("table.table-common tr:has(td)")
    count = await rows.count()
    courses: dict[str, dict] = {}
    for i in range(count):
        row = rows.nth(i)
        cells = row.locator("td")
        n = await cells.count()
        if n < 5:
            continue
        texts = [" ".join((await cells.nth(c).inner_text()).split()) for c in range(n)]
        code = texts[1].strip().upper()
        if not re.search(r"[A-Z]{2,}\d{2,}", code):
            continue
        name = texts[2]
        lecturer = texts[3] if n > 3 else ""
        class_name = texts[4] if n > 4 else ""
        sks_raw = texts[6] if n > 6 else (texts[5] if n > 5 else "0")
        sks = int(re.sub(r"[^\d]", "", sks_raw) or "0")
        entry = courses.setdefault(code, {"code": code, "name": name, "sks": sks, "classes": []})
        entry["classes"].append({"class_name": class_name, "lecturer": lecturer})
    return list(courses.values())


async def main() -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900}, locale="id-ID")
        page = await context.new_page()
        await page.goto(SIAKAD_URL, wait_until="domcontentloaded")
        await login(page, screenshot_on_success=False)
        courses = await scrape_all_courses(page)
        await browser.close()

    by_code = {c["code"].upper(): c for c in courses}
    print("\n=== PRIORITY SEMESTER 5 CHECK ===")
    found, missing = [], []
    for code in PRIORITY_CODES:
        item = by_code.get(code)
        if item:
            found.append(code)
            classes = ", ".join(c.get("class_name") or "-" for c in item.get("classes") or [])
            print(f"[OK] {code} | {item['name']} | {item['sks']} SKS | classes: {classes}")
        else:
            missing.append(code)
            print(f"[MISSING] {code}")

    print("\n=== FALLBACK CHECK ===")
    fb_found, fb_missing = [], []
    for code in FALLBACK_CODES:
        item = by_code.get(code)
        if item:
            fb_found.append(code)
            print(f"[OK] {code} | {item['name']} | {item['sks']} SKS")
        else:
            fb_missing.append(code)
            print(f"[MISSING] {code}")

    total_priority_sks = sum(int(by_code[c]["sks"]) for c in found)
    print("\n=== SUMMARY ===")
    print(f"Priority found: {len(found)}/8 codes, SKS sum(found)={total_priority_sks}/23")
    print(f"Priority missing: {missing or '-'}")
    print(f"Fallback found: {len(fb_found)}/4")
    print(f"Fallback missing: {fb_missing or '-'}")
    print("COMPLETE" if len(missing) == 0 and total_priority_sks == 23 else "NOT COMPLETE")

    out = {
        "priority_found": found,
        "priority_missing": missing,
        "fallback_found": fb_found,
        "fallback_missing": fb_missing,
        "priority_sks_found": total_priority_sks,
        "complete": len(missing) == 0 and total_priority_sks == 23,
        "courses_priority": [by_code[c] for c in found],
    }
    out_path = PROJECT_ROOT / "logs" / "semester5_check.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
