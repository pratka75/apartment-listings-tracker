"""
Orchestrator: fetch enabled sources + pasted links -> diff vs snapshot ->
render category digest -> optionally email -> roll snapshot forward.

Run:
  python main.py            normal run; writes digest.html
  python main.py --email    also email the digest (Gmail app password)
  python main.py --no-save  dry run; do not update the snapshot

Sources: `sources.rentcast` (config) + every URL in config `watch_urls`,
each routed to its platform parser by sources_links.dispatch().
"""

import sys
from datetime import date
from pathlib import Path

import engine
import digest
import sources_links
from config import get_config

HERE = Path(__file__).parent
SNAPSHOT = HERE / "snapshot.json"
DIGEST_OUT = HERE / "digest.html"


def gather(cfg: dict):
    listings, manual = [], []

    if cfg.get("sources", {}).get("rentcast"):
        try:
            import sources_rentcast
            rc = sources_rentcast.fetch()
            listings += rc
            print(f"  rentcast: {len(rc)} listings")
        except SystemExit as e:
            print(f"  rentcast skipped: {e}")
        except Exception as e:
            print(f"  rentcast FAILED: {e}")

    link_listings, manual = sources_links.dispatch(cfg.get("watch_urls", []))
    listings += link_listings

    # Keep only the requested bedroom count (when a listing states its beds).
    beds = cfg["search"]["bedrooms"]
    listings = [l for l in listings if l.get("beds") in (None, beds)]

    # De-dupe by id.
    return list({l["id"]: l for l in listings}.values()), manual


def main():
    cfg = get_config()
    no_save = "--no-save" in sys.argv

    print("Fetching sources...")
    current, manual = gather(cfg)
    print(f"Total listings gathered: {len(current)} (+{len(manual)} manual-check links)")

    snapshot = engine.load_snapshot(SNAPSHOT)
    if snapshot["last_run"] is None:
        print("No previous snapshot — first run: everything counts as NEW.")
    changes = engine.diff(snapshot, current)
    print(f"Changes: {len(changes['new'])} new, {len(changes['price_changes'])} price changes, "
          f"{len(changes['removed'])} removed, {len(changes['back_in_market'])} back.")

    html = digest.build_html(current, changes, cfg, manual_links=manual)
    DIGEST_OUT.write_text(html, encoding="utf-8")
    print(f"Digest written to {DIGEST_OUT.name}")

    if "--email" in sys.argv:
        import mailer
        n = len([l for l in changes["new"] if (l.get("price") or 1e9) <= cfg["search"]["max_rent"]])
        d = sum(1 for c in changes["price_changes"] if c["delta"] < 0)
        beds = cfg["search"]["bedrooms"]
        mailer.send(f"{beds}BR apartments — {n} new, {d} price drops ({date.today():%b %d})", html)

    if no_save:
        print("--no-save: snapshot NOT updated.")
    else:
        engine.save_snapshot(SNAPSHOT, engine.build_next_snapshot(snapshot, current, changes))
        print(f"Snapshot updated ({len(current)} active).")


if __name__ == "__main__":
    main()
