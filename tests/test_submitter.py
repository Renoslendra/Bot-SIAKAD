from __future__ import annotations

from bot import config
from bot.submitter import find_checkbox_match, preflight_submit


def test_preflight_blocks_dry_run() -> None:
    ok, reason = preflight_submit(
        dry_run=True,
        selected=[{"code": "IF2228", "sks": 3}],
        period={"is_open": True},
        selectors={"krs": {"select_control": "input", "submit": "button"}},
    )
    assert ok is False
    assert "dry-run" in reason.lower()


def test_preflight_blocks_when_allow_submit_false(monkeypatch) -> None:
    monkeypatch.setattr(config, "ALLOW_SUBMIT", False)
    ok, reason = preflight_submit(
        dry_run=False,
        selected=[{"code": "IF2228", "sks": 3}],
        period={"is_open": True},
        selectors={"krs": {"select_control": "input", "submit": "button"}},
    )
    assert ok is False
    assert "ALLOW_SUBMIT" in reason


def test_preflight_blocks_empty_selected(monkeypatch) -> None:
    monkeypatch.setattr(config, "ALLOW_SUBMIT", True)
    ok, reason = preflight_submit(
        dry_run=False,
        selected=[],
        period={"is_open": True},
        selectors={"krs": {"select_control": "input", "submit": "button"}},
    )
    assert ok is False
    assert "tidak ada mk" in reason.lower()


def test_preflight_blocks_closed_period(monkeypatch) -> None:
    """Period check dihapus dari preflight karena SIAKAD menyediakan tombol
    Tambah Matakuliah meski belum 'masa KRS' resmi. Deteksi sudah
    berbasis keberadaan kontrol, bukan flag period."""
    monkeypatch.setattr(config, "ALLOW_SUBMIT", True)
    ok, reason = preflight_submit(
        dry_run=False,
        selected=[{"code": "IF2228", "sks": 3}],
        period={"is_open": False, "reason": "Bukan Periode Krs"},
        selectors={"krs": {"select_control": "input", "submit": "button"}},
    )
    # Preflight sekarang LOLOS karena kontrol sudah lengkap.
    assert ok is True


def test_preflight_blocks_missing_selectors(monkeypatch) -> None:
    monkeypatch.setattr(config, "ALLOW_SUBMIT", True)
    ok, reason = preflight_submit(
        dry_run=False,
        selected=[{"code": "IF2228", "sks": 3}],
        period={"is_open": True},
        selectors={"krs": {"select_control": None, "submit": None}},
    )
    assert ok is False
    assert "select_control" in reason or "submit" in reason


def test_preflight_passes_when_ready(monkeypatch) -> None:
    monkeypatch.setattr(config, "ALLOW_SUBMIT", True)
    ok, reason = preflight_submit(
        dry_run=False,
        selected=[{"code": "IF2228", "sks": 3}],
        period={"is_open": True},
        selectors={"krs": {"select_control": "input.chk", "submit": "input[type=submit]"}},
    )
    assert ok is True
    assert "lulus" in reason.lower()


def test_checkbox_match_requires_exact_course_name_and_class() -> None:
    rows = [
        {
            "value": "perangkat",
            "namaMK": "Proyek Perangkat Lunak",
            "kelas": "IF 5C",
        },
        {
            "value": "sain-data",
            "namaMK": "Proyek Sain Data",
            "kelas": "IF 5C",
        },
    ]

    match = find_checkbox_match(
        {"name": "Proyek Sain Data", "class_name": "IF 5C"}, rows
    )

    assert match is not None
    assert match["value"] == "sain-data"


def test_checkbox_match_normalizes_class_spacing() -> None:
    match = find_checkbox_match(
        {"name": "Basis Data III", "class_name": "IF 7A"},
        [{"value": "basis-data", "namaMK": "Basis Data III", "kelas": "IF  7A"}],
    )

    assert match is not None
    assert match["value"] == "basis-data"
