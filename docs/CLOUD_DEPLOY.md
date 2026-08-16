# Hands-free hosting on Claude cloud

Run the tracker as a **scheduled Claude cloud agent** ("routine") so the daily
digest arrives with your laptop off. The routine spins up an isolated cloud
session, clones this repo, runs the tracker, emails you, and saves state back.

## Why this needs a few special steps

A cloud run is stateless and isolated — it can't see your laptop. In this
private repo:

- **Filters** (`config.local.json`) are **committed to the repo** (filters +
  recipient only — no secrets). Change your budget/beds/area anytime by editing
  that one file (or regenerating it with `webapp/index.html`); no code or routine
  changes needed. The next run picks it up.
- **Secrets** (`.env`) are written by the agent from the routine prompt each run.
  **Never committed.**
- **State** (`snapshot.json`, `rentcast_usage.json`) is committed back by the
  agent after each run so change-detection persists between days.

Because filters live in the repo, keep it **private**.

## Prerequisites

- This repo pushed to a **private** GitHub repo (pure code — no config/secrets).
- A Gmail **app password**, your Gmail address, and (optionally) a RentCast key.

## The routine

Create a scheduled routine (via the `/schedule` skill or claude.ai/code/routines)
with:

- **Repo:** your private GitHub URL
- **Schedule:** daily at **6 PM ET** = `0 22 * * *` (UTC, during EDT).
  Cron is fixed UTC, so when clocks change to EST (winter) this fires at 5 PM ET
  — update to `0 23 * * *` then if you want it to stay 6 PM year-round.
- **Allowed tools:** `Bash`, `Read`, `Write`, `Edit`
- **Prompt:** (fill in your real secret values — these live in the routine
  config, which is stored in Anthropic's cloud, not in git)

```
You are running the apartment-listings-tracker in this cloned repo. Filters are
already in config.local.json (committed). Do EXACTLY this, and never print .env
or any secret value.

1. Write a .env file in the repo root with EXACTLY these lines (replace the
   <<FILL>> markers with real values before enabling this routine):
   GMAIL_SENDER=<your-gmail-address>
   DIGEST_RECIPIENT=<where-to-send-the-digest>
   GMAIL_APP_PASSWORD=<<FILL: your Gmail app password>>
   RENTCAST_API_KEY=<<FILL: your RentCast API key>>

2. Run: python main.py --email

3. Persist state so tomorrow's run can detect changes (only these two files):
   git add -f snapshot.json rentcast_usage.json
   git -c user.email=bot@local -c user.name=tracker commit -m "state update" || true
   git push || true

4. Report the counts printed by main.py (new / price drops / removed / back).
```

> To change filters later (beds, rent, area, links), edit `config.local.json` in
> the repo — no change to this prompt or the code.

## Security notes for cloud

- Keep the repo **private** — `config.local.json` contains your recipient email.
- The Gmail app password lives in the routine config. Use a **dedicated** app
  password you can revoke independently, and never reuse it elsewhere.
- The agent is instructed not to echo `.env`; secrets are not logged.
- `.env` is written fresh each run and never committed (it stays gitignored, and
  the state commit only force-adds `snapshot.json` / `rentcast_usage.json`).
- Rotate the app password if you ever suspect exposure
  (https://myaccount.google.com/apppasswords).

## First run

Trigger the routine once manually ("Run now"). Confirm the email arrives and that
a `state update` commit appears in the repo. After that, it runs on schedule and
each day's email shows only real changes.
