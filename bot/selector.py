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


def _build_candidate(
    code: str,
    course: dict[str, Any],
    class_item: dict[str, Any],
    *,
    name: str,
    sks: int,
    source: str,
) -> dict[str, Any]:
    return {
        "code": code,
        "name": str(course.get("name") or name),
        "sks": int(course.get("sks") or sks),
        "class_name": class_item.get("class_name"),
        "schedules": _extract_schedules(class_item),
        "source": source,
        "quota_remaining": class_item.get("quota_remaining"),
        "href": class_item.get("href"),
    }


def _viable_classes(
    course: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Pisahkan kelas yang layak (ada kuota + ada jadwal) dari yang gagal."""
    viable: list[dict[str, Any]] = []
    failures: list[str] = []
    for class_item in _class_candidates(course):
        label = class_item.get("class_name") or "?"
        if not _quota_ok(class_item):
            failures.append(f"{label}:full")
            continue
        if not _extract_schedules(class_item):
            failures.append(f"{label}:no_schedule")
            continue
        viable.append(class_item)
    return viable, failures


def _failure_reason(failures: list[str], *, blocked_by_conflict: bool) -> str:
    if blocked_by_conflict:
        return "all_classes_conflict"
    if failures and all(item.endswith(":full") for item in failures):
        return "all_classes_full"
    if failures and all(item.endswith(":no_schedule") for item in failures):
        return "no_schedule_data"
    if failures and all(item.endswith(":conflict") for item in failures):
        return "all_classes_conflict"
    return "no_valid_class"


def _solve(
    units: list[dict[str, Any]],
    base_schedules: list[dict[str, Any]],
    base_sks: int,
    target_sks: int,
) -> list[dict[str, Any]]:
    """Cari kombinasi kelas terbaik lewat backtracking.

    Greedy first-fit dapat mengunci slot yang merupakan satu-satunya
    pilihan MK lain, sehingga total SKS jadi rendah. Solver ini mencoba
    kombinasi lain, mendahulukan MK dengan pilihan kelas paling sedikit
    (most-constrained-first) agar cabang mati terpangkas lebih awal.

    Skor: maksimalkan SKS; jika seri, dahulukan MK berprioritas awal.
    """
    ordered = sorted(units, key=lambda u: (len(u["classes"]), u["order"]))

    best: list[dict[str, Any]] = []
    best_score: tuple[int, int] = (0, 0)

    def priority_score(chosen: list[dict[str, Any]]) -> int:
        # Semakin awal urutan prioritas, semakin besar bobotnya.
        return sum(len(ordered) - unit["order"] for unit, _ in chosen)

    def recurse(
        index: int,
        chosen: list[tuple[dict[str, Any], dict[str, Any]]],
        schedules: list[dict[str, Any]],
        current_sks: int,
    ) -> None:
        nonlocal best, best_score

        remaining_possible = current_sks + sum(u["sks"] for u in ordered[index:])
        score = (current_sks, priority_score(chosen))
        if score > best_score:
            best_score = score
            best = [_build_candidate(
                unit["code"], unit["course"], class_item,
                name=unit["name"], sks=unit["sks"], source=unit["source"],
            ) for unit, class_item in chosen]

        if current_sks >= target_sks:
            return
        if index >= len(ordered):
            return
        # Pangkas: sisa MK tidak cukup untuk melampaui hasil terbaik.
        if remaining_possible < best_score[0]:
            return

        unit = ordered[index]
        if can_add_sks(current_sks, unit["sks"], target_sks):
            for class_item in unit["classes"]:
                item_schedules = _extract_schedules(class_item)
                if is_schedule_conflict(item_schedules, schedules):
                    continue
                recurse(
                    index + 1,
                    chosen + [(unit, class_item)],
                    schedules + item_schedules,
                    current_sks + unit["sks"],
                )

        # Cabang: lewati MK ini (mungkin membuka slot untuk MK lain).
        recurse(index + 1, chosen, schedules, current_sks)

    recurse(0, [], list(base_schedules), base_sks)
    return best


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

    skipped: list[dict[str, str]] = []
    existing_sks = total_sks(existing)

    catalog: list[tuple[dict[str, Any], str]] = [(m, "priority") for m in priority_list]
    if use_fallback:
        catalog += [(m, "fallback") for m in fallback_list]

    units: list[dict[str, Any]] = []
    seen_codes: set[str] = set()

    for meta, source in catalog:
        code = _normalize_code(meta.get("code"))
        if not code or code in seen_codes:
            continue
        seen_codes.add(code)

        name = str(meta.get("name") or "")
        sks = int(meta.get("sks") or 0)

        if code in existing_codes:
            skipped.append({"code": code, "reason": "already_in_existing_krs"})
            continue
        if not period_open:
            skipped.append({"code": code, "reason": "krs_period_closed"})
            continue

        course = available_index.get(code)
        if not course:
            skipped.append({"code": code, "reason": "not_found_in_available"})
            continue

        course_sks = int(course.get("sks") or sks)
        if not can_add_sks(existing_sks, course_sks, target_sks):
            skipped.append({"code": code, "reason": "sks_cap_exceeded"})
            continue

        classes = _class_candidates(course)
        if not classes:
            skipped.append({"code": code, "reason": "no_class_data"})
            continue

        viable, failures = _viable_classes(course)
        if not viable:
            reason = _failure_reason(failures, blocked_by_conflict=False)
            skipped.append({"code": code, "reason": reason})
            log.warning(f"{code} dilewati — {reason}")
            continue

        # Taruh preferred_class di urutan pertama agar solver coba duluan.
        preferred = str(meta.get("preferred_class") or "").strip()
        if preferred:
            viable.sort(key=lambda c: 0 if c.get("class_name") == preferred else 1)

        units.append(
            {
                "code": code,
                "name": name,
                "sks": course_sks,
                "source": source,
                "course": course,
                "classes": viable,
                "failures": failures,
                "order": len(units),
            }
        )

    selected = _solve(units, taken_schedules, existing_sks, target_sks)
    selected_codes = {item["code"] for item in selected}

    chosen_schedules: list[dict[str, Any]] = list(taken_schedules)
    for item in selected:
        chosen_schedules.extend(item["schedules"])
    solved_sks = existing_sks + total_sks(selected)

    for unit in units:
        if unit["code"] in selected_codes:
            continue

        blocked = all(
            is_schedule_conflict(_extract_schedules(c), chosen_schedules)
            for c in unit["classes"]
        )
        if blocked:
            reason = _failure_reason(unit["failures"], blocked_by_conflict=True)
        elif solved_sks >= target_sks:
            reason = "target_reached"
        elif not can_add_sks(solved_sks, unit["sks"], target_sks):
            reason = "sks_cap_exceeded"
        else:
            reason = _failure_reason(unit["failures"], blocked_by_conflict=False)

        skipped.append({"code": unit["code"], "reason": reason})
        log.warning(f"{unit['code']} dilewati — {reason}")

    # Urutkan hasil mengikuti urutan prioritas asli agar report konsisten.
    order_map = {unit["code"]: unit["order"] for unit in units}
    selected.sort(key=lambda item: order_map.get(item["code"], 0))

    for item in selected:
        log.info(
            f"{item['code']} kelas {item.get('class_name')} terpilih — "
            f"{', '.join(s.get('raw', '') for s in item['schedules'])} — {item['sks']} SKS"
        )

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
