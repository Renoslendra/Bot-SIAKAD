"""Submit Pemrograman Game IF 7A ke SIAKAD dan cetak hasil verifikasi."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from bot.config import load_selectors
from bot.login import login_with_browser
from bot.submitter import submit_selected_courses


async def main() -> int:
    session = await login_with_browser(headless=True, save_state=True)
    try:
        result = await submit_selected_courses(
            session.page,
            [
                {
                    "code": "IF2257",
                    "name": "Pemrograman Game",
                    "class_name": "IF 7A",
                    "sks": 3,
                    "schedules": [],
                }
            ],
            dry_run=False,
            auto_confirm=True,
            selectors=load_selectors(),
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["status"] == "SUCCESS" else 1
    finally:
        await session.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
