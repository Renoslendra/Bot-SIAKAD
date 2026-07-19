from __future__ import annotations

import asyncio
import re
from datetime import datetime
from typing import Any

from playwright.async_api import Page

from bot.config import (
    ACTION_DELAY,
    EXISTING_KRS_PATH,
    SCRAPED_COURSES_PATH,
    ScrapingError,
    load_selectors,
)
from bot.utils import get_logger, save_json, screenshot_path, total_sks


async def navigate_to_krs(page: Page, selectors: dict[str, Any] | None = None) -> None:
    log = get_logger("scraper")
    data = selectors or load_selectors()
    nav = data.get("nav", {})
    krs = data.get("krs", {})
    krs_link = nav.get("krs") or "a:has-text('Kartu Rencana Studi')"
    heading = krs.get("heading") or "h2:has-text('Kartu Rencana Studi')"

    log.info("Navigasi ke halaman Kartu Rencana Studi")
    locator = page.locator(krs_link).first
    if await locator.count() == 0:
        raise ScrapingError("Link navigasi KRS tidak ditemukan")
    await locator.click()
    await page.wait_for_load_state("domcontentloaded")
    await asyncio.sleep(ACTION_DELAY)

    if await page.locator(heading).count() == 0:
        body = await page.locator("body").inner_text()
        if "Kartu Rencana Studi" not in body and "KRS" not in body:
            raise ScrapingError("Halaman KRS tidak terbuka dengan benar")


async def detect_krs_period(page: Page, selectors: dict[str, Any] | None = None) -> dict[str, Any]:
    data = selectors or load_selectors()
    krs = data.get("krs", {})
    warning_sel = krs.get("warning_container") or "#warning"
    not_period_text = (krs.get("not_period_text") or "Bukan Periode Krs").lower()
    select_control = krs.get("select_control")
    submit_control = krs.get("submit")

    warning_text = ""
    if await page.locator(warning_sel).count() > 0:
        warning_text = " ".join((await page.locator(warning_sel).inner_text()).split())

    body_text = " ".join((await page.locator("body").inner_text()).split())
    is_open = True
    reason = "Periode KRS terlihat aktif / tidak ada peringatan penutupan"

    if not_period_text in warning_text.lower() or not_period_text in body_text.lower():
        is_open = False
        reason = warning_text or krs.get("not_period_text") or "Bukan Periode Krs"

    has_select = bool(select_control) and await page.locator(select_control).count() > 0
    has_submit = bool(submit_control) and await page.locator(submit_control).count() > 0
    if is_open and not (has_select or has_submit):
        if select_control is None and submit_control is None:
            is_open = False
            reason = "Kontrol pilih/submit KRS belum tersedia di selectors (kemungkinan di luar masa KRS)"

    return {
        "is_open": is_open,
        "reason": reason,
        "warning_text": warning_text,
        "has_select_control": has_select,
        "has_submit_control": has_submit,
    }


async def scrape_profile(page: Page, selectors: dict[str, Any] | None = None) -> dict[str, str]:
    data = selectors or load_selectors()
    profile_sel = (data.get("krs") or {}).get("profile_table") or "table.table-list"
    profile: dict[str, str] = {}
    if await page.locator(profile_sel).count() == 0:
        return profile

    rows = page.locator(f"{profile_sel} tr")
    count = await rows.count()
    for idx in range(count):
        row = rows.nth(idx)
        cells = row.locator("th, td")
        cell_count = await cells.count()
        if cell_count < 2:
            continue
        key = " ".join((await cells.nth(0).inner_text()).split())
        value = " ".join((await cells.nth(1).inner_text()).split())
        if key:
            profile[key] = value
    return profile


