"""Bangun cache jadwal semua kelas MK prioritas + fallback.

Dijalankan SEBELUM war KRS supaya saat war tinggal pakai cache
(hemat waktu: tidak perlu buka ~40 halaman detail kelas saat jam 08.00).

Jalankan: python scripts/build_schedule_cache.py
Output  : logs/scraped_courses.json (dengan jadwal terisi)
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from bot.config import LOG_LEVEL, ensure_runtime_dirs, fallback_codes, priority_codes
from bot.login import login_with_browser
from bot.scraper import enrich_courses_with_schedules, scrape_offered_courses
from bot.utils import get_logger, setup_logger


async def main() -> int:
    setup_logger(LOG_LEVEL)
    ensure_runtime_dirs()
    log = get_logger("cache")

    codes = priority_codes() + fallback_codes()
    log.info(f"Target: {len(codes)} MK -> {', '.join(codes)}")

    session = None
    try:
        session = await login_with_browser(headless=True, save_state=True)
        page = session.page

        payload = await scrape_offered_courses(page, target_codes=codes, save=True)
        found = {c["code"] for c in payload.get("courses", [])}
        missing = [c for c in codes if c not in found]
        if missing:
            log.warning(f"MK tidak ditemukan di penawaran: {', '.join(missing)}")

        payload = await enrich_courses_with_schedules(page, payload, save=True)

        print()
        print("=" * 72)
        print("CACHE JADWAL SELESAI")
        print("=" * 72)
        for course in payload.get("courses", []):
            print(f"\n{course['code']} - {course['name']} ({course['sks']} SKS)")
            for cls in course.get("classes", []):
                sched = ", ".join(s.get("raw", "") for s in cls.get("schedules") or [])
                quota = cls.get("quota_remaining")
                quota_text = f" | kuota: {quota}" if quota is not None else ""
                print(f"  - {cls.get('class_name'):<8} {sched or '(jadwal kosong)'}{quota_text}")
        print()
        print(f"Total MK: {len(payload.get('courses', []))}")
        print(f"Kelas ter-enrich: {payload.get('schedule_enriched_count', 0)}")
        return 0
    except Exception as exc:
        log.error(f"Gagal: {exc}")
        print(f"ERROR: {exc}")
        return 1
    finally:
        if session is not None:
            await session.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
