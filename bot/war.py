"""War mode: tunggu masa KRS dibuka, lalu langsung rebut jadwal.

Alur:
  1. Login lebih awal dan pertahankan sesi tetap hidup.
  2. Polling halaman KRS sampai kontrol pilih/submit muncul.
  3. Begitu terbuka: auto-detect selector, pilih MK, submit, verifikasi.
  4. Bila submit sebagian gagal, coba lagi untuk MK yang belum masuk.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, time as dtime
from typing import Any

from playwright.async_api import Page

from bot import config
from bot.autodetect import autodetect_and_persist
from bot.config import (
    TARGET_SKS,
    USE_FALLBACK,
    fallback_codes,
    load_selectors,
    priority_codes,
)
from bot.login import login_with_browser
from bot.reporter import merge_submit_into_report, save_and_print_report
from bot.scraper import (
    detect_krs_period,
    enrich_courses_with_schedules,
    merge_schedule_cache,
    navigate_to_krs,
    scrape_existing_krs,
    scrape_offered_courses,
)
from bot.selector import build_selection_report, select_courses
from bot.submitter import submit_selected_courses
from bot.utils import get_logger


async def wait_until_clock(target: dtime, *, lead_seconds: int = 30) -> None:
    """Tidur sampai mendekati jam target (default: 30 detik sebelumnya)."""
    log = get_logger("war")
    now = datetime.now()
    target_dt = now.replace(
        hour=target.hour, minute=target.minute, second=0, microsecond=0
    )
    if target_dt <= now:
        log.info(f"Jam target {target.strftime('%H:%M')} sudah lewat — lanjut sekarang")
        return

    wake_at = target_dt.timestamp() - lead_seconds
    delay = wake_at - now.timestamp()
    if delay <= 0:
        return

    log.info(
        f"Menunggu sampai {target.strftime('%H:%M')} "
        f"(bangun {lead_seconds}s lebih awal, tidur {delay / 60:.1f} menit)"
    )
    while True:
        remaining = wake_at - datetime.now().timestamp()
        if remaining <= 0:
            break
        await asyncio.sleep(min(remaining, 30))
        if remaining > 60:
            log.info(f"Sisa {remaining / 60:.1f} menit")
    log.info("Waktu target hampir tiba — bersiap")


async def poll_until_open(
    page: Page,
    *,
    selectors: dict[str, Any],
    interval: float = 3.0,
    max_minutes: float = 90.0,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Refresh halaman KRS sampai kontrol pilih/submit tersedia."""
    log = get_logger("war")
    deadline = datetime.now().timestamp() + max_minutes * 60
    attempt = 0

    while datetime.now().timestamp() < deadline:
        attempt += 1
        try:
            await navigate_to_krs(page, selectors)
            period = await detect_krs_period(page, selectors)
            selectors, detected = await autodetect_and_persist(
                page, selectors=selectors, save=True
            )

            has_controls = (
                bool(detected.get("select_control")) and bool(detected.get("submit"))
            ) or bool(detected.get("has_tambah_button"))
            if has_controls:
                log.info(f"KRS TERBUKA pada percobaan #{attempt}")
                return selectors, period

            if attempt % 10 == 1:
                log.info(
                    f"#{attempt} belum buka — {period.get('reason', '')[:60]} "
                    f"(pilih={bool(detected.get('select_control'))}, "
                    f"submit={bool(detected.get('submit'))})"
                )
        except Exception as exc:
            log.warning(f"#{attempt} polling error: {exc}")
            try:
                await page.goto(config.SIAKAD_URL, wait_until="domcontentloaded")
            except Exception:
                pass

        await asyncio.sleep(interval)

    raise config.BotSIAKADError(
        f"KRS belum terbuka setelah {max_minutes} menit — dibatalkan"
    )


async def _gather_offering(
    page: Page,
    *,
    selectors: dict[str, Any],
    use_fallback: bool,
    refresh_schedules: bool,
) -> dict[str, Any]:
    log = get_logger("war")
    codes = priority_codes() + (fallback_codes() if use_fallback else [])
    offered = await scrape_offered_courses(page, target_codes=codes, save=True)

    if refresh_schedules:
        return await enrich_courses_with_schedules(page, offered, save=True)

    offered = merge_schedule_cache(offered)
    missing = sum(
        1
        for course in offered.get("courses", [])
        for cls in course.get("classes", [])
        if not cls.get("schedules")
    )
    if missing:
        log.warning(f"{missing} kelas tanpa jadwal — melengkapi dari halaman detail")
        offered = await enrich_courses_with_schedules(page, offered, save=True)
    return offered


