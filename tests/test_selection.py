from __future__ import annotations

from bot.utils import parse_schedule, parse_schedules
from bot.selector import select_courses


def _mk(code: str, name: str, sks: int, classes: list[dict]) -> dict:
    return {"code": code, "name": name, "sks": sks, "classes": classes}


def _cls(class_name: str, raw_schedules: str, quota: int = 5) -> dict:
    return {
        "class_name": class_name,
        "quota_remaining": quota,
        "schedules": parse_schedules(raw_schedules),
    }


def test_greedy_selects_in_priority_order_without_conflict() -> None:
    available = [
        _mk("IF2228", "Sistem Terdistribusi", 3, [_cls("A", "Senin 08:00-10:00")]),
        _mk("IF2229", "Proyek Perangkat Lunak", 3, [_cls("A", "Senin 10:00-12:00")]),
        _mk("IF2230", "Pembelajaran Mesin", 3, [_cls("A", "Selasa 08:00-10:00")]),
    ]
    priority = [
        {"code": "IF2228", "name": "Sistem Terdistribusi", "sks": 3},
        {"code": "IF2229", "name": "Proyek Perangkat Lunak", "sks": 3},
        {"code": "IF2230", "name": "Pembelajaran Mesin", "sks": 3},
    ]
    result = select_courses(
        available,
        existing_courses=[],
        priority=priority,
        fallback=[],
        target_sks=9,
        use_fallback=False,
        period_open=True,
    )
    assert result["status"] == "SUCCESS"
    assert result["total_sks"] == 9
    assert [c["code"] for c in result["selected"]] == ["IF2228", "IF2229", "IF2230"]


def test_skip_existing_codes() -> None:
    available = [
        _mk("IF2228", "Sistem Terdistribusi", 3, [_cls("A", "Senin 08:00-10:00")]),
        _mk("IF2229", "Proyek Perangkat Lunak", 3, [_cls("A", "Selasa 08:00-10:00")]),
    ]
    existing = [
        {
            "code": "IF2228",
            "name": "Sistem Terdistribusi",
            "sks": 3,
            "schedules": [parse_schedule("Senin 08:00-10:00")],
        }
    ]
    priority = [
        {"code": "IF2228", "name": "Sistem Terdistribusi", "sks": 3},
        {"code": "IF2229", "name": "Proyek Perangkat Lunak", "sks": 3},
    ]
    result = select_courses(
        available,
        existing_courses=existing,
        priority=priority,
        fallback=[],
        target_sks=6,
        use_fallback=False,
        period_open=True,
    )
    assert [c["code"] for c in result["selected"]] == ["IF2229"]
    assert any(s["code"] == "IF2228" and s["reason"] == "already_in_existing_krs" for s in result["skipped"])
    assert result["total_sks"] == 6


def test_class_fallback_on_conflict() -> None:
    available = [
        _mk(
            "IF2228",
            "Sistem Terdistribusi",
            3,
            [_cls("A", "Senin 08:00-10:00"), _cls("B", "Selasa 08:00-10:00")],
        )
    ]
    existing = [
        {
            "code": "OTHER",
            "name": "Other",
            "sks": 2,
            "schedules": [parse_schedule("Senin 09:00-11:00")],
        }
    ]
    result = select_courses(
        available,
        existing_courses=existing,
        priority=[{"code": "IF2228", "name": "Sistem Terdistribusi", "sks": 3}],
        fallback=[],
        target_sks=5,
        use_fallback=False,
        period_open=True,
    )
    assert result["selected"][0]["class_name"] == "B"
    assert result["status"] == "SUCCESS"


def test_all_classes_conflict() -> None:
    available = [
        _mk(
            "IF2228",
            "Sistem Terdistribusi",
            3,
            [_cls("A", "Senin 08:00-10:00"), _cls("B", "Senin 08:30-09:30")],
        )
    ]
    existing = [
        {
            "code": "OTHER",
            "name": "Other",
            "sks": 2,
            "schedules": [parse_schedule("Senin 08:00-10:00")],
        }
    ]
    result = select_courses(
        available,
        existing_courses=existing,
        priority=[{"code": "IF2228", "name": "Sistem Terdistribusi", "sks": 3}],
        fallback=[],
        target_sks=5,
        use_fallback=False,
        period_open=True,
    )
    assert result["selected"] == []
    assert any(s["reason"] == "all_classes_conflict" for s in result["skipped"])


def test_full_class_skipped_then_next() -> None:
    available = [
        _mk(
            "IF2228",
            "Sistem Terdistribusi",
            3,
            [_cls("A", "Senin 08:00-10:00", quota=0), _cls("B", "Senin 13:00-15:00", quota=2)],
        )
    ]
    result = select_courses(
        available,
        existing_courses=[],
        priority=[{"code": "IF2228", "name": "Sistem Terdistribusi", "sks": 3}],
        fallback=[],
        target_sks=3,
        use_fallback=False,
        period_open=True,
    )
    assert result["selected"][0]["class_name"] == "B"


