#!/usr/bin/env python3
"""
Pre-commit secret scanner. Fails (exit 1) if any file that WOULD be committed
looks like it contains a real secret. Run manually or wire it as a git hook:

    python scripts/check_secrets.py

    # or as .git/hooks/pre-commit (make it executable):
    #!/bin/sh
    python scripts/check_secrets.py || exit 1

It intentionally errs toward caution. Placeholder values (containing "example",
"your_", "here", "placeholder", "changeme") are ignored.
"""

import re
import subprocess
import sys
from pathlib import Path

# Ensure Unicode-safe output on Windows consoles (cp1252).
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
PLACEHOLDERS = ("example", "your_", "your-", "here", "placeholder", "changeme", "xxxx")

# Files that must never be tracked at all. (config.local.json is intentionally
# committed in this personal tracker repo — filters only, no secrets — so it is
# NOT forbidden here. It remains forbidden in the shareable digest project.)
FORBIDDEN_NAMES = {".env", "apikey.txt", "gmail_sender.txt", "gmail_app_password.txt",
                   "snapshot.json", "rentcast_usage.json"}

# Suspicious content patterns.
PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|app[_-]?password|secret|token)\s*[=:]\s*['\"]?([A-Za-z0-9_\-]{16,})"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),                 # AWS
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),               # generic sk- keys
    re.compile(r"(?i)gmail_app_password\s*[=:]\s*\S{8,}"),
]


def candidate_files():
    """Files that git would include (tracked + untracked-not-ignored), or a walk fallback."""
    try:
        out = subprocess.run(["git", "ls-files", "-co", "--exclude-standard"],
                             cwd=ROOT, capture_output=True, text=True, check=True)
        files = [ROOT / f for f in out.stdout.splitlines() if f]
        if files:
            return files
    except Exception:
        pass
    # Fallback: walk, skipping obvious ignored dirs.
    skip = {".git", "__pycache__"}
    return [p for p in ROOT.rglob("*")
            if p.is_file() and not (set(p.relative_to(ROOT).parts) & skip)]


def looks_placeholder(s: str) -> bool:
    return any(p in s.lower() for p in PLACEHOLDERS)


def main() -> int:
    findings = []
    for f in candidate_files():
        if f.name in FORBIDDEN_NAMES:
            findings.append(f"{f.name}: secret/private file is not gitignored (would be committed!)")
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if looks_placeholder(line):
                continue
            for pat in PATTERNS:
                m = pat.search(line)
                if m:
                    findings.append(f"{f.relative_to(ROOT)}:{i}: possible secret -> {line.strip()[:80]}")
                    break

    if findings:
        print("[FAIL] Potential secrets detected — commit blocked:\n")
        for x in findings:
            print("  " + x)
        print("\nMove secrets to .env (gitignored) and remove them from tracked files.")
        return 1
    print("[OK] No secrets detected in committable files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