async def run_war(
    *,
    headless: bool = False,
    start_at: dtime | None = None,
    lead_seconds: int = 30,
    interval: float = 3.0,
    max_minutes: float = 90.0,
    use_fallback: bool | None = None,
    target_sks: int = TARGET_SKS,
    refresh_schedules: bool = False,
    max_rounds: int = 3,
    dry_run: bool = False,
) -> int:
    """Jalankan prosedur war KRS end-to-end."""
    log = get_logger("war")
    fallback_on = USE_FALLBACK if use_fallback is None else use_fallback

    session = None
    try:
        selectors = load_selectors()

        log.info("Login lebih awal agar sesi siap sebelum jam buka")
        session = await login_with_browser(headless=headless, save_state=True)
        page = session.page

        # Siapkan cache jadwal selagi menunggu — hemat waktu saat war.
        log.info("Menyiapkan data penawaran + jadwal")
        offered = await _gather_offering(
            page,
            selectors=selectors,
            use_fallback=fallback_on,
            refresh_schedules=refresh_schedules,
        )

        if start_at is not None:
            await wait_until_clock(start_at, lead_seconds=lead_seconds)

        log.info("Mulai polling halaman KRS")
        selectors, period = await poll_until_open(
            page, selectors=selectors, interval=interval, max_minutes=max_minutes
        )

        report: dict[str, Any] = {}
        for round_no in range(1, max_rounds + 1):
            log.info(f"=== Ronde {round_no}/{max_rounds} ===")

            existing = await scrape_existing_krs(page, selectors=selectors, save=True)
            existing_courses = existing.get("courses") or []
            current_sks = existing.get("total_sks") or 0
            log.info(f"KRS saat ini: {len(existing_courses)} MK / {current_sks} SKS")

            if current_sks >= target_sks:
                log.info(f"Target {target_sks} SKS tercapai")
                report = build_selection_report(
                    existing_payload=existing,
                    offered_payload=offered,
                    selection_result=select_courses(
                        offered.get("courses") or [],
                        existing_courses=existing_courses,
                        period_open=True,
                        use_fallback=fallback_on,
                        target_sks=target_sks,
                    ),
                    notes=[f"War mode ronde {round_no}", "Target tercapai"],
                )
                save_and_print_report(report)
                return 0

            # Kuota berubah cepat saat war — segarkan sebelum memilih ulang.
            if round_no > 1:
                offered = await _gather_offering(
                    page,
                    selectors=selectors,
                    use_fallback=fallback_on,
                    refresh_schedules=False,
                )

            selection = select_courses(
                offered.get("courses") or [],
                existing_courses=existing_courses,
                period_open=True,
                use_fallback=fallback_on,
                target_sks=target_sks,
            )
            report = build_selection_report(
                existing_payload=existing,
                offered_payload=offered,
                selection_result=selection,
                notes=[f"War mode ronde {round_no}"],
            )

            selected = selection.get("selected") or []
            if not selected:
                log.warning("Tidak ada MK baru yang bisa dipilih")
                save_and_print_report(report)
                return 1

            log.info(f"Akan submit {len(selected)} MK / {selection.get('selected_sks')} SKS")
            for item in selected:
                sched = ", ".join(s.get("raw", "") for s in item.get("schedules") or [])
                log.info(f"  {item['code']} {item.get('class_name')} — {sched}")

            if dry_run:
                report.setdefault("notes", []).append("Dry-run: submit dilewati")
                save_and_print_report(report)
                return 0

            try:
                submit_result = await submit_selected_courses(
                    page,
                    selected,
                    dry_run=False,
                    auto_confirm=True,
                    selectors=selectors,
                )
                report = merge_submit_into_report(report, submit_result)
                save_and_print_report(report)

                missing = submit_result.get("missing_after_verify") or []
                if submit_result.get("status") == "SUCCESS" and not missing:
                    log.info("Submit sukses penuh")
                    return 0
                log.warning(f"Submit sebagian — belum masuk: {missing}")
            except config.SubmitError as exc:
                log.error(f"Submit ronde {round_no} gagal: {exc}")
                report.setdefault("notes", []).append(f"Ronde {round_no}: {exc}")

            await asyncio.sleep(2.0)

        log.warning(f"Selesai {max_rounds} ronde tanpa mencapai target penuh")
        if report:
            save_and_print_report(report)
        return 1

    except Exception as exc:
        log.error(f"War mode gagal: {exc}")
        print(f"ERROR: {exc}")
        return 1
    finally:
        if session is not None:
            await session.close()
            log.info("Browser ditutup")
