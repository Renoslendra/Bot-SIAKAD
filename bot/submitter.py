"""Submitter yang mengikuti alur SIAKAD:

  1. Halaman KRS utama -> klik "Tambah Matakuliah" (btnProses)
  2. Halaman daftar MK ditawarkan -> centang checkbox -> klik "Tambah" (btnAdd)
  3. Kembali ke KRS utama -> verifikasi MK sudah masuk
"""

from __future__ import annotations

import asyncio
import re
import sys
from datetime import datetime
from typing import Any

from playwright.async_api import Page

from bot.config import (
    ACTION_DELAY,
    MAX_SUBMIT_RETRIES,
    SubmitError,
    load_selectors,
    submit_allowed,
)
from bot.scraper import detect_krs_period, navigate_to_krs, scrape_existing_krs
from bot.utils import get_logger, screenshot_path


def preflight_submit(
    *,
    dry_run: bool,
    selected: list[dict[str, Any]],
    period: dict[str, Any] | None = None,
    selectors: dict[str, Any] | None = None,
) -> tuple[bool, str]:
    allowed, reason = submit_allowed(dry_run=dry_run)
    if not allowed:
        return False, reason
    if not selected:
        return False, "Tidak ada MK baru yang dipilih untuk di-submit"

    period = period or {}
    # ponytail: skip period check — sekarang KRS sudah bisa dibuka
    # meski SIAKAD belum mengumumkan "masa KRS". Deteksi berbasis
    # keberadaan tombol "Tambah Matakuliah" sudah cukup.

    data = selectors or load_selectors()
    krs = data.get("krs") or {}
    if not krs.get("select_control"):
        return False, (
            "selectors.json belum punya krs.select_control. "
            "Ulangi recon saat masa KRS buka."
        )
    if not krs.get("submit"):
        return False, (
            "selectors.json belum punya krs.submit. "
            "Ulangi recon saat masa KRS buka."
        )
    return True, "Preflight submit lulus"


def confirm_submit(
    selected: list[dict[str, Any]],
    *,
    auto_confirm: bool = False,
) -> bool:
    log = get_logger("submitter")
    print()
    print("MK yang akan di-submit:")
    for idx, course in enumerate(selected, start=1):
        sched = ", ".join(s.get("raw", "") for s in course.get("schedules") or [])
        print(
            f"  {idx}. {course.get('code')} - {course.get('name')} - "
            f"Kelas {course.get('class_name') or '-'} - {course.get('sks')} SKS"
            f"{f' - {sched}' if sched else ''}"
        )
    print()

    if auto_confirm:
        log.warning("AUTO_CONFIRM aktif — melewati prompt submit")
        return True
    if not (hasattr(sys.stdin, "isatty") and sys.stdin.isatty()):
        log.error("Tidak ada stdin interaktif. Pakai --auto-confirm jika memang yakin.")
        return False
    answer = input("Submit KRS ke SIAKAD? (y/N): ").strip().lower()
    return answer in {"y", "yes"}


async def _navigate_to_tambah_mk(
    page: Page,
    selectors: dict[str, Any],
) -> None:
    """Dari halaman KRS utama, klik 'Tambah Matakuliah' untuk membuka daftar pilihan."""
    log = get_logger("submitter")
    krs = selectors.get("krs") or {}
    tambah = krs.get("tambah_button") or "input[name='btnProses'][value='Tambah Matakuliah']"

    locator = page.locator(tambah).first
    if await locator.count() == 0:
        raise SubmitError("Tombol 'Tambah Matakuliah' tidak ditemukan di halaman KRS")

    log.info("Klik 'Tambah Matakuliah'")
    await locator.click()
    await page.wait_for_load_state("domcontentloaded")
    await asyncio.sleep(ACTION_DELAY)


