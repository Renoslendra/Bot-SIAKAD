from __future__ import annotations

import argparse
import asyncio
import sys
from typing import Any

from bot import config
from bot.config import (
    ALLOW_SUBMIT,
    AUTO_CONFIRM,
    HEADLESS,
    LOG_LEVEL,
    SELECTION_REPORT_PATH,
    TARGET_SKS,
    USE_FALLBACK,
    ensure_runtime_dirs,
    fallback_codes,
    load_selectors,
    priority_codes,
    require_credentials,
    submit_allowed,
)
from bot.login import login_with_browser
from bot.reporter import merge_submit_into_report, print_final_report, save_and_print_report
from bot.scraper import (
    enrich_courses_with_schedules,
    merge_schedule_cache,
    scrape_existing_krs,
    scrape_offered_courses,
)
from bot.selector import build_selection_report, select_courses
from bot.submitter import preflight_submit, submit_selected_courses
from bot.utils import get_logger, load_last_report, setup_logger


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="Bot SIAKAD — auto course selection (Semester 5, 23 SKS)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Login + scrape + select tanpa submit")
    parser.add_argument("--status", action="store_true", help="Tampilkan report terakhir")
    parser.add_argument("--headless", action="store_true", help="Paksa browser headless")
    parser.add_argument("--headed", action="store_true", help="Paksa browser headed/GUI")
    parser.add_argument("--auto-confirm", action="store_true", help="Skip prompt konfirmasi submit")
    parser.add_argument("--run", action="store_true", help="Pipeline penuh (butuh ALLOW_SUBMIT=true)")
    parser.add_argument(
        "--refresh-schedules",
        action="store_true",
        help="Scrape ulang jadwal tiap kelas (lambat; abaikan cache)",
    )

    war = parser.add_argument_group("war mode")
    war.add_argument(
        "--war",
        action="store_true",
        help="Tunggu masa KRS dibuka lalu langsung pilih + submit",
    )
    war.add_argument(
        "--at",
        metavar="HH:MM",
        help="Jam mulai war, contoh: --at 08:00",
    )
    war.add_argument(
        "--lead",
        type=int,
        default=60,
        help="Bangun N detik sebelum jam target (default: 60)",
    )
    war.add_argument(
        "--interval",
        type=float,
        default=3.0,
        help="Jeda antar polling dalam detik (default: 3.0)",
    )
    war.add_argument(
        "--max-minutes",
        type=float,
        default=90.0,
        help="Batas waktu polling dalam menit (default: 90)",
    )
    war.add_argument(
        "--rounds",
        type=int,
        default=3,
        help="Maksimum ronde submit ulang (default: 3)",
    )
    war.add_argument(
        "--fallback",
        action="store_true",
        help="Izinkan MK fallback bila prioritas tidak cukup 23 SKS",
    )
    return parser


def parse_clock(value: str | None) -> Any:
    if not value:
        return None
    from datetime import time as dtime

    try:
        hour_str, minute_str = value.strip().split(":")
        return dtime(hour=int(hour_str), minute=int(minute_str))
    except (ValueError, AttributeError):
        raise SystemExit(f"Format --at tidak valid: {value!r}. Gunakan HH:MM, contoh 08:00")


def resolve_runtime_flags(args: argparse.Namespace) -> dict[str, Any]:
    if args.headed and args.headless:
        raise SystemExit("Pilih salah satu: --headed atau --headless")

    headless = HEADLESS
    if args.headed:
        headless = False
    elif args.headless:
        headless = True

    dry_run = bool(args.dry_run)
    run_mode = False
    if args.dry_run:
        dry_run = True
        run_mode = False
    elif args.run or args.auto_confirm:
        dry_run = False
        run_mode = True

    return {
        "dry_run": dry_run,
        "run_mode": run_mode,
        "status_only": bool(args.status),
        "headless": headless,
        "auto_confirm": bool(args.auto_confirm) or AUTO_CONFIRM,
        "refresh_schedules": bool(getattr(args, "refresh_schedules", False)),
    }


