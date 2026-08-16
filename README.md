# Apartment Listings Tracker

A daily email digest of **2-bedroom apartments near Newport PATH (Jersey City)**,
grouped by provider, with new / price-drop / removed / back-on-market detection.
This is a personal, multi-source build (a generic RentCast-only version lives in
the sibling `apartment-listings-digest` project).

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
python test_security.py       # optional
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

## Files

| File | Purpose |
|---|---|
| `main.py` | Orchestrator |
| `config.py` / `config.local.json` | Config loader / your filters (committed here — no secrets; edit to change filters) |
| `secrets_env.py` / `.env` | Secret loader / your secrets (gitignored) |
| `safefetch.py` | SSRF-resistant HTTP helper |
| `sources_rentcast.py` / `sources_newport_rentals.py` / `sources_avalon.py` | Fetchers |
| `sources_links.py` | Routes `watch_urls` to parsers or the manual section |
| `engine.py` / `digest.py` / `mailer.py` | Diff / category email / Gmail sender |
| `scripts/check_secrets.py` | Pre-commit secret scanner |
| `test_security.py` | Security regression suite |
