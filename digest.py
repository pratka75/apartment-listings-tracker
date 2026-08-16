"""
Render the daily digest as an HTML email, grouped by provider category
(e.g. "Newport Rentals", "Avalon Cove", "Other listings (RentCast)"). Within
each category, listings carry change badges: NEW, BACK, price drop/rise.

SECURITY: every value from an external site is HTML-escaped, and URLs are
restricted to http/https, so scraped content cannot inject markup or scripts.
"""

import html as _html
from datetime import date
from urllib.parse import quote_plus, urlsplit

from config import get_config

MAX_ROWS_PER_CATEGORY = 25


def esc(v) -> str:
    return _html.escape(str(v), quote=True)


def safe_url(u) -> str:
    if not u or not isinstance(u, str):
        return ""
    try:
        scheme = urlsplit(u).scheme.lower()
    except ValueError:
        return ""
    return esc(u) if scheme in ("http", "https") else ""


def _fmt(p):
    return f"${p:,}" if isinstance(p, (int, float)) else "?"


def category_of(l: dict) -> str:
    s = l.get("source")
    if s == "avalon":
        return l.get("building") or "Avalon"
    if s == "newport_rentals":
        return "Newport Rentals — Newport listings"
    if s == "rentcast":
        return "Other listings (RentCast)"
    return l.get("building") or (s or "Listings").replace("_", " ").title()


def _category_sort_key(name: str):
    # Specific buildings first (alpha); the generic RentCast bucket last.
    return (1, name) if name.startswith("Other listings") else (0, name)


def _badges(l, new_ids, back_ids, drop_map, rise_map):
    i = l["id"]
    out = []
    pill = ('display:inline-block;padding:1px 7px;border-radius:10px;font-size:11px;'
            'font-weight:700;margin-right:6px;')
    if i in new_ids:
        out.append(f'<span style="{pill}background:#e5f6ec;color:#1a7f4b;">NEW</span>')
    if i in back_ids:
        out.append(f'<span style="{pill}background:#e5f0fb;color:#2c6fbf;">BACK</span>')
    if i in drop_map:
        c = drop_map[i]
        out.append(f'<span style="{pill}background:#fbe9e7;color:#c0392b;">↓ '
                   f'{_fmt(c["old_price"])}→{_fmt(c["new_price"])} ({c["delta"]:+,})</span>')
    if i in rise_map:
        c = rise_map[i]
        out.append(f'<span style="{pill}background:#f0f0f0;color:#777;">↑ '
                   f'{_fmt(c["old_price"])}→{_fmt(c["new_price"])} ({c["delta"]:+,})</span>')
    return "".join(out)


def _row(l, badges="", note=""):
    price = _fmt(l.get("price"))
    title = esc(" ".join(x for x in [l.get("building") or "", l.get("unit") or ""] if x)
                or l.get("address") or "")
    addr = l.get("address") or l.get("formattedAddress") or ""
    beds, baths, sqft = l.get("beds", "?"), l.get("baths", "?"), l.get("sqft")
    size = f"{sqft:,} sf" if isinstance(sqft, int) else ""
    meta = esc(" · ".join(x for x in [f"{beds}BR/{baths}ba", size, l.get("available") or ""]
                          if x and x != "None"))
    link = safe_url(l.get("url", ""))
    name = f'<a href="{link}" style="color:#1a5;text-decoration:none;">{title}</a>' if link else title

    extras = []
    fp = safe_url(l.get("floorplan_url"))
    if fp:
        extras.append(f'<a href="{fp}" style="color:#39c;font-size:12px;">floor plan</a>')
    if addr:
        extras.append(f'<a href="https://www.google.com/search?q={quote_plus(addr + " apartment for rent")}" '
                      f'style="color:#39c;font-size:12px;">search</a>')
    linkbar = " · ".join(extras)
    return (f'<tr><td style="padding:6px 10px;font-weight:600;vertical-align:top;white-space:nowrap;">{price}</td>'
            f'<td style="padding:6px 10px;">{badges and badges + "<br>"}{name}'
            f'<br><span style="color:#777;font-size:12px;">{esc(addr)}</span>'
            f'{("<br>" + linkbar) if linkbar else ""}{note}</td>'
            f'<td style="padding:6px 10px;color:#555;font-size:13px;vertical-align:top;">{meta}</td></tr>')


