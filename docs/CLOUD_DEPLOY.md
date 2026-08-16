# Hands-free hosting on Claude cloud

Run the tracker as a **scheduled Claude cloud agent** ("routine") so the daily
digest arrives with your laptop off. The routine spins up an isolated cloud
session, clones this repo, runs the tracker, emails you, and saves state back.

## Why this needs a few special steps

A cloud run is stateless and isolated — it can't see your laptop. So the
committed repo stays **pure code** — no filters, no secrets — and the routine
injects everything private at runtime:

- **Filters** (`config.local.json`) are written by the agent from the routine
  prompt each run. Nothing private is committed.
- **Secrets** (`.env`) are written by the agent from the routine prompt each run.
  Never committed.
- **State** (`snapshot.json`, `rentcast_usage.json`) must persist between days,
  so the agent commits *only those* back to the repo after each run.

This keeps the repo identical to the shareable code and leaks nothing if the repo
is ever exposed. Keeping it **private** is still recommended.

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
You are running the apartment-listings-tracker in this repo. Do exactly this:

1. Write config.local.json in the repo root with EXACTLY this content:
   {
     "search": { "bedrooms": 2, "max_rent": 4200,
       "location": { "latitude": 40.7266, "longitude": -74.0339, "radius_miles": 0.6 } },
     "sources": { "rentcast": true },
     "watch_urls": [
       "https://www.newportrentals.com/2-bedroom-apartments-jersey-city/",
       "https://www.avaloncommunities.com/new-jersey/jersey-city-apartments/avalon-cove/",
       "https://www.rentcafe.com/apartments/nj/jersey-city/the-blvd-collection/default.aspx"
     ],
     "email": { "recipient": "<your-recipient-email>" }
   }

2. Write a .env file in the repo root with EXACTLY these lines:
   GMAIL_SENDER=<your-gmail-address>
   GMAIL_APP_PASSWORD=<your-app-password>
   RENTCAST_API_KEY=<your-rentcast-key>

3. Run: python main.py --email

4. Persist state so tomorrow's run can detect changes (only these two files):
   git add -f snapshot.json rentcast_usage.json
   git -c user.email=bot@local -c user.name=tracker commit -m "state update" || true
   git push || true

5. Report the counts printed by main.py (new / price drops / removed / back).
Never print the contents of .env, config.local.json, or any secret.
```

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
