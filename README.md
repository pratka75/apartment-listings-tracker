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

## Hands-free hosting on Claude cloud

This tracker is set up to run as a **scheduled Claude cloud agent** (a "routine")
so it runs daily without your machine being on. See
[`docs/CLOUD_DEPLOY.md`](docs/CLOUD_DEPLOY.md) for the full walkthrough. In short:

1. Push this repo to GitHub (private).
2. Create a routine that clones the repo, injects secrets from the routine
   config (never committed), runs `python main.py --email`, and commits the
   updated `snapshot.json` back so change-detection persists between days.
3. Schedule it daily.

> Security note: cloud hosting means your Gmail app password and RentCast key
> must live in the cloud routine config. Use a dedicated app password you can
> revoke, and keep the repo private.

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
