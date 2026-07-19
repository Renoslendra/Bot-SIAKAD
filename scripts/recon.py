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

from bot.config import RECON_DIR, SIAKAD_URL, ensure_runtime_dirs
from bot.login import login


def _slug() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


async def dump_page(page, name: str) -> dict:
    ensure_runtime_dirs()
    stamp = _slug()
    html_path = RECON_DIR / f"{name}_{stamp}.html"
    shot_path = RECON_DIR / f"{name}_{stamp}.png"
    html_path.write_text(await page.content(), encoding="utf-8")
    await page.screenshot(path=str(shot_path), full_page=True)
    return {"url": page.url, "title": await page.title(), "html": str(html_path), "screenshot": str(shot_path)}


async def summarize_tables(page) -> list[dict]:
    return await page.evaluate(
        """() => Array.from(document.querySelectorAll('table')).slice(0, 20).map((table, tIdx) => ({
            tIdx,
            id: table.id || null,
            className: (table.className || '').toString().slice(0, 120) || null,
            headers: Array.from(table.querySelectorAll('th')).map(th => (th.innerText || '').trim()).slice(0, 20),
            rowCount: table.querySelectorAll('tr').length,
            sampleRows: Array.from(table.querySelectorAll('tr')).slice(0, 6).map(tr =>
                Array.from(tr.querySelectorAll('th,td')).map(td => (td.innerText || '').trim().replace(/\\s+/g, ' ').slice(0, 80))
            ),
            inputs: Array.from(table.querySelectorAll('input, select, button')).slice(0, 20).map(el => ({
                tag: el.tagName.toLowerCase(),
                type: el.getAttribute('type'),
                name: el.getAttribute('name'),
                id: el.id || null,
                value: ((el.value || '').toString().slice(0, 40) || null),
            })),
        }))"""
    )


async def body_sample(page, limit: int = 2000) -> str:
    text = await page.locator("body").inner_text()
    return " ".join(text.split())[:limit]


async def main() -> None:
    ensure_runtime_dirs()
    report: dict = {"started_at": datetime.now().isoformat(), "steps": []}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900}, locale="id-ID")
        page = await context.new_page()
        page.set_default_timeout(30000)

        print("[1] login")
        await page.goto(SIAKAD_URL, wait_until="domcontentloaded")
        await login(page, screenshot_on_success=False)
        report["steps"].append({"name": "dashboard", "dump": await dump_page(page, "recon_dashboard")})

        print("[2] KRS page")
        await page.get_by_role("link", name="Kartu Rencana Studi").click()
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(1500)
        report["steps"].append(
            {
                "name": "krs",
                "dump": await dump_page(page, "recon_krs"),
                "tables": await summarize_tables(page),
                "body": await body_sample(page),
            }
        )
        print("  body:", report["steps"][-1]["body"][:180])

        print("[3] Informasi Matakuliah")
        await page.get_by_role("link", name="Informasi Matakuliah").click()
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(1500)
        report["steps"].append(
            {
                "name": "info_mk",
                "dump": await dump_page(page, "recon_info_mk"),
                "tables": await summarize_tables(page),
                "body": await body_sample(page),
            }
        )

        out = RECON_DIR / f"recon_report_{_slug()}.json"
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[done] {out}")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