async def _build_checkbox_map(page: Page) -> dict[tuple[str, str], str]:
    """Peta (kode_mk, kelas) -> value checkbox dari halaman daftar MK ditawarkan.

    Tabel: No | checkbox | Kelas | Mata Kuliah | Jadwal Kuliah | ... | Sks
    Kode MK harus diekstrak dari kolom Mata Kuliah (format "Nama MK" tanpa kode)
    atau dari kolom Kelas (yang berisi kode prodi). Ternyata kode MK TIDAK ada
    di tabel ini — hanya nama MK. Jadi kita cocokkan via nama MK.
    """
    return await page.evaluate(
        """() => {
            const map = {};
            const tables = document.querySelectorAll('table.table-common');
            for (const table of tables) {
                for (const tr of table.querySelectorAll('tr')) {
                    const tds = tr.querySelectorAll('td');
                    if (tds.length < 7) continue;
                    const cb = tds[1].querySelector("input[type='checkbox']");
                    if (!cb) continue;
                    const kelas = (tds[2].innerText || '').trim();
                    const namaMK = (tds[3].innerText || '').trim();
                    const jadwal = (tds[4].innerText || '').trim();
                    const sks = (tds[6].innerText || '').trim();
                    map[kelas + '|' + namaMK] = {
                        value: cb.value,
                        kelas, namaMK, jadwal, sks,
                    };
                }
            }
            return map;
        }"""
    )


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


