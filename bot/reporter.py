from __future__ import annotations

from typing import Any

from bot.config import SELECTION_REPORT_PATH
from bot.utils import format_selection_summary, get_logger, save_json


def print_final_report(report: dict[str, Any]) -> None:
    print()
    print(format_selection_summary(report))
    notes = report.get("notes") or []
    if notes:
        print("Catatan:")
        for note in notes:
            print(f"- {note}")
    submit = report.get("submit") or {}
    if submit:
        print()
        print("Submit:")
        print(f"- status: {submit.get('status')}")
        print(f"- submitted: {', '.join(submit.get('submitted_codes') or []) or '-'}")
        missing = submit.get("missing_after_verify") or []
        if missing:
            print(f"- missing after verify: {', '.join(missing)}")
    print(f"Report path: {SELECTION_REPORT_PATH}")


def merge_submit_into_report(report: dict[str, Any], submit_result: dict[str, Any]) -> dict[str, Any]:
    updated = dict(report)
    updated["submit"] = submit_result
    notes = list(updated.get("notes") or [])
    notes.append(f"Submit status: {submit_result.get('status')}")
    updated["notes"] = notes
    return updated


def save_and_print_report(report: dict[str, Any]) -> str:
    path = save_json(SELECTION_REPORT_PATH, report)
    get_logger("reporter").info(f"Report disimpan: {path}")
    print_final_report(report)
    return str(path)
