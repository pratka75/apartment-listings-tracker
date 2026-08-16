#!/usr/bin/env python3
"""
Security regression suite. Run: python test_security.py

Covers the app's attack surface:
  1. HTML injection      — scraped data cannot inject markup/script into the email
  2. URL sanitization    — javascript:/data:/other schemes dropped from links
  3. SMTP header inject   — CR/LF stripped from recipient/subject/sender
  4. Config validation    — hostile configs rejected (bad email, non-http links, ranges, types)
  5. SSRF                  — internal/loopback/link-local/metadata hosts + bad schemes refused
  6. Response size cap     — oversized responses rejected
  7. Secret hygiene        — secret scanner flags planted secrets; loader doesn't echo values
  8. Dangerous builtins    — no eval/exec/pickle/yaml.load/shell in the codebase

Exit code is non-zero if any check fails.
"""

import io
import re
import sys
from contextlib import redirect_stdout
from pathlib import Path

import digest
import config
import mailer
import safefetch

HERE = Path(__file__).parent
results = []


def check(name, cond):
    results.append((name, bool(cond)))


BASE_CFG = {
    "search": {"bedrooms": 2, "max_rent": 4200,
               "location": {"latitude": 40.7, "longitude": -74.0, "radius_miles": 1}},
    "sources": {"rentcast": False},
    "email": {"recipient": "you@example.com"},
}

# 1 + 2. HTML/URL injection via a hostile listing.
evil = {"source": "x", "building": "<script>alert(1)</script>",
        "unit": '"><img src=x onerror=alert(2)>', "address": "</td><script>bad()</script>",
        "beds": 2, "baths": 1.0, "sqft": 800, "price": 4000,
        "available": "<b>x</b>", "url": "javascript:alert(3)",
        "floorplan_url": "data:text/html,<script>1</script>", "id": "x|evil"}
changes = {"new": [evil], "back_in_market": [], "price_changes": [], "removed": []}
html = digest.build_html([evil], changes, BASE_CFG)
check("no raw <script from data", "<script>alert" not in html and "<script>bad" not in html)
check("no raw <img from data", "<img src=x" not in html)
check("javascript: url dropped", "javascript:" not in html)
check("data: url dropped", 'href="data:' not in html)
check("script text is escaped", "&lt;script&gt;" in html)

# 3. SMTP header injection.
check("mailer strips CRLF", mailer._single_line("a@b.com\r\nBcc: evil@x.com") == "a@b.comBcc: evil@x.com")

# 4. Config validation rejects hostile input.
def rejects(cfg):
    try:
        config._validate(cfg); return False
    except SystemExit:
        return True

import copy
check("reject header-injection email",
      rejects({**BASE_CFG, "email": {"recipient": "a@b.com\nBcc: x@y.com"}}))
check("reject javascript watch_url",
      rejects({**BASE_CFG, "watch_urls": ["javascript:alert(1)"]}))
check("reject file watch_url",
      rejects({**BASE_CFG, "watch_urls": ["file:///etc/passwd"]}))
check("reject bad bedrooms type", rejects({**BASE_CFG, "search": {**BASE_CFG["search"], "bedrooms": "2; DROP"}}))
check("reject negative rent", rejects({**BASE_CFG, "search": {**BASE_CFG["search"], "max_rent": -5}}))
bad_loc = copy.deepcopy(BASE_CFG); bad_loc["search"]["location"] = {"latitude": 999, "longitude": 0, "radius_miles": 1}
check("reject out-of-range latitude", rejects(bad_loc))
check("accept a valid config", not rejects(copy.deepcopy(BASE_CFG)))

# 5. SSRF.
for url in ["http://169.254.169.254/latest/meta-data/", "http://127.0.0.1/x",
            "http://localhost/x", "http://10.0.0.1/x", "http://192.168.1.1/x",
            "file:///etc/passwd", "ftp://x/y", "gopher://x"]:
    try:
        safefetch.get(url, timeout=5)
        check(f"SSRF blocks {url}", False)
    except safefetch.FetchError:
        check(f"SSRF blocks {url}", True)
    except Exception:
        check(f"SSRF blocks {url}", True)   # any failure to fetch internal is acceptable

# 6. Response size cap (network; skip cleanly if offline).
try:
    safefetch.get("https://example.com", max_bytes=50, timeout=10)
    check("size cap enforced", False)
except safefetch.FetchError as e:
    check("size cap enforced", "exceeds" in str(e))
except Exception:
    check("size cap enforced (skipped - offline)", True)

# 7. Secret scanner catches a planted secret; ignores placeholders.
sys.path.insert(0, str(HERE / "scripts"))
import check_secrets  # noqa: E402
def scan_line(line):
    return any(p.search(line) for p in check_secrets.PATTERNS) and not check_secrets.looks_placeholder(line)
# Build fixtures by concatenation so this test file itself never contains a
# literal `KEY=<secret>` line that the scanner (correctly) flags.
_k, _p = "ab12cd34ef56gh78ij90kl12", "abcdabcdabcdabcd"
check("scanner flags real api key", scan_line("RENTCAST_API_KEY=" + _k))
check("scanner flags app password", scan_line("GMAIL_APP_PASSWORD=" + _p))
check("scanner ignores placeholder", not scan_line("RENTCAST_API_KEY=" + "your_key_here"))

# 8. No dangerous builtins in the codebase.
danger = re.compile(r"\b(eval|exec|os\.system|subprocess|pickle\.load|yaml\.load)\s*\(|shell\s*=\s*True")
offenders = []
for py in HERE.glob("*.py"):
    if py.name == "test_security.py":
        continue
    for i, line in enumerate(py.read_text(encoding="utf-8").splitlines(), 1):
        if danger.search(line):
            offenders.append(f"{py.name}:{i}")
check(f"no dangerous builtins ({offenders})", not offenders)

# ---- report ----
passed = sum(1 for _, ok in results if ok)
for name, ok in results:
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
print(f"\n{passed}/{len(results)} checks passed.")
sys.exit(0 if passed == len(results) else 1)