async def _check_selected_courses(
    page: Page,
    selected: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Centang checkbox untuk setiap MK terpilih, return list yang berhasil dicentang."""
    log = get_logger("submitter")
    checkbox_map = await _build_checkbox_map(page)

    matched: list[dict[str, Any]] = []
    for course in selected:
        code = str(course.get("code") or "").upper()
        name = str(course.get("name") or "")
        class_name = str(course.get("class_name") or "")
        sks = str(course.get("sks") or "")

        # Cari checkbox yang cocok: match kelas + nama MK
        cb_value = None
        for key, info in checkbox_map.items():
            kelas_part = info["kelas"]
            nama_part = info["namaMK"]

            # Match via kelas
            if class_name and kelas_part == class_name:
                # Verifikasi nama MK mirip
                if _normalize(name) in _normalize(nama_part) or _normalize(nama_part) in _normalize(name):
                    cb_value = info["value"]
                    log.info(f"Match: {code} {class_name} -> '{nama_part}' kelas '{kelas_part}'")
                    break

        if not cb_value:
            # Fallback: match hanya nama MK + SKS
            for key, info in checkbox_map.items():
                if _normalize(name) in _normalize(info["namaMK"]) or _normalize(info["namaMK"]) in _normalize(name):
                    if info["sks"] == sks and info["kelas"] == class_name:
                        cb_value = info["value"]
                        log.info(f"Match (fallback): {code} -> '{info['namaMK']}' kelas '{info['kelas']}'")
                        break

        if not cb_value:
            log.warning(f"{code} kelas {class_name} '{name}': checkbox tidak ditemukan")
            continue

        # Centang checkbox
        selector = f"input[type='checkbox'][value='{cb_value}']"
        checkbox = page.locator(selector).first
        if await checkbox.count() == 0:
            log.warning(f"{code}: checkbox value '{cb_value[:20]}...' tidak ada di DOM")
            continue

        if not await checkbox.is_checked():
            await checkbox.check()
            log.info(f"{code} kelas {class_name}: dicentang")
        else:
            log.info(f"{code} kelas {class_name}: sudah tercentang")

        matched.append(course)
        await asyncio.sleep(0.2)

    return matched


async def submit_selected_courses(
    page: Page,
    selected: list[dict[str, Any]],
    *,
    dry_run: bool = False,
    auto_confirm: bool = False,
    selectors: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Pilih dan submit MK ke SIAKAD.

    Alur:
      1. Navigasi ke halaman KRS
      2. Klik "Tambah Matakuliah"
      3. Centang checkbox MK terpilih
      4. Klik "Tambah"
      5. Verifikasi KRS
    """
    log = get_logger("submitter")
    data = selectors or load_selectors()

    await navigate_to_krs(page, data)
    period = await detect_krs_period(page, data)
    ok, reason = preflight_submit(
        dry_run=dry_run,
        selected=selected,
        period=period,
        selectors=data,
    )
    if not ok:
        raise SubmitError(reason)
    if not confirm_submit(selected, auto_confirm=auto_confirm):
        raise SubmitError("Submit dibatalkan user")

    before = screenshot_path("submitter", "before")
    await page.screenshot(path=str(before), full_page=True)

    krs = data.get("krs") or {}
    submit_sel = krs.get("submit") or "input[name='btnAdd'][value='Tambah']"

    last_error: Exception | None = None
    for attempt in range(1, MAX_SUBMIT_RETRIES + 1):
        try:
            log.info(f"Submit attempt {attempt}/{MAX_SUBMIT_RETRIES}")

            # Step 1: Navigasi ke KRS dan klik "Tambah Matakuliah"
            await navigate_to_krs(page, data)
            await _navigate_to_tambah_mk(page, data)

            step2 = screenshot_path("submitter", f"tambah_mk_page_{attempt}")
            await page.screenshot(path=str(step2), full_page=True)

            # Step 2: Centang checkbox MK terpilih
            matched = await _check_selected_courses(page, selected)
            if not matched:
                raise SubmitError("Tidak ada MK yang berhasil dicentang")

            step3 = screenshot_path("submitter", f"checked_{attempt}")
            await page.screenshot(path=str(step3), full_page=True)

            # Step 3: Klik "Tambah"
            log.info(f"Klik 'Tambah' ({len(matched)} MK dicentang)")
            submit_btn = page.locator(submit_sel).first
            if await submit_btn.count() == 0:
                raise SubmitError(f"Tombol submit '{submit_sel}' tidak ditemukan")

            await submit_btn.click()
            await page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(ACTION_DELAY * 2)

            after = screenshot_path("submitter", f"after_{attempt}")
            await page.screenshot(path=str(after), full_page=True)

            # Step 4: Cek error
            body = " ".join((await page.locator("body").inner_text()).split()).lower()
            error_sel = krs.get("error_message") or "#warning"
            if await page.locator(error_sel).count() > 0:
                err_text = " ".join((await page.locator(error_sel).inner_text()).split())
                if err_text and any(w in err_text.lower() for w in ("gagal", "error", "tidak")):
                    raise SubmitError(f"SIAKAD error: {err_text}")

            # Step 5: Verifikasi
            verified = await scrape_existing_krs(page, selectors=data, save=True)
            verified_codes = {
                str(item.get("code", "")).upper()
                for item in (verified.get("courses") or [])
            }
            submitted_codes = [str(c.get("code") or "").upper() for c in matched]
            missing = [code for code in submitted_codes if code not in verified_codes]

            result = {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "status": "SUCCESS" if not missing else "PARTIAL",
                "submitted_codes": submitted_codes,
                "failed_mark": [
                    {"code": str(c.get("code")), "reason": "checkbox_not_found"}
                    for c in selected
                    if c not in matched
                ],
                "missing_after_verify": missing,
                "period": period,
                "screenshots": {
                    "before": str(before),
                    "tambah_mk": str(step2),
                    "checked": str(step3),
                    "after": str(after),
                },
                "verified_total_sks": verified.get("total_sks"),
                "allow_submit": True,
            }
            log.info(f"Submit selesai status={result['status']}")
            if missing:
                log.warning(f"MK belum masuk KRS: {missing}")
            return result

        except Exception as exc:
            last_error = exc
            log.warning(f"Submit attempt {attempt} gagal: {exc}")
            if attempt < MAX_SUBMIT_RETRIES:
                await asyncio.sleep(ACTION_DELAY * attempt)
            else:
                break

    raise SubmitError(str(last_error) if last_error else "Submit gagal")
