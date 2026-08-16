"""
RentCast source — the generic, works-anywhere fetcher (driven by config location).

Cost safety: RentCast has NO hard spending cap, so we enforce our own. A monthly
request counter (rentcast_usage.json, gitignored) blocks the call if it would
exceed REQUEST_BUDGET for the current month. One daily run ~= 30/month, under the
50 free-tier limit.

Links in the output point to a public Google search of the address, never to
api.rentcast.io — so opening a listing from the email can never spend quota.
"""

import json
import urllib.parse
from datetime import date
from pathlib import Path

import safefetch
from config import get_config
from secrets_env import get_secret

HERE = Path(__file__).parent
USAGE_FILE = HERE / "rentcast_usage.json"
REQUEST_BUDGET = 45          # stay safely under the 50/month free tier
API = "https://api.rentcast.io/v1/listings/rental/long-term"


def _check_and_bump_budget() -> None:
    month = date.today().strftime("%Y-%m")
    usage = {"month": month, "count": 0}
    if USAGE_FILE.exists():
        try:
            saved = json.loads(USAGE_FILE.read_text(encoding="utf-8"))
            if saved.get("month") == month:
                usage = saved
        except json.JSONDecodeError:
            pass
    if usage["count"] >= REQUEST_BUDGET:
        raise SystemExit(
            f"RentCast monthly request budget ({REQUEST_BUDGET}) reached for {month}. "
            f"Skipping to avoid overage charges."
        )
    usage["count"] += 1
    USAGE_FILE.write_text(json.dumps(usage), encoding="utf-8")


def _params(cfg: dict) -> dict:
    s = cfg["search"]
    loc = s["location"]
    p = {"bedrooms": s["bedrooms"], "status": "Active", "limit": 500}
    if "latitude" in loc:
        p.update(latitude=loc["latitude"], longitude=loc["longitude"],
                 radius=loc.get("radius_miles", 1))
    elif loc.get("zipCode"):
        p["zipCode"] = loc["zipCode"]
    else:
        p.update(city=loc["city"], state=loc["state"])
    return p


def _normalize(rec: dict) -> dict:
    addr = rec.get("formattedAddress") or ""
    q = urllib.parse.quote_plus(f"{addr} apartment for rent")
    return {
        "source": "rentcast",
        "building": None,
        "unit": None,
        "address": addr,
        "beds": rec.get("bedrooms"),
        "baths": rec.get("bathrooms"),
        "sqft": rec.get("squareFootage"),
        "price": rec.get("price"),
        "available": rec.get("status") or (rec.get("listedDate") or "")[:10],
        "url": f"https://www.google.com/search?q={q}",   # public search, never the API
        "floorplan_url": None,
        "id": f"rentcast|{addr.lower()}",
    }


def fetch(timeout: int = 30) -> list[dict]:
    cfg = get_config()
    api_key = get_secret("RENTCAST_API_KEY")
    _check_and_bump_budget()

    url = API + "?" + urllib.parse.urlencode(_params(cfg))
    raw = safefetch.get_text(url, headers={"X-Api-Key": api_key, "Accept": "application/json"},
                             timeout=timeout)
    data = json.loads(raw)
    records = data if isinstance(data, list) else data.get("data", [])
    return [_normalize(r) for r in records if r.get("formattedAddress")]
