from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"

load_dotenv(PROJECT_ROOT / ".env")


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


TARGET_SKS = 23
USE_FALLBACK = _env_bool("USE_FALLBACK", False)
ALLOW_SUBMIT = _env_bool("ALLOW_SUBMIT", False)
AUTO_CONFIRM = _env_bool("AUTO_CONFIRM", False)
HEADLESS = _env_bool("HEADLESS", True)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

SIAKAD_USERNAME = os.getenv("SIAKAD_USERNAME", "").strip()
SIAKAD_PASSWORD = os.getenv("SIAKAD_PASSWORD", "").strip()

SIAKAD_URL = "https://siakad.trunojoyo.ac.id"
SIAKAD_KRS_NAV_TEXT = "Kartu Rencana Studi"

SELECTORS_PATH = CONFIG_DIR / "selectors.json"
SELECTORS_EXAMPLE_PATH = CONFIG_DIR / "selectors.example.json"

LOGS_DIR = PROJECT_ROOT / "logs"
SCREENSHOTS_DIR = LOGS_DIR / "screenshots"
RECON_DIR = LOGS_DIR / "recon"
SESSION_PATH = LOGS_DIR / "session.json"
SCRAPED_COURSES_PATH = LOGS_DIR / "scraped_courses.json"
SCHEDULE_CACHE_PATH = LOGS_DIR / "schedule_cache.json"
EXISTING_KRS_PATH = LOGS_DIR / "existing_krs.json"
SELECTION_REPORT_PATH = LOGS_DIR / "selection_report.json"
BOT_LOG_PATH = LOGS_DIR / "bot.log"

MAX_LOGIN_RETRIES = 3
MAX_SUBMIT_RETRIES = 2
REQUEST_TIMEOUT = 30000
ACTION_DELAY = 1.0

PRIORITY_COURSES: list[dict[str, Any]] = [
    {"code": "IF2229", "name": "Proyek Perangkat Lunak", "sks": 3, "preferred_class": "IF 5A"},
    {"code": "IF2231", "name": "Proyek Sain Data", "sks": 3, "preferred_class": "IF 5C"},
    {"code": "IF2259", "name": "Pengolahan Citra", "sks": 3, "preferred_class": "IF 7B"},
    {"code": "IF2258", "name": "Basis Data III", "sks": 3, "preferred_class": "IF 7A"},
    {"code": "IF2230", "name": "Pembelajaran Mesin", "sks": 3, "preferred_class": "IF 5E"},
    {"code": "IF2232", "name": "Metodologi Penelitian", "sks": 2, "preferred_class": "IF 5D"},
    {"code": "IF2260", "name": "Pemodelan Proses Bisnis", "sks": 3, "preferred_class": "IF 7B"},
    {"code": "IF2228", "name": "Sistem Terdistribusi", "sks": 3, "preferred_class": "IF 5C"},
]

FALLBACK_COURSES: list[dict[str, Any]] = [
    {"code": "IF2255", "name": "Technopreneurship", "sks": 2},
    {"code": "IF2256", "name": "Komputasi Numerik", "sks": 3},
    {"code": "IF2257", "name": "Pemrograman Game", "sks": 3},
    {"code": "IF2258", "name": "Basis Data III", "sks": 3},
]


class BotSIAKADError(Exception):
    pass


class LoginError(BotSIAKADError):
    pass


class ScrapingError(BotSIAKADError):
    pass


class SelectionError(BotSIAKADError):
    pass


class SubmitError(BotSIAKADError):
    pass


class ConfigError(BotSIAKADError):
    pass


def priority_codes() -> list[str]:
    return [course["code"] for course in PRIORITY_COURSES]


def fallback_codes() -> list[str]:
    return [course["code"] for course in FALLBACK_COURSES]


def target_codes(include_fallback: bool | None = None) -> list[str]:
    use_fallback = USE_FALLBACK if include_fallback is None else include_fallback
    codes = priority_codes()
    if use_fallback:
        codes = codes + fallback_codes()
    return codes


def ensure_runtime_dirs() -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    RECON_DIR.mkdir(parents=True, exist_ok=True)


def require_credentials() -> None:
    if not SIAKAD_USERNAME or not SIAKAD_PASSWORD:
        raise ConfigError("SIAKAD_USERNAME / SIAKAD_PASSWORD belum diisi di file .env")


def load_selectors(path: Path | None = None) -> dict[str, Any]:
    import json

    selector_path = path or SELECTORS_PATH
    if not selector_path.exists():
        raise ConfigError(
            f"selectors.json belum ada di {selector_path}. "
            f"Copy dari {SELECTORS_EXAMPLE_PATH} lalu isi setelah recon."
        )
    with selector_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ConfigError("selectors.json harus berupa object JSON")
    return data


def submit_allowed(dry_run: bool = False) -> tuple[bool, str]:
    if dry_run:
        return False, "Mode dry-run aktif — submit diblokir"
    if not ALLOW_SUBMIT:
        return False, "ALLOW_SUBMIT=false — production submit terkunci"
    return True, "Submit diizinkan"
