"""Tampilkan jadwal semua kelas dari cache (logs/scraped_courses.json)."""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
PROJECT_ROOT = Path(__file__).resolve().parent.parent

data = json.loads((PROJECT_ROOT / "logs" / "scraped_courses.json").read_text(encoding="utf-8"))

for course in data.get("courses", []):
    print(f"{course['code']} - {course['name']} ({course['sks']} SKS)")
    for cls in course.get("classes", []):
        sched = ", ".join(s.get("raw", "") for s in cls.get("schedules") or [])
        quota = cls.get("quota_remaining")
        quota_text = f"  [kuota {quota}]" if quota is not None else ""
        print(f"    {str(cls.get('class_name')):<8} {sched or '(KOSONG)'}{quota_text}")
    print()

print(f"Total MK  : {len(data.get('courses', []))}")
print(f"Enriched  : {data.get('schedule_enriched_count', 0)} kelas")
