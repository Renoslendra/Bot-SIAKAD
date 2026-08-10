"""Simulasi selection engine memakai cache jadwal, tanpa membuka browser.

Memaksa period_open=True supaya bisa diuji sebelum masa KRS buka.

Jalankan: python scripts/simulate_selection.py
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from bot.config import TARGET_SKS
from bot.selector import select_courses
from bot.utils import format_selection_summary

data = json.loads((PROJECT_ROOT / "logs" / "schedule_cache.json").read_text(encoding="utf-8"))
offered = data.get("courses", [])

for use_fallback in (False, True):
    print("=" * 74)
    print(f"SIMULASI  use_fallback={use_fallback}  target={TARGET_SKS} SKS")
    print("=" * 74)
    result = select_courses(
        offered,
        existing_courses=[],
        period_open=True,
        use_fallback=use_fallback,
        target_sks=TARGET_SKS,
    )
    print(format_selection_summary(result))

    print("\nJADWAL MINGGUAN:")
    slots = []
    for course in result.get("selected", []):
        for sched in course.get("schedules", []):
            slots.append((sched["day"], sched["start"], sched["end"], course["code"],
                          course.get("class_name")))
    order = {"Senin": 1, "Selasa": 2, "Rabu": 3, "Kamis": 4, "Jumat": 5, "Sabtu": 6}
    for day, start, end, code, kelas in sorted(slots, key=lambda x: (order.get(x[0], 9), x[1])):
        print(f"  {day:<8} {start//60:02d}:{start%60:02d}-{end//60:02d}:{end%60:02d}  "
              f"{code} {kelas}")

    # Cek bentrok
    conflicts = []
    for i in range(len(slots)):
        for j in range(i + 1, len(slots)):
            a, b = slots[i], slots[j]
            if a[0] == b[0] and a[1] < b[2] and a[2] > b[1]:
                conflicts.append((a, b))
    print(f"\nBENTROK: {len(conflicts)}")
    for a, b in conflicts:
        print(f"  !! {a[3]} {a[4]} vs {b[3]} {b[4]} ({a[0]})")
    print()
