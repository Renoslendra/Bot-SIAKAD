---
name: bot-siakad
description: >
  Automate KRS selection on SIAKAD Universitas Trunojoyo Madura for semester 5
  (23 SKS, no schedule conflicts). Use when the user asks about ambil KRS,
  siakad bot, course selection, dry-run KRS, status KRS, or Bot-SIAKAD.
version: 1.0.0
author: Bot-SIAKAD
---

# Bot SIAKAD Skill

## When to use

- User wants to run / dry-run / check status of Bot-SIAKAD
- User mentions KRS, SIAKAD Trunojoyo, ambil matakuliah semester 5

## Architecture rule

- Core bot is Python + Playwright in the project root
- This skill is a **wrapper only**
- Always use the `terminal` tool to run the bot
- Do **not** use Hermes browser tools for login/scrape/select/submit

## Prerequisites

1. Project path exists (Bot-SIAKAD root containing `main.py`)
2. `.env` filled (`SIAKAD_USERNAME`, `SIAKAD_PASSWORD`)
3. Dependencies installed (`pip install -r requirements.txt`, `playwright install chromium`)
4. `config/selectors.json` present (recon done; re-recon when masa KRS opens)
5. Prefer dry-run before any submit
6. Activate project venv if available: `.venv`

## Working directory

Always set cwd to the Bot-SIAKAD project root before running commands.

Prefer:

```bash
source .venv/Scripts/activate 2>/dev/null || true
python main.py --dry-run
```

Selectors live in `config/selectors.json` (local, gitignored). Template: `config/selectors.example.json`.

## Commands

| Mode | When | Terminal command |
|------|------|------------------|
| dry-run | Default / first run / testing | `python main.py --dry-run` |
| status | User asks last result | `python main.py --status` |
| report | Need detailed JSON | Read `logs/selection_report.json` |
| run | User explicitly wants submit | `python main.py --run --auto-confirm` |

### Run mode safety

Only execute **run/submit** if:

1. User explicitly asks to submit
2. `ALLOW_SUBMIT=true` in `.env`
3. Dry-run previously reviewed
4. Masa KRS is open
5. `config/selectors.json` has non-null `krs.select_control` and `krs.submit`

If any check fails, **do not** force submit. Explain blocker and suggest dry-run / re-recon.

## Current known production blockers (as of last recon)

- Outside KRS period SIAKAD shows **Bukan Periode Krs**
- Existing KRS can still be scraped
- Selection/submit UI selectors may be `null` until re-recon during open period

## Response format to user

After command finishes, summarize:

1. Status: SUCCESS / PARTIAL / FAILED / BLOCKED
2. Total SKS (existing + selected) vs 23
3. List existing + newly selected MK
4. Skipped MK + reasons
5. Period open/closed
6. Paths: `logs/selection_report.json`, screenshots if any

## Security

- Never ask user to paste password into chat
- Never print password
- Credentials stay in local `.env` only
- Prefer `USE_FALLBACK=false` unless user enables it
- After successful submit, remind user to set `ALLOW_SUBMIT=false` again

## Optional cron pattern

1. Pre-check: dry-run on schedule
2. Go-live: only with explicit user enablement + `ALLOW_SUBMIT=true`
3. Default cron must be dry-run, never auto-submit

## Examples

User: "dry-run ambil KRS semester 5"  
→ `python main.py --dry-run`

User: "status KRS bot"  
→ `python main.py --status`

User: "submit KRS sekarang"  
→ Check `ALLOW_SUBMIT` + period; if locked, explain; else `python main.py --run --auto-confirm`

## Troubleshooting

| Problem | Action |
|---------|--------|
| `main.py` not found | Wrong cwd — go to project root |
| Missing env | Tell user to copy `.env.example` → `.env` and fill credentials |
| selectors incomplete | Tell user re-run M0 recon when masa KRS opens |
| Login failed | Suggest headed mode / CAPTCHA / check credentials |
| Partial SKS | Show skipped reasons; ask if enable `USE_FALLBACK` |
| Submit blocked | Read reason (`ALLOW_SUBMIT`, period closed, missing selectors) |