def print_status() -> int:
    report = load_last_report()
    if not report:
        get_logger("main").warning(f"Belum ada report di {SELECTION_REPORT_PATH}")
        print("Status: NO_REPORT")
        print(f"Path: {SELECTION_REPORT_PATH}")
        return 1
    print_final_report(report)
    return 0 if str(report.get("status", "")).upper() == "SUCCESS" else 1


def print_safety_banner(flags: dict[str, Any]) -> None:
    allowed, reason = submit_allowed(dry_run=flags["dry_run"])
    print("----------------------------------------")
    print("Bot SIAKAD — runtime config")
    print(f"Target SKS     : {TARGET_SKS}")
    print(f"USE_FALLBACK   : {USE_FALLBACK}")
    print(f"ALLOW_SUBMIT   : {ALLOW_SUBMIT}")
    print(f"AUTO_CONFIRM   : {flags['auto_confirm']}")
    print(f"HEADLESS       : {flags['headless']}")
    print(f"DRY_RUN        : {flags['dry_run']}")
    print(f"RUN_MODE       : {flags['run_mode']}")
    print(f"Submit allowed : {allowed} ({reason})")
    print("----------------------------------------")


async def run_pipeline_async(flags: dict[str, Any]) -> int:
    log = get_logger("main")
    ensure_runtime_dirs()
    print_safety_banner(flags)

    try:
        require_credentials()
        selectors = load_selectors()
    except config.ConfigError as exc:
        log.error(str(exc))
        print(str(exc))
        return 1

    dry_run = flags["dry_run"]
    if not dry_run and not flags["run_mode"]:
        print("Mode default aman: gunakan --dry-run dulu.")
        print("Contoh: python main.py --dry-run")
        print("Submit: set ALLOW_SUBMIT=true lalu python main.py --run --auto-confirm")
        return 1

    session = None
    try:
        mode_label = "dry-run" if dry_run else "run"
        log.info(f"Memulai {mode_label}: login → scrape → select" + ("" if dry_run else " → submit"))
        session = await login_with_browser(headless=flags["headless"], save_state=True)
        page = session.page

        existing = await scrape_existing_krs(page, save=True)
        offered = None
        try:
            codes = priority_codes() + (fallback_codes() if USE_FALLBACK else [])
            offered = await scrape_offered_courses(page, target_codes=codes, save=True)

            # Jadwal wajib ada agar bentrok terdeteksi. Pakai cache bila
            # tersedia (cepat); jika tidak, scrape langsung (lambat).
            if flags.get("refresh_schedules"):
                offered = await enrich_courses_with_schedules(page, offered, save=True)
            else:
                offered = merge_schedule_cache(offered)
                missing = sum(
                    1
                    for course in offered.get("courses", [])
                    for cls in course.get("classes", [])
                    if not cls.get("schedules")
                )
                if missing:
                    log.warning(
                        f"{missing} kelas tanpa jadwal — scrape langsung sebagai fallback"
                    )
                    offered = await enrich_courses_with_schedules(page, offered, save=True)
        except Exception as exc:
            log.warning(f"Scrape Informasi Matakuliah dilewati/gagal: {exc}")

        period = (existing or {}).get("period") or {}
        offered_courses = (offered or {}).get("courses") or []
        selection = select_courses(
            offered_courses,
            existing_courses=(existing or {}).get("courses") or [],
            period_open=bool(period.get("is_open", False)),
            use_fallback=USE_FALLBACK,
            target_sks=TARGET_SKS,
        )
        report = build_selection_report(
            existing_payload=existing or {},
            offered_payload=offered or {},
            selection_result=selection,
            notes=[f"Mode: {mode_label}", "Pipeline: login + scrape + selection engine."],
        )

        if dry_run:
            report.setdefault("notes", []).append("Submit tidak dijalankan (dry-run).")
            save_and_print_report(report)
            if not period.get("is_open", False):
                print()
                print("CATATAN: Masa KRS belum buka / UI pilih-submit belum tersedia.")
            return 0 if report.get("status") == "SUCCESS" else 1

        selected = selection.get("selected") or []
        ok, reason = preflight_submit(
            dry_run=False,
            selected=selected,
            period=period,
            selectors=selectors,
        )
        if not ok:
            log.warning(reason)
            report.setdefault("notes", []).append(f"Submit diblokir: {reason}")
            report["submit"] = {"status": "BLOCKED", "reason": reason}
            save_and_print_report(report)
            print()
            print(f"Submit diblokir: {reason}")
            return 1

        try:
            submit_result = await submit_selected_courses(
                page,
                selected,
                dry_run=False,
                auto_confirm=flags["auto_confirm"],
                selectors=selectors,
            )
            report = merge_submit_into_report(report, submit_result)
            save_and_print_report(report)
            missing = submit_result.get("missing_after_verify") or []
            return 0 if submit_result.get("status") == "SUCCESS" and not missing else 1
        except config.SubmitError as exc:
            log.error(str(exc))
            report.setdefault("notes", []).append(f"Submit error: {exc}")
            report["submit"] = {"status": "FAILED", "reason": str(exc)}
            save_and_print_report(report)
            return 1
    except Exception as exc:
        log.error(f"Pipeline gagal: {exc}")
        print(f"ERROR: {exc}")
        return 1
    finally:
        if session is not None:
            await session.close()
            log.info("Browser ditutup")


