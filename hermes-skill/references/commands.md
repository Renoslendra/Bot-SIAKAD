# Bot-SIAKAD — Command Reference (Hermes)

## Standalone CLI

```bash
# recommended: activate venv first
source .venv/Scripts/activate   # Windows git-bash / MSYS
# or: .\.venv\Scripts\Activate.ps1

python main.py --dry-run
python main.py --status
python main.py --run --auto-confirm
python main.py --headed --dry-run
python main.py --help
```

## Hermes natural language → action

| User says | Action |
|-----------|--------|
| dry-run / coba dulu / simulasi KRS | `python main.py --dry-run` |
| status / hasil terakhir / report | `python main.py --status` or read `logs/selection_report.json` |
| ambil / submit / daftarkan KRS | `python main.py --run --auto-confirm` only if ALLOW_SUBMIT=true + period open |

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | SUCCESS |
| 1 | FAILED / PARTIAL / BLOCKED / error |

## Important env flags

| Flag | Default | Meaning |
|------|---------|---------|
| ALLOW_SUBMIT | false | Production submit lock |
| AUTO_CONFIRM | false | Skip interactive confirm |
| USE_FALLBACK | false | Use cadangan MK if needed |
| HEADLESS | true | Browser GUI off |

## Safety gates before submit

1. `python main.py --dry-run` reviewed
2. Masa KRS open (not "Bukan Periode Krs")
3. `config/selectors.json` has `krs.select_control` + `krs.submit`
4. `ALLOW_SUBMIT=true`
5. User confirms or `--auto-confirm`

## Recommended flow

1. dry-run
2. review report
3. wait until KRS period opens + re-recon if needed
4. set ALLOW_SUBMIT=true
5. `python main.py --run --auto-confirm`
6. verify with `--status` + SIAKAD UI
7. set ALLOW_SUBMIT=false again

## Artifact paths

- `logs/selection_report.json`
- `logs/existing_krs.json`
- `logs/scraped_courses.json`
- `logs/bot.log`
- `logs/screenshots/`
- `logs/session.json`
