"""
AvalonBay source (avaloncommunities.com). Their community pages embed a JSON
`"units":[...]` array with per-unit pricing/availability — served over plain
HTTP, so a lightweight daily fetch works.

`fetch(url)` takes an AvalonBay community URL (e.g. the Avalon Cove page) so the
same adapter works for any AvalonBay community, not just this one.
"""

import json

import safefetch


def _extract_units(html: str) -> list[dict]:
    key = '"units":['
    i = html.find(key)
    if i < 0:
        return []
    start = i + len(key) - 1          # at the '['
    depth = 0
    for j in range(start, len(html)):
        c = html[j]
        if c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(html[start:j + 1])
                except json.JSONDecodeError:
                    return []
    return []


def _price(unit: dict):
    for key in ("startingAtPricesUnfurnished", "startingAtPricesFurnished"):
        block = unit.get(key) or {}
        p = (block.get("prices") or {}).get("price")
        if isinstance(p, (int, float)):
            return int(p)
    return None


def _normalize(u: dict) -> dict:
    addr = (u.get("address") or {})
    line = addr.get("addressLine1") or ""
    full = ", ".join(x for x in [line, addr.get("city"), addr.get("state")] if x)
    if addr.get("zip"):
        full = f"{full} {addr['zip']}"
    avail = (u.get("availableDateUnfurnished") or u.get("availableDateFurnished") or "")[:10]
    return {
        "source": "avalon",
        "building": u.get("communityName") or "Avalon",
        "unit": u.get("unitName"),
        "address": full,
        "beds": u.get("bedroomNumber"),
        "baths": u.get("bathroomNumber"),
        "sqft": u.get("squareFeet"),
        "price": _price(u),
        "available": avail or "Available",
        "url": u.get("url") or "",
        "floorplan_url": None,
        "id": f"avalon|{u.get('unitId')}",
    }


def fetch(url: str, timeout: int = 30) -> list[dict]:
    html = safefetch.get_text(url, timeout=timeout)
    return [_normalize(u) for u in _extract_units(html) if u.get("unitId")]


if __name__ == "__main__":
    import sys
    u = sys.argv[1] if len(sys.argv) > 1 else \
        "https://www.avaloncommunities.com/new-jersey/jersey-city-apartments/avalon-cove/"
    items = fetch(u)
    print(f"Parsed {len(items)} units from {u}\n")
    for x in sorted(items, key=lambda d: (d["beds"] or 0, d["price"] or 0)):
        print(f"  {x['beds']}BR ${x['price']} {str(x['sqft'])+'sf':<8} {x['unit']} | {x['available']}")
