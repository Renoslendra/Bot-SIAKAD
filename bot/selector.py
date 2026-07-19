from __future__ import annotations

from datetime import datetime
from typing import Any

from bot.config import (
    FALLBACK_COURSES,
    PRIORITY_COURSES,
    TARGET_SKS,
    USE_FALLBACK,
    priority_codes,
)
from bot.utils import can_add_sks, get_logger, is_schedule_conflict, total_sks


def _normalize_code(code: str | None) -> str:
    return str(code or "").strip().upper()


def _course_index(courses: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for course in courses:
        code = _normalize_code(course.get("code"))
        if code:
            indexed[code] = course
    return indexed


def _extract_schedules(item: dict[str, Any]) -> list[dict[str, Any]]:
    schedules = item.get("schedules") or []
    if isinstance(schedules, list):
        return [
            s
            for s in schedules
            if isinstance(s, dict) and "day" in s and "start" in s and "end" in s
        ]
    return []


def _class_candidates(course: dict[str, Any]) -> list[dict[str, Any]]:
    classes = course.get("classes")
    if isinstance(classes, list) and classes:
        return [c for c in classes if isinstance(c, dict)]
    if course.get("class_name") is not None or _extract_schedules(course):
        return [
            {
                "class_name": course.get("class_name"),
                "quota_remaining": course.get("quota_remaining", 1),
                "schedules": _extract_schedules(course),
            }
        ]
    return []


def _quota_ok(class_item: dict[str, Any]) -> bool:
    if "quota_remaining" not in class_item or class_item.get("quota_remaining") is None:
        return True
    try:
        return int(class_item.get("quota_remaining", 0)) > 0
    except (TypeError, ValueError):
        return False


def select_courses(
    available_courses: list[dict[str, Any]],
    *,
    existing_courses: list[dict[str, Any]] | None = None,
    priority: list[dict[str, Any]] | None = None,
    fallback: list[dict[str, Any]] | None = None,
    target_sks: int = TARGET_SKS,
    use_fallback: bool = USE_FALLBACK,
    period_open: bool = True,
) -> dict[str, Any]:
    log = get_logger("selector")
    existing = list(existing_courses or [])
    available_index = _course_index(available_courses)
    priority_list = list(priority if priority is not None else PRIORITY_COURSES)
    fallback_list = list(fallback if fallback is not None else FALLBACK_COURSES)

    existing_codes = {_normalize_code(item.get("code")) for item in existing}
    taken_schedules: list[dict[str, Any]] = []
    for item in existing:
        taken_schedules.extend(_extract_schedules(item))

    selected: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    current_sks = total_sks(existing)

    def process_catalog(catalog: list[dict[str, Any]], source: str) -> None:
        nonlocal current_sks
        for meta in catalog:
            code = _normalize_code(meta.get("code"))
            name = str(meta.get("name") or "")
            sks = int(meta.get("sks") or 0)
            if not code:
                continue

            if code in existing_codes or any(_normalize_code(s.get("code")) == code for s in selected):
                skipped.append({"code": code, "reason": "already_in_existing_krs"})
                continue

            if not period_open:
                skipped.append({"code": code, "reason": "krs_period_closed"})
                continue

            if current_sks >= target_sks:
                skipped.append({"code": code, "reason": "target_reached"})
                continue

            if not can_add_sks(current_sks, sks, target_sks):
                skipped.append({"code": code, "reason": "sks_cap_exceeded"})
                continue

            course = available_index.get(code)
            if not course:
                skipped.append({"code": code, "reason": "not_found_in_available"})
                continue

            course_name = str(course.get("name") or name)
            course_sks = int(course.get("sks") or sks)
            if not can_add_sks(current_sks, course_sks, target_sks):
                skipped.append({"code": code, "reason": "sks_cap_exceeded"})
                continue

            classes = _class_candidates(course)
            if not classes:
                skipped.append({"code": code, "reason": "no_class_data"})
                continue

            picked = None
            class_failures: list[str] = []
            for class_item in classes:
                class_name = class_item.get("class_name")
                schedules = _extract_schedules(class_item)
                if not _quota_ok(class_item):
                    class_failures.append(f"{class_name or '?'}:full")
                    continue
                if not schedules:
                    class_failures.append(f"{class_name or '?'}:no_schedule")
                    continue
                if is_schedule_conflict(schedules, taken_schedules):
                    class_failures.append(f"{class_name or '?'}:conflict")
                    continue
                picked = {
                    "code": code,
                    "name": course_name,
                    "sks": course_sks,
                    "class_name": class_name,
                    "schedules": schedules,
                    "source": source,
                    "quota_remaining": class_item.get("quota_remaining"),
                    "href": class_item.get("href"),
                }
                break

            if picked is None:
                if class_failures and all(item.endswith(":full") for item in class_failures):
                    reason = "all_classes_full"
                elif class_failures and all(item.endswith(":conflict") for item in class_failures):
                    reason = "all_classes_conflict"
                elif class_failures and all(item.endswith(":no_schedule") for item in class_failures):
                    reason = "no_schedule_data"
                else:
                    reason = "no_valid_class"
                skipped.append({"code": code, "reason": reason})
                log.warning(f"{code} dilewati — {reason}")
                continue

            selected.append(picked)
            taken_schedules.extend(picked["schedules"])
            current_sks += course_sks
            log.info(
                f"{code} kelas {picked.get('class_name')} terpilih — "
                f"{', '.join(s.get('raw', '') for s in picked['schedules'])} — {course_sks} SKS"
            )

    process_catalog(priority_list, "priority")
    if current_sks < target_sks and use_fallback:
        process_catalog(fallback_list, "fallback")

    selected_sks = total_sks(selected)
    existing_sks = total_sks(existing)
    total = existing_sks + selected_sks
    status = "SUCCESS" if total == target_sks else "PARTIAL"

    return {
        "status": status,
        "target_sks": target_sks,
        "total_sks": total,
        "existing_sks": existing_sks,
        "selected_sks": selected_sks,
        "existing": existing,
        "selected": selected,
        "skipped": skipped,
        "use_fallback": use_fallback,
        "period_open": period_open,
    }


def build_selection_report(
    *,
    existing_payload: dict[str, Any] | None = None,
    offered_payload: dict[str, Any] | None = None,
    selection_result: dict[str, Any] | None = None,
    notes: list[str] | None = None,
) -> dict[str, Any]:
    existing_payload = existing_payload or {}
    offered_payload = offered_payload or {}
    period = existing_payload.get("period") or {}
    existing = existing_payload.get("courses") or []
    offered = offered_payload.get("courses") or []

    if selection_result is None:
        selection_result = select_courses(
            offered,
            existing_courses=existing,
            period_open=bool(period.get("is_open", False)),
            use_fallback=USE_FALLBACK,
            target_sks=TARGET_SKS,
        )

    report_notes = list(notes or [])
    if not period.get("is_open", False):
        report_notes.append(f"Periode: {period.get('reason', 'KRS period closed')}")
        report_notes.append("Selection dijalankan dalam mode planning; submit diblokir.")
    if not offered:
        report_notes.append("Tidak ada offered course data untuk priority filter / schedule.")

    return {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "status": selection_result.get("status", "PARTIAL"),
        "target_sks": selection_result.get("target_sks", TARGET_SKS),
        "total_sks": selection_result.get("total_sks", total_sks(existing)),
        "selected_sks": selection_result.get("selected_sks", 0),
        "existing_sks": selection_result.get("existing_sks", total_sks(existing)),
        "existing": selection_result.get("existing", existing),
        "selected": selection_result.get("selected", []),
        "skipped": selection_result.get("skipped", []),
        "use_fallback": selection_result.get("use_fallback", USE_FALLBACK),
        "period": period,
        "period_open": selection_result.get("period_open", bool(period.get("is_open", False))),
        "profile": existing_payload.get("profile") or {},
        "offered_priority_hits": [item.get("code") for item in offered],
        "priority_codes": priority_codes(),
        "notes": report_notes,
        "artifacts": {
            "existing_krs": str(existing_payload.get("screenshot") or ""),
            "offered": str(offered_payload.get("screenshot") or ""),
        },
    }