async def scrape_existing_krs(
    page: Page,
    *,
    selectors: dict[str, Any] | None = None,
    save: bool = True,
) -> dict[str, Any]:
    log = get_logger("scraper")
    data = selectors or load_selectors()
    krs = data.get("krs", {})
    table_rows = krs.get("course_rows") or "table.table-common tr:has(td)"

    await navigate_to_krs(page, data)
    shot = screenshot_path("scraper", "krs_existing")
    await page.screenshot(path=str(shot), full_page=True)

    period = await detect_krs_period(page, data)
    profile = await scrape_profile(page, data)

    courses: list[dict[str, Any]] = []
    rows = page.locator(table_rows)
    row_count = await rows.count()
    for idx in range(row_count):
        row = rows.nth(idx)
        cells = row.locator("td")
        cell_count = await cells.count()
        if cell_count < 3:
            continue

        texts = [" ".join((await cells.nth(cidx).inner_text()).split()) for cidx in range(cell_count)]
        joined = " ".join(texts).lower()
        if "total sks" in joined:
            continue
        if not any(re.search(r"[A-Za-z]{2,}\d{2,}", text) for text in texts):
            continue

        code = texts[1] if cell_count >= 2 else ""
        name = texts[2] if cell_count >= 3 else ""
        sks_raw = texts[3] if cell_count >= 4 else "0"
        if not re.search(r"[A-Za-z]{2,}\d{2,}", code):
            continue
        try:
            sks = int(re.sub(r"[^\d]", "", sks_raw) or "0")
        except ValueError:
            sks = 0

        courses.append(
            {
                "code": code.strip(),
                "name": name.strip(),
                "sks": sks,
                "class_name": None,
                "schedules": [],
                "source": "existing",
            }
        )

    payload = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "url": page.url,
        "period": period,
        "profile": profile,
        "courses": courses,
        "total_sks": total_sks(courses),
        "count": len(courses),
        "screenshot": str(shot),
    }
    log.info(
        f"KRS existing: {payload['count']} MK / {payload['total_sks']} SKS | "
        f"periode_open={period['is_open']} ({period['reason']})"
    )
    if save:
        path = save_json(EXISTING_KRS_PATH, payload)
        log.info(f"Disimpan: {path}")
    return payload


async def scrape_offered_courses(
    page: Page,
    *,
    target_codes: list[str] | None = None,
    selectors: dict[str, Any] | None = None,
    save: bool = True,
) -> dict[str, Any]:
    log = get_logger("scraper")
    data = selectors or load_selectors()
    info = data.get("info_matakuliah") or {}
    nav = data.get("nav") or {}
    info_link = nav.get("info_matakuliah") or "a:has-text('Informasi Matakuliah')"
    fields = info.get("fields") or {}
    row_sel = info.get("course_rows") or "table.table-common tr:has(td)"

    log.info("Navigasi ke Informasi Matakuliah")
    locator = page.locator(info_link).first
    if await locator.count() == 0:
        raise ScrapingError("Link Informasi Matakuliah tidak ditemukan")
    await locator.click()
    await page.wait_for_load_state("domcontentloaded")
    await asyncio.sleep(ACTION_DELAY)

    shot = screenshot_path("scraper", "info_mk")
    await page.screenshot(path=str(shot), full_page=True)

    wanted = {code.upper() for code in (target_codes or [])}
    courses_map: dict[str, dict[str, Any]] = {}
    rows = page.locator(row_sel)
    row_count = await rows.count()
    for idx in range(row_count):
        row = rows.nth(idx)
        cells = row.locator("td")
        cell_count = await cells.count()
        if cell_count < 5:
            continue
        texts = [" ".join((await cells.nth(cidx).inner_text()).split()) for cidx in range(cell_count)]
        code = texts[1].strip().upper() if cell_count >= 2 else ""
        if not re.search(r"[A-Za-z]{2,}\d{2,}", code):
            continue
        if wanted and code not in wanted:
            continue

        name = texts[2] if cell_count >= 3 else ""
        lecturer = texts[3] if cell_count >= 4 else ""
        class_name = texts[4] if cell_count >= 5 else ""
        sks_raw = texts[6] if cell_count >= 7 else (texts[5] if cell_count >= 6 else "0")
        try:
            sks = int(re.sub(r"[^\d]", "", sks_raw) or "0")
        except ValueError:
            sks = 0

        class_href = None
        class_link_sel = fields.get("class_link") or "td:nth-child(5) a"
        link = row.locator(class_link_sel)
        if await link.count() > 0:
            class_href = await link.first.get_attribute("href")

        entry = courses_map.setdefault(
            code,
            {"code": code, "name": name, "sks": sks, "classes": []},
        )
        entry["classes"].append(
            {
                "class_name": class_name,
                "lecturer": lecturer,
                "quota_remaining": None,
                "schedules": [],
                "href": class_href,
            }
        )

    courses = list(courses_map.values())
    payload = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "url": page.url,
        "target_filter": sorted(wanted),
        "courses": courses,
        "count": len(courses),
        "screenshot": str(shot),
        "notes": [
            "Schedule/quota tidak tersedia di list Informasi Matakuliah saat recon.",
            "Selection/submit UI hanya ada saat masa KRS buka.",
        ],
    }
    log.info(f"Scraped offered courses (filtered): {payload['count']} MK")
    if save:
        path = save_json(SCRAPED_COURSES_PATH, payload)
        log.info(f"Disimpan: {path}")
    return payload
