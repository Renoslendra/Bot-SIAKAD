"""Recon mendalam halaman KRS: form, tombol, dan alur 'Tambah Matakuliah'.

Jalankan: python scripts/recon_krs_page.py
Output  : logs/recon/krs_deep_*.json + .html
"""

from __future__ import annotations

import asyncio
import io
import json
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from playwright.async_api import async_playwright

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from bot.config import RECON_DIR, SIAKAD_URL, ensure_runtime_dirs, load_selectors
from bot.login import login
from bot.scraper import navigate_to_krs


def _slug() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


PROBE_JS = """() => {
    const q = (sel) => Array.from(document.querySelectorAll(sel));
    return {
        title: document.title,
        forms: q('form').map(f => ({
            name: f.getAttribute('name'), id: f.id || null,
            action: (f.getAttribute('action') || '').slice(0, 160),
            method: f.getAttribute('method'),
            fields: Array.from(f.elements).slice(0, 40).map(el => ({
                tag: el.tagName.toLowerCase(),
                type: el.getAttribute('type'),
                name: el.getAttribute('name'),
                id: el.id || null,
                value: ((el.value || '') + '').slice(0, 50),
            })),
        })),
        controls: q("input[type='submit'], input[type='button'], button, a.button").map(el => ({
            tag: el.tagName.toLowerCase(),
            type: el.getAttribute('type'),
            name: el.getAttribute('name'),
            id: el.id || null,
            value: ((el.value || '') + '').slice(0, 60),
            text: (el.innerText || '').trim().slice(0, 60),
            onclick: (el.getAttribute('onclick') || '').slice(0, 120),
            visible: !!(el.offsetParent || el.offsetWidth || el.offsetHeight),
        })),
        checkboxes: q("input[type='checkbox']").length,
        radios: q("input[type='radio']").length,
        selects: q('select').map(s => ({
            name: s.getAttribute('name'),
            options: Array.from(s.options).slice(0, 8).map(o => (o.text || '').trim()),
        })),
        tables: q('table').map((t, i) => ({
            idx: i,
            className: (t.className || '').toString() || null,
            headers: Array.from(t.querySelectorAll('th')).map(th => (th.innerText||'').trim()),
            rowCount: t.querySelectorAll('tr').length,
            firstRows: Array.from(t.querySelectorAll('tr')).slice(0, 4).map(tr =>
                Array.from(tr.querySelectorAll('th,td')).map(td =>
                    (td.innerText||'').trim().replace(/\\s+/g,' ').slice(0, 60))),
        })),
        links: q('a').map(a => (a.innerText || '').trim()).filter(Boolean).slice(0, 60),
    };
}"""


async def snapshot(page, name: str) -> dict:
    stamp = _slug()
    path = RECON_DIR / f"krs_deep_{name}_{stamp}.html"
    path.write_text(await page.content(), encoding="utf-8")
    await page.screenshot(path=str(RECON_DIR / f"krs_deep_{name}_{stamp}.png"), full_page=True)
    data = await page.evaluate(PROBE_JS)
    data["url"] = page.url
    data["html"] = str(path)
    data["body"] = " ".join((await page.locator("body").inner_text()).split())[:2500]
    return data


def report(label: str, data: dict) -> None:
    print("=" * 78)
    print(f"{label}  |  {data.get('url','')[:90]}")
    print(f"  checkbox={data['checkboxes']}  radio={data['radios']}  select={len(data['selects'])}")
    print("  TOMBOL:")
    for c in data["controls"]:
        vis = "vis" if c["visible"] else "hid"
        print(f"    [{vis}] <{c['tag']} type={c['type']} name={c['name']}> "
              f"value={c['value']!r} text={c['text']!r}")
        if c["onclick"]:
            print(f"          onclick={c['onclick']}")
    print("  FORM:")
    for f in data["forms"]:
        print(f"    name={f['name']} action={f['action']} method={f['method']}")
        for el in f["fields"]:
            print(f"      {el['tag']} type={el['type']} name={el['name']} value={el['value']!r}")
    print("  SELECT:")
    for s in data["selects"]:
        print(f"    name={s['name']} options={s['options']}")
    print("  TABEL:")
    for t in data["tables"]:
        print(f"    [{t['idx']}] class={t['className']} rows={t['rowCount']} headers={t['headers']}")
        for row in t["firstRows"]:
            print(f"        {row}")
    print(f"  BODY: {data['body'][:400]}")
    print()


async def main() -> None:
    ensure_runtime_dirs()
    selectors = load_selectors()
    out: dict = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900}, locale="id-ID")
        page = await context.new_page()
        page.set_default_timeout(30000)

        await page.goto(SIAKAD_URL, wait_until="domcontentloaded")
        await login(page, screenshot_on_success=False)

        await navigate_to_krs(page, selectors)
        out["krs"] = await snapshot(page, "main")
        report("HALAMAN KRS", out["krs"])

        # Coba klik tombol 'Tambah Matakuliah' bila ada
        target = None
        for c in out["krs"]["controls"]:
            label = f"{c['value']} {c['text']}".lower()
            if "tambah" in label:
                target = c
                break

        if target:
            print(f">>> Klik tombol: {target['value'] or target['text']!r}")
            try:
                sel = (f"#{target['id']}" if target["id"]
                       else f"[name='{target['name']}']" if target["name"]
                       else f"[value='{target['value']}']")
                await page.locator(sel).first.click()
                await page.wait_for_load_state("domcontentloaded")
                await page.wait_for_timeout(2000)
                out["after_tambah"] = await snapshot(page, "after_tambah")
                report("SETELAH KLIK TAMBAH MATAKULIAH", out["after_tambah"])
            except Exception as exc:
                print(f"    gagal klik: {exc}")
        else:
            print(">>> Tombol 'Tambah' tidak ditemukan")

        await browser.close()

    path = RECON_DIR / f"krs_deep_report_{_slug()}.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[done] {path}")


if __name__ == "__main__":
    asyncio.run(main())
