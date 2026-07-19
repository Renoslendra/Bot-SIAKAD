from __future__ import annotations

import pytest

from bot.utils import (
    can_add_sks,
    is_schedule_conflict,
    parse_schedule,
    parse_schedules,
    schedules_conflict,
    time_to_minutes,
    total_sks,
)


def test_time_to_minutes() -> None:
    assert time_to_minutes("08:00") == 480
    assert time_to_minutes("10:30") == 630
    assert time_to_minutes("13.00") == 780


def test_parse_schedule_basic() -> None:
    result = parse_schedule("Senin 08:00-10:30")
    assert result["day"] == "Senin"
    assert result["start"] == 480
    assert result["end"] == 630
    assert result["raw"] == "Senin 08:00-10:30"


def test_parse_schedule_with_dot_separator() -> None:
    result = parse_schedule("Selasa 13.00-15.30")
    assert result["day"] == "Selasa"
    assert result["start"] == 780
    assert result["end"] == 930


def test_parse_schedules_multi() -> None:
    result = parse_schedules("Senin 08:00-10:00; Rabu 10:00-12:00")
    assert len(result) == 2
    assert result[0]["day"] == "Senin"
    assert result[1]["day"] == "Rabu"


def test_overlap_same_day_is_conflict() -> None:
    a = parse_schedule("Senin 08:00-10:30")
    b = parse_schedule("Senin 09:00-11:00")
    assert schedules_conflict(a, b) is True
    assert is_schedule_conflict(a, [b]) is True


def test_exact_boundary_is_not_conflict() -> None:
    a = parse_schedule("Senin 08:00-10:30")
    b = parse_schedule("Senin 10:30-12:00")
    assert schedules_conflict(a, b) is False
    assert is_schedule_conflict(a, [b]) is False


def test_different_day_is_not_conflict() -> None:
    a = parse_schedule("Senin 08:00-10:30")
    b = parse_schedule("Selasa 08:00-10:30")
    assert schedules_conflict(a, b) is False
    assert is_schedule_conflict(a, [b]) is False


def test_partial_overlap_is_conflict() -> None:
    a = parse_schedule("Rabu 13:00-15:00")
    b = parse_schedule("Rabu 14:00-16:00")
    assert schedules_conflict(a, b) is True


def test_contained_interval_is_conflict() -> None:
    a = parse_schedule("Kamis 08:00-12:00")
    b = parse_schedule("Kamis 09:00-10:00")
    assert schedules_conflict(a, b) is True


def test_multi_slot_conflict_detection() -> None:
    new_slots = parse_schedules("Senin 08:00-10:00; Rabu 13:00-15:00")
    existing = parse_schedules("Selasa 08:00-10:00; Rabu 14:00-16:00")
    assert is_schedule_conflict(new_slots, existing) is True


def test_multi_slot_no_conflict() -> None:
    new_slots = parse_schedules("Senin 08:00-10:00; Rabu 13:00-15:00")
    existing = parse_schedules("Selasa 08:00-10:00; Rabu 15:00-17:00")
    assert is_schedule_conflict(new_slots, existing) is False


def test_nested_existing_schedule_lists() -> None:
    new_slot = parse_schedule("Jumat 10:00-12:00")
    existing_groups = [
        parse_schedules("Senin 08:00-10:00"),
        parse_schedules("Jumat 11:00-13:00"),
    ]
    assert is_schedule_conflict(new_slot, existing_groups) is True


def test_total_sks() -> None:
    courses = [{"code": "IF2228", "sks": 3}, {"code": "IF2232", "sks": 2}]
    assert total_sks(courses) == 5


def test_can_add_sks_boundary() -> None:
    assert can_add_sks(20, 3, 23) is True
    assert can_add_sks(21, 3, 23) is False
    assert can_add_sks(23, 0, 23) is True


def test_parse_schedule_invalid() -> None:
    with pytest.raises(ValueError):
        parse_schedule("invalid-schedule")