def _table(rows):
    return (f'<table style="border-collapse:collapse;width:100%;font-family:Arial,sans-serif;">'
            f'{rows}</table>')


def _h2(title, color="#1a5"):
    return (f'<h2 style="font-size:16px;margin:24px 0 6px;border-bottom:2px solid {color};'
            f'padding-bottom:4px;color:#222;">{esc(title)}</h2>')


def build_html(current, changes, cfg=None, manual_links=None) -> str:
    cfg = cfg or get_config()
    budget = cfg["search"]["max_rent"]

    new_ids = {l["id"] for l in changes["new"]}
    back_ids = {l["id"] for l in changes["back_in_market"]}
    drop_map = {c["listing"]["id"]: c for c in changes["price_changes"] if c["delta"] < 0}
    rise_map = {c["listing"]["id"]: c for c in changes["price_changes"] if c["delta"] > 0}
    changed = new_ids | back_ids | set(drop_map) | set(rise_map)

    # Group current listings by provider category.
    groups: dict[str, list] = {}
    for l in current:
        groups.setdefault(category_of(l), []).append(l)

    parts = [f'<div style="max-width:700px;margin:auto;font-family:Arial,sans-serif;color:#222;'
             f'background:#fff;padding:20px;border-radius:8px;">',
             f'<h1 style="font-size:20px;">🏙️ Apartment Alert — {date.today():%b %d, %Y}</h1>',
             f'<p style="color:#555;">{len(new_ids)} new · {len(drop_map)} price drops · '
             f'{len(rise_map)} increases · {len(changes["removed"])} removed · '
             f'{len(back_ids)} back. In-budget threshold ≤ ${budget:,}.</p>']

    for cat in sorted(groups, key=_category_sort_key):
        items = groups[cat]
        # Show in-budget listings and anything that changed; if none, show cheapest 2.
        show = [l for l in items if (l.get("price") or 1e9) <= budget or l["id"] in changed]
        note = ""
        if not show:
            show = sorted((l for l in items if l.get("price")), key=lambda x: x["price"])[:2]
            note = " (cheapest shown — none in budget)"
        show = sorted(show, key=lambda x: x.get("price") or 1e9)
        extra_note = ""
        if len(show) > MAX_ROWS_PER_CATEGORY:
            hidden = len(show) - MAX_ROWS_PER_CATEGORY
            show = show[:MAX_ROWS_PER_CATEGORY]
            extra_note = f'<tr><td colspan="3" style="padding:6px 10px;color:#999;font-size:12px;">' \
                         f'…and {hidden} more in this category.</td></tr>'
        rows = "".join(_row(l, _badges(l, new_ids, back_ids, drop_map, rise_map)) for l in show)
        parts.append(_h2(f"{cat}{note}"))
        parts.append(_table(rows + extra_note))

    # Removed (across all categories).
    if changes["removed"]:
        rows = "".join(_row(l) for l in changes["removed"])
        parts.append(_h2("❌ Removed (likely rented)", color="#999"))
        parts.append(_table(rows))

    # Links we couldn't auto-scrape — surfaced for a manual check.
    if manual_links:
        parts.append(_h2("🔗 Check manually (not auto-scraped)", color="#a60"))
        li = "".join(
            f'<li style="margin:4px 0;"><a href="{safe_url(m["url"])}" style="color:#2c6fbf;">'
            f'{esc(m["url"])}</a><br><span style="color:#777;font-size:12px;">{esc(m["reason"])}</span></li>'
            for m in manual_links)
        parts.append(f'<ul style="padding-left:18px;font-family:Arial,sans-serif;">{li}</ul>')

    parts.append('<p style="color:#aaa;font-size:12px;margin-top:24px;">'
                 'Automated daily digest — apartment-listings-tracker.</p></div>')
    return "".join(parts)
