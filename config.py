"""
Load and validate the self-hosted user configuration.

All user-specific values live in `config.local.json` (gitignored) so nobody's
filters or locality are ever committed. `config.example.json` is the committed
template. Generate your own with the config-builder webapp or by copying the
example.
"""

import json
import re
from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).parent
CONFIG_PATH = HERE / "config.local.json"

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ConfigError(SystemExit):
    """Raised (as a clean exit) when the config is missing or invalid."""


def _require(cond, msg):
    if not cond:
        raise ConfigError(f"config.local.json: {msg}")


def _clean_email(value, field):
    """Accept one email, or several comma-separated. Each is validated; CR/LF are
    stripped so this can't be used for SMTP header injection."""
    _require(isinstance(value, str), f"{field} must be a string")
    flat = value.replace("\r", " ").replace("\n", " ")
    parts = [p.strip() for p in flat.split(",") if p.strip()]
    _require(parts and all(_EMAIL_RE.match(p) for p in parts),
             f"{field} must be one or more valid email addresses: {value!r}")
    return ", ".join(parts)


def _validate(cfg: dict) -> dict:
    _require(isinstance(cfg, dict), "top level must be a JSON object")

    search = cfg.get("search", {})
    _require(isinstance(search, dict), "'search' must be an object")

    beds = search.get("bedrooms")
    _require(isinstance(beds, int) and 0 <= beds <= 10, "search.bedrooms must be an int 0-10")

    max_rent = search.get("max_rent")
    _require(isinstance(max_rent, int) and 0 < max_rent <= 1_000_000,
             "search.max_rent must be a positive int")

    loc = search.get("location", {})
    _require(isinstance(loc, dict), "search.location must be an object")
    # Accept either lat/long+radius OR zipCode OR city+state.
    if "latitude" in loc or "longitude" in loc:
        lat, lon = loc.get("latitude"), loc.get("longitude")
        _require(isinstance(lat, (int, float)) and -90 <= lat <= 90, "location.latitude out of range")
        _require(isinstance(lon, (int, float)) and -180 <= lon <= 180, "location.longitude out of range")
        r = loc.get("radius_miles", 1)
        _require(isinstance(r, (int, float)) and 0 < r <= 100, "location.radius_miles must be 0-100")
        loc["radius_miles"] = float(r)
    elif loc.get("zipCode"):
        _require(re.fullmatch(r"\d{5}", str(loc["zipCode"])), "location.zipCode must be 5 digits")
    else:
        _require(loc.get("city") and loc.get("state"),
                 "location needs latitude/longitude, or zipCode, or city+state")

    towers = cfg.get("watch_towers", [])
    _require(isinstance(towers, list), "watch_towers must be a list")
    for t in towers:
        _require(isinstance(t, dict) and t.get("name") and isinstance(t.get("match"), list),
                 "each watch_towers entry needs 'name' and a 'match' list")

    # User-pasted listing links to include in the scan. http/https only (no
    # javascript:/data:/file: schemes) so a malicious config can't be abused.
    urls = cfg.get("watch_urls", [])
    _require(isinstance(urls, list), "watch_urls must be a list")
    for u in urls:
        _require(isinstance(u, str) and re.match(r"^https?://", u, re.I),
                 f"watch_urls entries must be http(s) URLs: {u!r}")

    sources = cfg.get("sources", {})
    _require(isinstance(sources, dict), "sources must be an object of {name: bool}")

    email = cfg.get("email", {})
    _require(isinstance(email, dict), "email must be an object")
    # recipient is OPTIONAL in config: it can instead come from the DIGEST_RECIPIENT
    # env var (so it need not live in a public repo). Validate only if present.
    if email.get("recipient"):
        email["recipient"] = _clean_email(email["recipient"], "email.recipient")

    return cfg


@lru_cache(maxsize=1)
def get_config() -> dict:
    if not CONFIG_PATH.exists():
        raise ConfigError(
            "Missing config.local.json.\n"
            "  -> Copy config.example.json to config.local.json and edit your filters,\n"
            "     or open webapp/index.html to generate one. See README.md."
        )
    try:
        cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ConfigError(f"config.local.json is not valid JSON: {e}")
    return _validate(cfg)


def tower_name(listing: dict, cfg: dict | None = None):
    """Return the watch-tower name if this listing matches one, else None."""
    cfg = cfg or get_config()
    blob = " ".join(str(listing.get(k, "")) for k in ("address", "building", "formattedAddress")).lower()
    for t in cfg.get("watch_towers", []):
        if any(str(h).lower() in blob for h in t.get("match", [])):
            return t.get("name")
    return None
