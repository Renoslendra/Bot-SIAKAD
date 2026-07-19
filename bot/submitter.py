from __future__ import annotations

import asyncio
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
    if not period.get("is_open", False):
        return False, f"Masa KRS belum buka: {period.get('reason', 'unknown')}"

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
        print(
            f"  {idx}. {course.get('code')} - {course.get('name')} - "
            f"Kelas {course.get('class_name') or '-'} - {course.get('sks')} SKS"
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


async def _select_course_on_page(
    page: Page,
    course: dict[str, Any],
    selectors: dict[str, Any],
) -> bool:
    log = get_logger("submitter")
    krs = selectors.get("krs") or {}
    select_control = krs.get("select_control")
    if not select_control:
        return False

    code = str(course.get("code") or "").upper()
    class_name = str(course.get("class_name") or "")
    rows = page.locator(krs.get("course_rows") or "table.table-common tr:has(td)")
    count = await rows.count()
    for idx in range(count):
        row = rows.nth(idx)
        text = " ".join((await row.inner_text()).split()).upper()
        if code not in text:
            continue
        control = row.locator(select_control)
        if await control.count() == 0:
            control = page.locator(select_control)
        if await control.count() == 0:
            log.warning(f"Kontrol pilih tidak ditemukan untuk {code}")
            return False

        target = control.first
        input_type = (await target.get_attribute("type") or "").lower()
        tag = await target.evaluate("el => el.tagName.toLowerCase()")
        if tag == "select":
            if class_name:
                try:
                    await target.select_option(label=class_name)
                except Exception:
                    await target.select_option(value=class_name)
            else:
                options = await target.locator("option").all_text_contents()
                if len(options) > 1:
                    await target.select_option(index=1)
        elif input_type in {"checkbox", "radio"}:
            if not await target.is_checked():
                await target.check()
        else:
            await target.click()
        await asyncio.sleep(ACTION_DELAY)
        log.info(f"MK {code} ditandai untuk submit")
        return True
    log.warning(f"Baris MK {code} tidak ditemukan di halaman KRS")
    return False


async def submit_selected_courses(
    page: Page,
    selected: list[dict[str, Any]],
    *,
    dry_run: bool = False,
    auto_confirm: bool = False,
    selectors: dict[str, Any] | None = None,
) -> dict[str, Any]:
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
    submit_sel = krs.get("submit")
    success_sel = krs.get("success_message")
    error_sel = krs.get("error_message")

    marked: list[str] = []
    failed_mark: list[dict[str, str]] = []
    for course in selected:
        success = await _select_course_on_page(page, course, data)
        if success:
            marked.append(str(course.get("code")))
        else:
            failed_mark.append(
                {"code": str(course.get("code")), "reason": "select_control_failed"}
            )

    if not marked:
        raise SubmitError("Tidak ada MK yang berhasil ditandai di UI KRS")

    last_error: Exception | None = None
    for attempt in range(1, MAX_SUBMIT_RETRIES + 1):
        try:
            log.info(f"Klik submit KRS (attempt {attempt}/{MAX_SUBMIT_RETRIES})")
            await page.locator(submit_sel).first.click()
            await page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(ACTION_DELAY)

            body = " ".join((await page.locator("body").inner_text()).split()).lower()
            if error_sel and await page.locator(error_sel).count() > 0:
                err_text = " ".join((await page.locator(error_sel).inner_text()).split())
                if err_text:
                    raise SubmitError(f"SIAKAD error: {err_text}")
            if any(token in body for token in ["gagal", "error", "tidak berhasil"]):
                if success_sel and await page.locator(success_sel).count() == 0:
                    raise SubmitError("Indikasi gagal terdeteksi di halaman setelah submit")

            after = screenshot_path("submitter", "after")
            await page.screenshot(path=str(after), full_page=True)
            verified = await scrape_existing_krs(page, selectors=data, save=True)
            verified_codes = {
                str(item.get("code", "")).upper()
                for item in (verified.get("courses") or [])
            }
            missing = [code for code in marked if code.upper() not in verified_codes]
            result = {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "status": "SUCCESS" if not missing and not failed_mark else "PARTIAL",
                "submitted_codes": marked,
                "failed_mark": failed_mark,
                "missing_after_verify": missing,
                "period": period,
                "screenshots": {"before": str(before), "after": str(after)},
                "verified_total_sks": verified.get("total_sks"),
                "allow_submit": True,
            }
            log.info(f"Submit selesai status={result['status']}")
            return result
        except Exception as exc:
            last_error = exc
            log.warning(f"Submit attempt {attempt} gagal: {exc}")
            if attempt < MAX_SUBMIT_RETRIES:
                await asyncio.sleep(ACTION_DELAY * attempt)
            else:
                break
    raise SubmitError(str(last_error) if last_error else "Submit gagal")
