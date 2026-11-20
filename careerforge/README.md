# careerforge

Career strategy + portfolio-builder **CLI and local web dashboard** in pure-stdlib Python.
You feed it your **master profile** (skills, projects, non-traditional background, work
preferences) and **target roles** (job descriptions or company URLs), and Mistral generates:

1. **Brutal gap analysis** — exactly which skills / portfolio proof are missing per target role.
2. **A custom 14-day micro-project spec** that proves you can solve that company's specific problems.
3. **Tailored CV bullet points + outreach notes** that foreground your transferable analytical
   strengths without sounding generic or AI-written.

Everything (profile, targets, generated results, applications, follow-up reminders) is stored in
one **local SQLite** tracker with application status and reminders.

## Requirements

- Python ≥ 3.10, **no third-party dependencies**.
- A Mistral API key for the LLM features: `export MISTRAL_API_KEY=...` (get one at
  https://console.mistral.ai). Without a key — or with `--offline` — every command still works
  using a built-in deterministic generator, and results are clearly marked `mode=offline`.

## Install / run

```bash
pip install -e .            # optional; gives the `careerforge` command
# or run without installing:
python -m careerforge --help
```

Configuration (all optional):

| Env var | Purpose | Default |
|---|---|---|
| `MISTRAL_API_KEY` | Mistral API key (never stored, only read) | — |
| `CAREERFORGE_MODEL` | chat model | `mistral-large-latest` |
| `CAREERFORGE_BASE_URL` | API base URL override | `https://api.mistral.ai/v1` |
| `CAREERFORGE_DATA_DIR` | where `careerforge.db` lives | `~/.careerforge` |
| `CAREERFORGE_OFFLINE` | `1` = never call the API | — |

Global flags: `--data-dir DIR`, `--offline`, `--model NAME`.

## Quickstart

```bash
# 1. Build your master profile from your CV (plain text/markdown)
careerforge profile init --from-cv examples/cv-matus-altaner.md --name "Matúš Altaner"
careerforge profile set work_preferences.roles '["Junior Data Analyst", "IT Support Specialist"]'
careerforge profile set work_preferences.remote hybrid
careerforge profile set skills '- ' '{"name":"SQL","level":"none"}'
careerforge profile show            # inspect; profile export p.json / import p.json also available

# 2. Add targets: JD text/file/URL and/or a company URL (fetched as company context)
careerforge target add --title "Junior Data Analyst" --company "ACME Logistics" \
    --jd-file examples/jd-junior-data-analyst.txt --location Bratislava
careerforge target add --title "IT Support Specialist" --company "TatraTech" \
    --jd-url "https://example.com/jobs/it-support" --url "https://example.com/about"
careerforge target list

# 3. Generate the three artifacts for a target (or all at once with `run`)
careerforge analyze 1     # brutal gap analysis
careerforge project 1     # 14-day micro-project spec
careerforge tailor 1      # CV bullets + outreach email/LinkedIn DM
careerforge run 1         # all three

# 4. Track applications and follow-ups
careerforge track add --target 1 --status applied --contact "recruiter@acme.eu" --followup 2026-12-05
careerforge track set 1 --status interview
careerforge track list
careerforge remind add --message "Follow up with ACME recruiter" --due 2026-12-05 --app 1
careerforge remind list --due        # due today or overdue
careerforge remind done 1
careerforge status                   # full overview

# 5. Export per-target markdown files (gap analysis, project spec, tailored CV, JD)
careerforge export 1 --out out/

# 6. Web dashboard (loopback only)
careerforge serve --port 8000     # http://127.0.0.1:8000
```

## Dashboard

`careerforge serve` starts a local dashboard (bound to `127.0.0.1`; non-loopback binds are
refused) with:

- `/` — profile summary, targets with match scores, pipeline counts, due reminders
- `/targets` and `/targets/<id>` — JD, rendered gap analysis, day-by-day 14-day plan, tailored CV + outreach
- `/tracker` — applications with inline status/follow-up editing and reminders (add / mark done)
- `/api/stats`, `/api/profile`, `/api/targets`, `/api/applications`, `/api/reminders` — JSON

## Data model (SQLite, `<data-dir>/careerforge.db`)

- `profile` — the master profile as one JSON document
- `targets` — title, company, url, location, `jd_text`, `company_context`, notes
- `results` — generated artifacts per target, `kind` ∈ `gap | project | tailor`, with `mode`
  (`llm`/`offline`) and `model`, payload JSON
- `applications` — status (`saved, applied, screening, interview, offer, rejected, withdrawn,
  on_hold`), contact, applied date, next follow-up, notes, optional link to a target
- `reminders` — message, due date, done flag, optional link to an application

## Tests

```bash
python -m unittest discover -s tests -v
```

## Privacy

The Mistral API key is read from the environment at call time and is never written to disk or
logs. All data stays in the local SQLite file; the dashboard refuses non-loopback binds.