def test_sks_cap() -> None:
    available = [
        _mk("IF2228", "Sistem Terdistribusi", 3, [_cls("A", "Senin 08:00-10:00")]),
        _mk("IF2229", "Proyek Perangkat Lunak", 3, [_cls("A", "Selasa 08:00-10:00")]),
    ]
    priority = [
        {"code": "IF2228", "name": "Sistem Terdistribusi", "sks": 3},
        {"code": "IF2229", "name": "Proyek Perangkat Lunak", "sks": 3},
    ]
    result = select_courses(
        available,
        existing_courses=[],
        priority=priority,
        fallback=[],
        target_sks=3,
        use_fallback=False,
        period_open=True,
    )
    assert [c["code"] for c in result["selected"]] == ["IF2228"]
    assert any(
        s["code"] == "IF2229" and s["reason"] in {"sks_cap_exceeded", "target_reached"}
        for s in result["skipped"]
    )
    assert result["total_sks"] == 3
    assert result["status"] == "SUCCESS"


def test_fallback_off_by_default_path() -> None:
    available = [_mk("IF2255", "Technopreneurship", 2, [_cls("A", "Rabu 08:00-10:00")])]
    result = select_courses(
        available,
        existing_courses=[],
        priority=[{"code": "IF2228", "name": "Sistem Terdistribusi", "sks": 3}],
        fallback=[{"code": "IF2255", "name": "Technopreneurship", "sks": 2}],
        target_sks=5,
        use_fallback=False,
        period_open=True,
    )
    assert result["selected"] == []
    assert any(s["code"] == "IF2228" and s["reason"] == "not_found_in_available" for s in result["skipped"])


def test_fallback_on_fills_remaining_sks() -> None:
    available = [
        _mk("IF2228", "Sistem Terdistribusi", 3, [_cls("A", "Senin 08:00-10:00")]),
        _mk("IF2255", "Technopreneurship", 2, [_cls("A", "Rabu 08:00-10:00")]),
    ]
    result = select_courses(
        available,
        existing_courses=[],
        priority=[{"code": "IF2228", "name": "Sistem Terdistribusi", "sks": 3}],
        fallback=[{"code": "IF2255", "name": "Technopreneurship", "sks": 2}],
        target_sks=5,
        use_fallback=True,
        period_open=True,
    )
    assert [c["code"] for c in result["selected"]] == ["IF2228", "IF2255"]
    assert result["selected"][1]["source"] == "fallback"
    assert result["status"] == "SUCCESS"


def test_period_closed_skips_all() -> None:
    available = [_mk("IF2228", "Sistem Terdistribusi", 3, [_cls("A", "Senin 08:00-10:00")])]
    result = select_courses(
        available,
        existing_courses=[],
        priority=[{"code": "IF2228", "name": "Sistem Terdistribusi", "sks": 3}],
        fallback=[],
        target_sks=3,
        use_fallback=False,
        period_open=False,
    )
    assert result["selected"] == []
    assert any(s["reason"] == "krs_period_closed" for s in result["skipped"])
    assert result["status"] == "PARTIAL"


def test_exact_boundary_allowed_between_selected() -> None:
    available = [
        _mk("IF2228", "Sistem Terdistribusi", 3, [_cls("A", "Senin 08:00-10:30")]),
        _mk("IF2229", "Proyek Perangkat Lunak", 3, [_cls("A", "Senin 10:30-12:00")]),
    ]
    priority = [
        {"code": "IF2228", "name": "Sistem Terdistribusi", "sks": 3},
        {"code": "IF2229", "name": "Proyek Perangkat Lunak", "sks": 3},
    ]
    result = select_courses(
        available,
        existing_courses=[],
        priority=priority,
        fallback=[],
        target_sks=6,
        use_fallback=False,
        period_open=True,
    )
    assert len(result["selected"]) == 2
    assert result["status"] == "SUCCESS"


def test_not_found_course() -> None:
    result = select_courses(
        [],
        existing_courses=[],
        priority=[{"code": "IF2228", "name": "Sistem Terdistribusi", "sks": 3}],
        fallback=[],
        target_sks=3,
        use_fallback=False,
        period_open=True,
    )
    assert any(s["reason"] == "not_found_in_available" for s in result["skipped"])


def test_no_double_enroll_same_code_in_available_only() -> None:
    available = [
        _mk(
            "IF2228",
            "Sistem Terdistribusi",
            3,
            [_cls("A", "Senin 08:00-10:00"), _cls("B", "Selasa 08:00-10:00")],
        )
    ]
    result = select_courses(
        available,
        existing_courses=[],
        priority=[
            {"code": "IF2228", "name": "Sistem Terdistribusi", "sks": 3},
            {"code": "IF2228", "name": "Sistem Terdistribusi", "sks": 3},
        ],
        fallback=[],
        target_sks=6,
        use_fallback=False,
        period_open=True,
    )
    assert len(result["selected"]) == 1
