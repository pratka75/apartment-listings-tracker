# Apartment Listings Tracker

> **🔒 Personal project — not a general template.** This copy is tailored
> specifically to **Newport, Jersey City NJ** and is maintained for my own use
> (it includes Newport-specific building scrapers for Newport Rentals and Avalon
> Cove). **If you want alerts for your own city, use the general-purpose,
> shareable version instead:**
> **[apartment-listings-digest »](https://github.com/pratka75/apartment-listings-digest)**

A daily email digest of **apartments near Newport PATH (Jersey City)**, grouped by
provider, with new / price-drop / removed / back-on-market detection.

Designed to run **hands-free in the cloud** so alerts arrive with the laptop off.

---

## Sources (grouped as categories in the email)

| Category | Source | Method |
|---|---|---|
| **Newport Rentals** (LeFrak) | newportrentals.com | HTML parse (`sources_newport_rentals.py`) |
| **Avalon Cove** | avaloncommunities.com | Embedded JSON (`sources_avalon.py`) |
| **Other listings (RentCast)** | RentCast API | `sources_rentcast.py` — sweeps 07310 + corridor |
| **🔗 Check manually** | RentCafe / BLVD 425·475 | Cloudflare-blocked → surfaced as a link |

Pasted links in `config.local.json` → `watch_urls` are routed by
`sources_links.py`: known platforms (Newport, Avalon) are parsed; anything else
(or bot-protected sites like RentCafe) is shown in the **Check manually** section.

> **Note:** RentCast and RentCafe are unrelated companies. The RentCast API key
> does not work with RentCafe, which is Cloudflare-protected and cannot be
> scraped by the lightweight fetcher.

---

## How it works

```
Daily run → fetch sources + dispatch watch_urls → compare to yesterday's snapshot
          → new / price-change / removed / back → category digest → email → save snapshot
```

Current scan: **2BR, ≤ $4,200**, centered on **Newport PATH**
(lat 40.7266, lon −74.0339, **0.6 mi ≈ 10-min walk**) covering 07310 and the
Washington Blvd corridor.

---

## Security posture

- **No secrets or private filters in git** — `.env` and `config.local.json`
  (and `BUILDINGS.md`) are gitignored; only code + `*.example` templates commit.
- **Injection-safe email** — all scraped data HTML-escaped; links restricted to `http(s)`.
- **SSRF-resistant fetching** (`safefetch.py`) — refuses private/loopback/
  link-local/cloud-metadata hosts, validates redirects, caps response size.
- **SMTP header-injection-safe**, **strict config validation**, **stdlib only**
  (no `eval`/`exec`/`pickle`/shell), **pre-commit secret scanner**.
- **`python test_security.py`** — 26 automated checks covering all of the above.

---

## Run locally

```bash
cp .env.example .env          # add GMAIL_SENDER, GMAIL_APP_PASSWORD, RENTCAST_API_KEY
python tests/test_security.py # optional
python main.py --email        # fetch, build digest, email it
```

---

## Hands-free hosting on GitHub Actions

The included workflow [`.github/workflows/daily-digest.yml`](.github/workflows/daily-digest.yml)
runs the tracker daily (6 PM ET) with no machine of your own — GitHub's runners
have full network access, send the email, and commit state back for you.

**Setup (one time):**
1. In the repo: **Settings → Secrets and variables → Actions → New repository secret** —
   add four secrets: `GMAIL_SENDER`, `GMAIL_APP_PASSWORD`, `RENTCAST_API_KEY`, `DIGEST_RECIPIENT`.
2. **Actions** tab → enable workflows if prompted.
3. Test it: **Actions → Daily Apartment Digest → Run workflow**. Confirm the email
   arrives and a `state update` commit appears.
4. It then runs automatically on the daily schedule.

Filters come from the committed `config.local.json` — edit that file to change
budget/beds/area. Secrets live only in encrypted Actions secrets, never in git.

> Note: the Claude cloud "routine" runner is **not** suitable — its network
> sandbox blocks the listing sites and SMTP. GitHub Actions is the supported path.
> (`docs/CLOUD_DEPLOY.md` retained for historical reference.)

---

## Project layout

```
main.py                       # entry point: python main.py [--email] [--no-save]
apartment_alerts/             # the Python package
├── cli.py                    # orchestrator
├── config.py                 # loads config.local.json (repo root)
├── secrets_env.py            # loads .env (repo root)
├── safefetch.py              # SSRF-resistant HTTP helper
├── engine.py                 # snapshot + diff
├── digest.py                 # category HTML email builder (escaped)
├── mailer.py                 # Gmail SMTP sender
└── sources/                  # rentcast.py, newport_rentals.py, avalon.py, links.py
scripts/check_secrets.py      # pre-commit secret scanner
tests/test_security.py        # security regression suite (26 checks)
webapp/index.html             # static config builder
config.local.json  .env       # your filters (committed) / secrets (gitignored)
```

Runtime data (`config.local.json`, `.env`, `snapshot.json`, `rentcast_usage.json`)
lives at the repo root; the package resolves it via `apartment_alerts/paths.py`.
