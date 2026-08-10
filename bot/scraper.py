from __future__ import annotations

import asyncio
import re
from datetime import datetime
from typing import Any

from playwright.async_api import Page

from bot.config import (
    ACTION_DELAY,
    EXISTING_KRS_PATH,
    SCHEDULE_CACHE_PATH,
    SCRAPED_COURSES_PATH,
    ScrapingError,
    load_selectors,
)
from bot.utils import (
    get_logger,
    load_json,
    parse_schedule,
    save_json,
    screenshot_path,
    total_sks,
)


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
    tambah_button = krs.get("tambah_button") or "input[name='btnProses'][value='Tambah Matakuliah']"

    warning_text = ""
    if await page.locator(warning_sel).count() > 0:
        warning_text = " ".join((await page.locator(warning_sel).inner_text()).split())

    body_text = " ".join((await page.locator("body").inner_text()).split())
    is_open = True
    reason = "Periode KRS terlihat aktif / tidak ada peringatan penutupan"

    if not_period_text in warning_text.lower() or not_period_text in body_text.lower():
        is_open = False
        reason = warning_text or krs.get("not_period_text") or "Bukan Periode Krs"

    has_tambah = await page.locator(tambah_button).count() > 0
    has_select = bool(select_control) and await page.locator(select_control).count() > 0
    has_submit = bool(submit_control) and await page.locator(submit_control).count() > 0

    # Tombol "Tambah Matakuliah" = KRS bisa diisi (alur 2-langkah SIAKAD)
    if has_tambah:
        is_open = True
        reason = "Tombol 'Tambah Matakuliah' tersedia — KRS aktif"

    if is_open and not (has_tambah or has_select or has_submit):
        is_open = False
        reason = "Kontrol pilih/submit KRS belum tersedia di selectors (kemungkinan di luar masa KRS)"

    return {
        "is_open": is_open,
        "reason": reason,
        "warning_text": warning_text,
        "has_tambah_button": has_tambah,
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


def merge_schedule_cache(payload: dict[str, Any]) -> dict[str, Any]:
    """Isi jadwal dari cache hasil build_schedule_cache.py.

    Saat war KRS, membuka ~40 halaman detail kelas terlalu lambat.
    Cache dibangun sebelumnya dipakai agar selection langsung jalan.
    """
    log = get_logger("scraper")
    if not SCHEDULE_CACHE_PATH.exists():
        log.warning("Cache jadwal tidak ada — jalankan scripts/build_schedule_cache.py")
        return payload

    try:
        cache = load_json(SCHEDULE_CACHE_PATH)
    except Exception as exc:
        log.warning(f"Cache jadwal gagal dibaca: {exc}")
        return payload

    if not cache.get("schedule_enriched"):
        log.warning("Cache jadwal belum ter-enrich — bentrok tidak dapat dideteksi")
        return payload

    lookup: dict[tuple[str, str], dict[str, Any]] = {}
    for course in cache.get("courses") or []:
        code = str(course.get("code") or "").upper()
        for class_item in course.get("classes") or []:
            key = (code, str(class_item.get("class_name") or "").strip())
            lookup[key] = class_item

    filled = 0
    for course in payload.get("courses") or []:
        code = str(course.get("code") or "").upper()
        for class_item in course.get("classes") or []:
            if class_item.get("schedules"):
                continue
            cached = lookup.get((code, str(class_item.get("class_name") or "").strip()))
            if not cached:
                continue
            class_item["schedules"] = cached.get("schedules") or []
            if class_item.get("quota_remaining") is None:
                class_item["quota_remaining"] = cached.get("quota_remaining")
            if class_item["schedules"]:
                filled += 1

    payload["schedule_source"] = "cache"
    payload["schedule_cache_filled"] = filled
    log.info(f"Jadwal dari cache: {filled} kelas terisi")
    return payload


async def _open_info_matakuliah(page: Page, selectors: dict[str, Any]) -> None:
    nav = selectors.get("nav") or {}
    info_link = nav.get("info_matakuliah") or "a:has-text('Informasi Matakuliah')"
    locator = page.locator(info_link).first
    if await locator.count() == 0:
        raise ScrapingError("Link Informasi Matakuliah tidak ditemukan")
    await locator.click()
    await page.wait_for_load_state("domcontentloaded")
    await asyncio.sleep(ACTION_DELAY)


async def _click_class_link(page: Page, code: str, class_name: str) -> bool:
    """Buka halaman detail kelas.

    Link kelas berada di tabel collapsible yang tersembunyi, sehingga
    Playwright .click() menolak ('element is not visible'). Navigasi langsung
    via page.goto() juga ditolak SIAKAD ('tidak diijinkan mengakses module').

    Solusi: tandai link target lalu paksa tampil, sehingga bisa diklik
    normal dan Playwright menangani navigasinya (menghindari race
    'Execution context was destroyed' saat klik dilakukan di dalam evaluate).
    """
    marked = await page.evaluate(
        """({code, kelas}) => {
            const rows = document.querySelectorAll('table.table-common tr');
            for (const tr of rows) {
                const tds = tr.querySelectorAll('td');
                if (tds.length < 5) continue;
                if ((tds[1].innerText || '').trim().toUpperCase() !== code) continue;
                const a = tds[4].querySelector('a');
                if (!a) continue;
                if (kelas && (a.innerText || '').trim() !== kelas) continue;

                a.setAttribute('data-bot-target', '1');
                for (let el = a; el && el !== document.body; el = el.parentElement) {
                    el.style.display = '';
                    el.style.visibility = 'visible';
                    el.style.opacity = '1';
                    if (el.hasAttribute('hidden')) el.removeAttribute('hidden');
                }
                return true;
            }
            return false;
        }""",
        {"code": code.upper(), "kelas": class_name},
    )
    if not marked:
        return False

    link = page.locator("a[data-bot-target='1']").first
    async with page.expect_navigation(wait_until="domcontentloaded"):
        await link.click()
    return True


async def _recover_session(page: Page, selectors: dict[str, Any]) -> None:
    """Kembalikan browser ke halaman yang punya menu navigasi."""
    from bot.config import SIAKAD_URL

    try:
        await page.goto(SIAKAD_URL, wait_until="domcontentloaded")
        await asyncio.sleep(ACTION_DELAY)
    except Exception:
        pass


async def _extract_class_detail(page: Page) -> dict[str, Any]:
    """Ambil jadwal kuliah + kuota dari halaman detail kelas."""
    raw = await page.evaluate(
        """() => {
            const result = {schedules: [], quota: null, capacity: null, enrolled: null};

            // Tabel jadwal: header persis ['Hari','Jam','Ruang']
            for (const table of document.querySelectorAll('table')) {
                const heads = Array.from(table.querySelectorAll('th'))
                    .map(th => (th.innerText || '').trim().toLowerCase());
                if (heads.length !== 3) continue;
                if (!(heads[0] === 'hari' && heads[1] === 'jam' && heads[2] === 'ruang')) continue;
                for (const tr of table.querySelectorAll('tr')) {
                    const tds = tr.querySelectorAll('td');
                    if (tds.length < 3) continue;
                    const day = (tds[0].innerText || '').trim();
                    const time = (tds[1].innerText || '').trim();
                    const room = (tds[2].innerText || '').trim();
                    if (!day || !time) continue;
                    result.schedules.push({day, time, room});
                }
                break;
            }

            // Kuota: cari label kapasitas/kuota/peserta di seluruh tabel
            const body = document.body.innerText || '';
            const patterns = [
                [/kuota\\s*[:\\-]?\\s*(\\d+)/i, 'quota'],
                [/kapasitas\\s*[:\\-]?\\s*(\\d+)/i, 'capacity'],
                [/(?:jumlah\\s+)?peserta\\s*[:\\-]?\\s*(\\d+)/i, 'enrolled'],
                [/terisi\\s*[:\\-]?\\s*(\\d+)/i, 'enrolled'],
            ];
            for (const [re, key] of patterns) {
                const m = body.match(re);
                if (m) result[key] = parseInt(m[1], 10);
            }
            return result;
        }"""
    )

    schedules: list[dict[str, Any]] = []
    for item in raw.get("schedules") or []:
        text = f"{item.get('day', '')} {item.get('time', '')}"
        try:
            parsed = parse_schedule(text)
        except ValueError:
            continue
        parsed["room"] = item.get("room") or ""
        schedules.append(parsed)

    quota_remaining: int | None = None
    capacity = raw.get("capacity")
    enrolled = raw.get("enrolled")
    if raw.get("quota") is not None:
        quota_remaining = int(raw["quota"])
    elif capacity is not None and enrolled is not None:
        quota_remaining = max(int(capacity) - int(enrolled), 0)

    return {
        "schedules": schedules,
        "quota_remaining": quota_remaining,
        "capacity": capacity,
        "enrolled": enrolled,
    }


async def enrich_courses_with_schedules(
    page: Page,
    payload: dict[str, Any],
    *,
    selectors: dict[str, Any] | None = None,
    max_classes_per_course: int | None = None,
    save: bool = True,
) -> dict[str, Any]:
    """Kunjungi tiap halaman detail kelas untuk mengisi jadwal + kuota.

    Tanpa data ini, selection engine tidak bisa mendeteksi bentrok jadwal.
    """
    log = get_logger("scraper")
    data = selectors or load_selectors()
    courses = payload.get("courses") or []
    if not courses:
        return payload

    total_classes = sum(len(c.get("classes") or []) for c in courses)
    log.info(f"Enrich jadwal: {len(courses)} MK / {total_classes} kelas")

    done = 0
    for course in courses:
        code = str(course.get("code") or "").upper()
        classes = course.get("classes") or []
        if max_classes_per_course is not None:
            classes = classes[:max_classes_per_course]

        for class_item in classes:
            class_name = str(class_item.get("class_name") or "")
            try:
                await _open_info_matakuliah(page, data)
                clicked = await _click_class_link(page, code, class_name)
                if not clicked:
                    log.warning(f"{code} kelas {class_name}: link tidak ditemukan")
                    continue
                await page.wait_for_load_state("domcontentloaded")
                await asyncio.sleep(ACTION_DELAY)

                detail = await _extract_class_detail(page)
                class_item["schedules"] = detail["schedules"]
                class_item["quota_remaining"] = detail["quota_remaining"]
                class_item["capacity"] = detail["capacity"]
                class_item["enrolled"] = detail["enrolled"]

                done += 1
                raw_text = ", ".join(s.get("raw", "") for s in detail["schedules"]) or "-"
                log.info(f"{code} {class_name}: {raw_text}")
            except Exception as exc:
                log.warning(f"{code} kelas {class_name}: gagal ambil jadwal ({exc})")
                # Satu kegagalan bisa meninggalkan halaman tanpa menu nav,
                # membuat semua kelas berikutnya ikut gagal beruntun.
                await _recover_session(page, data)

    payload["schedule_enriched"] = True
    payload["schedule_enriched_count"] = done
    payload.setdefault("notes", []).append(
        f"Jadwal di-scrape dari halaman detail kelas ({done} kelas)."
    )
    log.info(f"Enrich jadwal selesai: {done}/{total_classes} kelas")

    if save:
        path = save_json(SCHEDULE_CACHE_PATH, payload)
        log.info(f"Cache jadwal disimpan: {path}")
    return payload
