"""
Fetcher for Newport Rentals (LeFrak) — parses the public 2BR availability page.
Free (no API cost). Returns a list of normalized listing dicts.

Normalized listing schema (shared across all sources):
    {
      "source":   "newport_rentals",
      "building":  "Parkside East",
      "unit":      "Residence 303",
      "address":   "30 Newport Parkway",
      "beds":      2,
      "baths":     1.0,
      "sqft":      863,
      "price":     3808,            # int USD/month, or None
      "available": "Available Now", # raw availability text
      "url":       "https://www.newportrentals.com/2-bedroom-apartments-jersey-city/",
      "id":        "newport_rentals|parkside east|residence 303",  # stable key
    }
"""

import re

import safefetch

URL = "https://www.newportrentals.com/2-bedroom-apartments-jersey-city/"


def _text(html_fragment: str) -> str:
    """Strip tags and collapse whitespace."""
    t = re.sub(r"<[^>]+>", " ", html_fragment)
    return re.sub(r"\s+", " ", t).strip()


def _first(pattern: str, text: str, default=None):
    m = re.search(pattern, text, re.DOTALL)
    return m.group(1).strip() if m else default


def _col(block: str, col: str) -> str:
    """Return the stripped text of a given availabilitylistings column."""
    m = re.search(rf'column--{col}">(.*?)</div>', block, re.DOTALL)
    return _text(m.group(1)) if m else ""


def fetch(url: str = URL, timeout: int = 30) -> list[dict]:
    html = safefetch.get_text(url, timeout=timeout)

    # Each unit row starts at a building-name span. Split there and parse each block.
    marker = 'availabilitylistings__building-name"'
    parts = html.split(marker)[1:]  # drop the pre-first-unit preamble
    listings = []

    for block in parts:
        block = block[:8000]  # a single row (incl. floor-plan SVG) fits well under this

        building = _first(r">\s*([^<]+?)\s*<span", block)  # name before the "|" sep span
        unit = _first(r'residence-name">\s*([^<]+?)\s*<', block)
        # address is the 2nd data-text span in the name column
        addr = _first(r'data-text">\s*([0-9][^<]+?)\s*</span>', block)

        layout = _col(block, "layout")
        beds = _first(r"(\d+)\s*Bedroom", layout)
        baths = _first(r"([\d.]+)\s*Bathroom", layout)

        sqft_raw = _col(block, "sqft")
        sqft = _first(r"([\d,]+)", sqft_raw) if sqft_raw else None

        rent_raw = _col(block, "rent")
        price = _first(r"\$([\d,]+)", rent_raw)
        available = re.sub(r"^\$[\d,]+\s*", "", rent_raw).strip() or None

        # Per-unit floor-plan PDF (public asset, no API involved).
        floorplan = _first(r'href="(https://adkastcdn[^"]+\.pdf)"', block)

        if not (building and unit):
            continue

        listings.append({
            "source": "newport_rentals",
            "building": building,
            "unit": unit,
            "address": addr,
            "beds": int(beds) if beds else None,
            "baths": float(baths) if baths else None,
            "sqft": int(sqft.replace(",", "")) if sqft else None,
            "price": int(price.replace(",", "")) if price else None,
            "available": available,
            "url": url,                    # live availability page (check price / inquire)
            "floorplan_url": floorplan,    # this unit's floor-plan PDF
            "id": f"newport_rentals|{building.lower()}|{unit.lower()}",
        })

    return listings


if __name__ == "__main__":
    items = fetch()
    print(f"Parsed {len(items)} units from the Newport Rentals 2BR page\n")
    for x in sorted(items, key=lambda d: d["price"] or 0):
        if x["price"]:
            print(f"  ${x['price']:<6} {x['beds']}BR/{x['baths']}ba {str(x['sqft'])+'sf':<7} "
                  f"| {x['building']} {x['unit']} | {x['available']}")
