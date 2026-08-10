import json, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
d = json.load(open('logs/schedule_cache.json', encoding='utf-8'))
targets = [
    ('IF2229', 'IF 5A', 'Proyek Perangkat Lunak'),
    ('IF2231', 'IF 5C', 'Proyek Sains Data'),
    ('IF2259', 'IF 7B', 'Pengolahan Citra'),
    ('IF2258', 'IF 7A', 'Basis Data III'),
    ('IF2230', 'IF 5E', 'Pembelajaran Mesin'),
    ('IF2232', 'IF 5D', 'Metodologi Penelitian'),
    ('IF2260', 'IF 7B', 'Pemodelan Proses Bisnis'),
    ('IF2228', 'IF 5C', 'Sistem Terdistribusi'),
]
total = 0
for code, kelas, name in targets:
    found = False
    for c in d['courses']:
        if c['code'] != code:
            continue
        for cl in c['classes']:
            if cl['class_name'] == kelas:
                sched = ', '.join(s.get('raw','') for s in cl.get('schedules') or [])
                sks = c['sks']
                total += sks
                print(f"OK   {code} {kelas:8s} {sched:30s} {sks} SKS  {name}")
                found = True
                break
    if not found:
        print(f"MISS {code} {kelas:8s} -- TIDAK ADA DI CACHE")
print(f"\nTotal: {total} SKS")