def run_pipeline(flags: dict[str, Any]) -> int:
    return asyncio.run(run_pipeline_async(flags))


def run_war_mode(args: argparse.Namespace, flags: dict[str, Any]) -> int:
    from bot.war import run_war

    log = get_logger("main")
    ensure_runtime_dirs()

    try:
        require_credentials()
        load_selectors()
    except config.ConfigError as exc:
        log.error(str(exc))
        print(str(exc))
        return 1

    start_at = parse_clock(args.at)
    use_fallback = True if args.fallback else USE_FALLBACK
    allowed, reason = submit_allowed(dry_run=flags["dry_run"])

    print("----------------------------------------")
    print("Bot SIAKAD — WAR MODE")
    print(f"Target SKS     : {TARGET_SKS}")
    print(f"Mulai jam      : {args.at or 'sekarang'}")
    print(f"Lead time      : {args.lead}s")
    print(f"Polling        : tiap {args.interval}s (maks {args.max_minutes} menit)")
    print(f"Ronde submit   : {args.rounds}")
    print(f"USE_FALLBACK   : {use_fallback}")
    print(f"ALLOW_SUBMIT   : {ALLOW_SUBMIT}")
    print(f"HEADLESS       : {flags['headless']}")
    print(f"DRY_RUN        : {flags['dry_run']}")
    print(f"Submit allowed : {allowed} ({reason})")
    print("----------------------------------------")

    if not flags["dry_run"] and not ALLOW_SUBMIT:
        print()
        print("ALLOW_SUBMIT=false — war mode akan berhenti sebelum submit.")
        print("Set ALLOW_SUBMIT=true di .env untuk submit sungguhan.")
        return 1

    return asyncio.run(
        run_war(
            headless=flags["headless"],
            start_at=start_at,
            lead_seconds=args.lead,
            interval=args.interval,
            max_minutes=args.max_minutes,
            use_fallback=use_fallback,
            target_sks=TARGET_SKS,
            refresh_schedules=flags["refresh_schedules"],
            max_rounds=args.rounds,
            dry_run=flags["dry_run"],
        )
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    flags = resolve_runtime_flags(args)
    setup_logger(LOG_LEVEL)
    get_logger("main").info("Bot SIAKAD start")
    if flags["status_only"]:
        return print_status()
    if args.war:
        return run_war_mode(args, flags)
    return run_pipeline(flags)


if __name__ == "__main__":
    sys.exit(main())
