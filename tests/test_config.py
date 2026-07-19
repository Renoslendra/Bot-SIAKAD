from __future__ import annotations

from pathlib import Path

from bot import config
from bot.utils import load_json, save_json


def test_priority_courses_total_sks() -> None:
    total = sum(course["sks"] for course in config.PRIORITY_COURSES)
    assert total == 23
    assert len(config.PRIORITY_COURSES) == 8


def test_fallback_default_off() -> None:
    assert config.USE_FALLBACK is False
    assert config.ALLOW_SUBMIT is False


def test_target_codes_respects_fallback_flag() -> None:
    priority_only = config.target_codes(include_fallback=False)
    with_fallback = config.target_codes(include_fallback=True)
    assert priority_only == config.priority_codes()
    assert len(with_fallback) == len(config.priority_codes()) + len(config.fallback_codes())


def test_submit_allowed_safety_lock() -> None:
    allowed, reason = config.submit_allowed(dry_run=True)
    assert allowed is False
    assert "dry-run" in reason.lower()

    allowed, reason = config.submit_allowed(dry_run=False)
    if config.ALLOW_SUBMIT:
        assert allowed is True
    else:
        assert allowed is False
        assert "ALLOW_SUBMIT" in reason


def test_json_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "sample.json"
    payload = {"ok": True, "items": [1, 2, 3]}
    save_json(path, payload)
    loaded = load_json(path)
    assert loaded == payload
