"""
Dispatcher for user-pasted `watch_urls`. Each link is routed to a platform
adapter by its domain. Links on platforms we can't fetch with a lightweight
request (e.g. Cloudflare-protected RentCafe) are returned as "manual" links so
the digest can still surface them for a human to click.

Returns (listings, manual_links) where manual_links = [{"url":..., "reason":...}].
"""

from urllib.parse import urlsplit

import sources_avalon
import sources_newport_rentals

# domain substring -> callable(url) -> list[listing]
ADAPTERS = [
    ("newportrentals.com", sources_newport_rentals.fetch),
    ("avaloncommunities.com", sources_avalon.fetch),
]

# Platforms known to block lightweight fetches; surfaced as manual links instead.
BLOCKED = {
    "rentcafe.com": "RentCafe is bot-protected (Cloudflare) — open to check availability.",
}


def dispatch(urls: list[str]) -> tuple[list[dict], list[dict]]:
    listings, manual = [], []
    for url in urls or []:
        host = (urlsplit(url).hostname or "").lower()

        blocked = next((msg for dom, msg in BLOCKED.items() if dom in host), None)
        if blocked:
            manual.append({"url": url, "reason": blocked})
            continue

        adapter = next((fn for dom, fn in ADAPTERS if dom in host), None)
        if adapter is None:
            manual.append({"url": url, "reason": "No parser for this site yet — open to check."})
            continue

        try:
            got = adapter(url)
            listings += got
            print(f"  link {host}: {len(got)} listings")
        except Exception as e:
            manual.append({"url": url, "reason": f"Fetch failed ({e}) — open to check."})
    return listings, manual
