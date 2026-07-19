from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterable

from loguru import logger

from bot.config import BOT_LOG_PATH, LOG_LEVEL, PROJECT_ROOT, SCREENSHOTS_DIR, ensure_runtime_dirs

_DAY_ALIASES = {
    "senin": "Senin",
    "selasa": "Selasa",
    "rabu": "Rabu",
    "kamis": "Kamis",
    "jumat": "Jumat",
    "jum'at": "Jumat",
    "sabtu": "Sabtu",
    "minggu": "Minggu",
}

_TIME_RANGE_RE = re.compile(
    r"(?P<day>[A-Za-z' ]+?)\s+(?P<start>\d{1,2}[:.]\d{2})\s*[-–—]\s*(?P<end>\d{1,2}[:.]\d{2})",
    re.IGNORECASE,
)


def setup_logger(level: str | None = None, log_file: Path | None = None) -> None:
    ensure_runtime_dirs()
    log_level = (level or LOG_LEVEL).upper()
    target_file = log_file or BOT_LOG_PATH

    logger.remove()
    logger.add(
        sys.stderr,
        level=log_level,
        format="<green>[{time:YYYY-MM-DD HH:mm:ss}]</green> <level>[{level}]</level> <cyan>[{extra[module]}]</cyan> {message}",
        colorize=True,
        filter=lambda record: record["extra"].setdefault("module", "bot") or True,
    )
    logger.add(
        target_file,
        level=log_level,
        format="[{time:YYYY-MM-DD HH:mm:ss}] [{level}] [{extra[module]}] {message}",
        encoding="utf-8",
        rotation="5 MB",
        retention="14 days",
    )


def get_logger(module: str = "bot"):
    return logger.bind(module=module)


def ensure_parent(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def load_json(path: Path | str) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: Path | str, data: Any, indent: int = 2) -> Path:
    file_path = ensure_parent(Path(path))
    with file_path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=indent)
        handle.write("\n")
    return file_path


def time_to_minutes(value: str) -> int:
    normalized = value.strip().replace(".", ":")
    hour_str, minute_str = normalized.split(":")
    hour = int(hour_str)
    minute = int(minute_str)
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        raise ValueError(f"Invalid time: {value}")
    return hour * 60 + minute


def minutes_to_time(value: int) -> str:
    hour, minute = divmod(value, 60)
    return f"{hour:02d}:{minute:02d}"


def normalize_day(day: str) -> str:
    key = day.strip().lower()
    if key in _DAY_ALIASES:
        return _DAY_ALIASES[key]
    return day.strip().title()


def parse_schedule(raw: str) -> dict[str, Any]:
    text = " ".join(raw.strip().split())
    match = _TIME_RANGE_RE.search(text)
    if not match:
        raise ValueError(f"Format jadwal tidak dikenali: {raw!r}")

    day = normalize_day(match.group("day"))
    start = time_to_minutes(match.group("start"))
    end = time_to_minutes(match.group("end"))
    if end <= start:
        raise ValueError(f"Jam selesai harus setelah jam mulai: {raw!r}")

    return {
        "day": day,
        "start": start,
        "end": end,
        "raw": f"{day} {minutes_to_time(start)}-{minutes_to_time(end)}",
    }


def parse_schedules(raw_value: str | Iterable[str]) -> list[dict[str, Any]]:
    if isinstance(raw_value, str):
        chunks = re.split(r"[;|/]+", raw_value)
        items = [chunk.strip() for chunk in chunks if chunk.strip()]
    else:
        items = [str(item).strip() for item in raw_value if str(item).strip()]
    return [parse_schedule(item) for item in items]


def schedules_conflict(schedule_a: dict[str, Any], schedule_b: dict[str, Any]) -> bool:
    if schedule_a["day"] != schedule_b["day"]:
        return False
    return schedule_a["start"] < schedule_b["end"] and schedule_a["end"] > schedule_b["start"]


def is_schedule_conflict(
    new_schedules: dict[str, Any] | list[dict[str, Any]],
    existing_schedules: list[dict[str, Any]] | list[list[dict[str, Any]]],
) -> bool:
    new_list = new_schedules if isinstance(new_schedules, list) else [new_schedules]
    flat_existing: list[dict[str, Any]] = []
    for item in existing_schedules:
        if isinstance(item, list):
            flat_existing.extend(item)
        else:
            flat_existing.append(item)

    for new_item in new_list:
        for existing in flat_existing:
            if schedules_conflict(new_item, existing):
                return True
    return False


def total_sks(courses: Iterable[dict[str, Any]]) -> int:
    return sum(int(course.get("sks", 0)) for course in courses)


def can_add_sks(current_sks: int, course_sks: int, target_sks: int) -> bool:
    return current_sks + course_sks <= target_sks


def timestamp_slug() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def screenshot_path(module: str, action: str) -> Path:
    ensure_runtime_dirs()
    return SCREENSHOTS_DIR / f"{module}_{action}_{timestamp_slug()}.png"


async def with_retry(
    func: Callable[[], Any],
    max_retries: int = 3,
    delay: float = 2.0,
    module: str = "bot",
) -> Any:
    import asyncio

    log = get_logger(module)
    last_error: Exception | None = None
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as exc:
            last_error = exc
            log.warning(f"Percobaan {attempt + 1}/{max_retries} gagal: {exc}")
            if attempt < max_retries - 1:
                await asyncio.sleep(delay * (attempt + 1))
            else:
                raise
    if last_error:
        raise last_error
    raise RuntimeError("with_retry gagal tanpa exception")


def format_selection_summary(report: dict[str, Any]) -> str:
    lines = [
        "========================================",
        "BOT SIAKAD — HASIL AKHIR",
        "========================================",
        f"Status: {report.get('status', 'UNKNOWN')}",
        "",
        "MK Existing:",
    ]

    existing = report.get("existing") or []
    if existing:
        for idx, course in enumerate(existing, start=1):
            lines.append(_format_course_line(idx, course))
    else:
        lines.append("- (tidak ada)")

    lines.extend(["", "MK Terpilih (baru):"])
    selected = report.get("selected") or []
    if selected:
        for idx, course in enumerate(selected, start=1):
            lines.append(_format_course_line(idx, course))
    else:
        lines.append("- (tidak ada)")

    total = report.get("total_sks", 0)
    target = report.get("target_sks", 23)
    lines.extend(["", f"Total SKS: {total} / {target}", "", "MK Gagal / Dilewati:"])

    skipped = report.get("skipped") or []
    if skipped:
        for item in skipped:
            lines.append(f"- {item.get('code', '?')}: {item.get('reason', 'unknown')}")
    else:
        lines.append("- (none)")

    lines.append("========================================")
    return "\n".join(lines)


def _format_course_line(index: int, course: dict[str, Any]) -> str:
    code = course.get("code", "?")
    name = course.get("name", "")
    class_name = course.get("class_name")
    sks = course.get("sks", 0)
    schedules = course.get("schedules") or []
    schedule_text = ""
    if schedules:
        schedule_text = ", ".join(item.get("raw", "") for item in schedules if item.get("raw"))

    parts = [f"{index}. {name} ({code})"]
    if class_name:
        parts.append(f"Kelas {class_name}")
    if schedule_text:
        parts.append(schedule_text)
    parts.append(f"{sks} SKS")
    return " - ".join(parts)


def load_last_report(path: Path | str | None = None) -> dict[str, Any] | None:
    from bot.config import SELECTION_REPORT_PATH

    report_path = Path(path) if path else SELECTION_REPORT_PATH
    if not report_path.exists():
        return None
    data = load_json(report_path)
    return data if isinstance(data, dict) else None
