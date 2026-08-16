"""
Snapshot + diff engine. Source-agnostic: operates on normalized listing dicts
(see sources_newport_rentals.py for the schema).

Snapshot file structure (snapshot.json):
{
  "last_run":  "2026-08-16T08:00:00",
  "active":    { id: listing, ... },              # listings seen on the previous run
  "graveyard": { id: {"listing": {...},
                      "removed_on": "2026-08-14"}, ... }  # previously-removed listings
}

Diff categories:
  new           -> appeared since last run, never seen before
  back_in_market-> appeared since last run, but was previously removed
  price_changes -> present both runs, price differs (old, new, delta)
  removed       -> was active last run, gone now
"""

import json
from datetime import date
from pathlib import Path


def load_snapshot(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"last_run": None, "active": {}, "graveyard": {}}


def diff(snapshot: dict, current: list[dict]) -> dict:
    """Compare current listings against the snapshot. Returns categorized changes."""
    prev_active = snapshot.get("active", {})
    graveyard = snapshot.get("graveyard", {})
    cur = {l["id"]: l for l in current}

    new, back = [], []
    for lid, listing in cur.items():
        if lid in prev_active:
            continue  # still active, handled by price-change check
        if lid in graveyard:
            back.append(listing)
        else:
            new.append(listing)

    price_changes = []
    for lid, listing in cur.items():
        if lid in prev_active:
            old = prev_active[lid].get("price")
            now = listing.get("price")
            if old is not None and now is not None and old != now:
                price_changes.append({
                    "listing": listing,
                    "old_price": old,
                    "new_price": now,
                    "delta": now - old,
                })

    removed = [prev_active[lid] for lid in prev_active if lid not in cur]

    return {"new": new, "back_in_market": back, "price_changes": price_changes, "removed": removed}


def build_next_snapshot(snapshot: dict, current: list[dict], changes: dict) -> dict:
    """Roll the snapshot forward: current becomes active; newly-removed join graveyard."""
    cur = {l["id"]: l for l in current}
    graveyard = dict(snapshot.get("graveyard", {}))
    today = date.today().isoformat()

    # Anything that came back is no longer "removed".
    for listing in changes["back_in_market"]:
        graveyard.pop(listing["id"], None)

    # Newly removed listings enter the graveyard.
    for listing in changes["removed"]:
        graveyard[listing["id"]] = {"listing": listing, "removed_on": today}

    from datetime import datetime
    return {"last_run": datetime.now().isoformat(timespec="seconds"),
            "active": cur, "graveyard": graveyard}


def save_snapshot(path: Path, snapshot: dict) -> None:
    path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
