# Bot-SIAKAD

Auto course selection bot for **SIAKAD Universitas Trunojoyo Madura** — Semester 5, target **23 SKS**, no schedule conflicts.

## Project structure

```text
Bot-SIAKAD/
├── main.py                 # CLI entrypoint
├── bot/                    # Core package
│   ├── cli.py
│   ├── config.py
│   ├── login.py
│   ├── scraper.py
│   ├── selector.py
│   ├── submitter.py
│   ├── reporter.py
│   └── utils.py
├── config/
│   ├── selectors.example.json
│   └── selectors.json      # local only (gitignored)
├── docs/                   # PRD, Task, Guideline, PREFLIGHT, flowchart
├── scripts/                # recon + semester5 checker
├── tests/
├── hermes-skill/
├── logs/                   # runtime output (gitignored)
├── .env.example
├── requirements.txt
└── README.md
```

## Status

| Layer | Ready? |
|-------|--------|
| Core package + tests | **Yes** (`pytest` 38 passed) |
| Login + scrape existing | **Yes** |
| Selection engine | **Yes** |
| Submit module | **Yes** (safety-locked) |
| Semester 5 MK list on SIAKAD | **Not complete yet** (check script) |
| Production submit | Locked until KRS period opens |

## Quick start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium

copy .env.example .env
# isi SIAKAD_USERNAME / SIAKAD_PASSWORD
# keep ALLOW_SUBMIT=false

# optional: copy selectors template if missing
copy config\selectors.example.json config\selectors.json

python main.py --dry-run
python main.py --status
pytest tests/ -q
python scripts/check_semester5.py
```

## CLI

| Flag | Description |
|------|-------------|
| `--dry-run` | Login + scrape + select, no submit |
| `--status` | Print last report |
| `--run` | Full pipeline including submit path |
| `--auto-confirm` | Skip submit prompt |
| `--headless` / `--headed` | Browser mode |

## Safety

1. Default `ALLOW_SUBMIT=false`
2. Default `USE_FALLBACK=false`
3. Submit blocked if period closed / no selected courses / missing selectors
4. After real submit, set `ALLOW_SUBMIT=false` again

## When semester 5 list updates

```powershell
python scripts/check_semester5.py
```

Need output: `COMPLETE` (8/8 priority, 23 SKS).

## Production submit (only when KRS open)

1. `python main.py --dry-run`
2. Re-recon if needed: `python scripts/recon.py` then update `config/selectors.json`
3. Review `logs/selection_report.json`
4. Set `ALLOW_SUBMIT=true`
5. `python main.py --run --auto-confirm`
6. Verify on SIAKAD + `--status`
7. Set `ALLOW_SUBMIT=false`

## Hermes

Skill: `hermes-skill/` (installed as `bot-siakad`).

```bash
python main.py --dry-run
python main.py --status
```

## Docs

- `docs/PRD.md`
- `docs/Task.md`
- `docs/Guideline.md`
- `docs/PREFLIGHT.md`
- `docs/flowchart.html`
