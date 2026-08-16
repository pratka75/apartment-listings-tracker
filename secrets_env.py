"""
Dependency-free secret loading. Resolution order for each name:

  1. Real environment variable (best for cloud / CI)
  2. A gitignored `.env` file in the project root  (KEY=VALUE lines)
  3. Legacy per-secret text files (back-compat with the original setup)

Secrets are never printed or logged by this module.
"""

import os
from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).parent
ENV_FILE = HERE / ".env"

# Back-compat: map secret names to the original single-value files.
_LEGACY_FILES = {
    "RENTCAST_API_KEY": "apikey.txt",
    "GMAIL_SENDER": "gmail_sender.txt",
    "GMAIL_APP_PASSWORD": "gmail_app_password.txt",
}


@lru_cache(maxsize=1)
def _dotenv() -> dict:
    values = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            values[key.strip()] = val.strip().strip('"').strip("'")
    return values


def get_secret(name: str, required: bool = True) -> str | None:
    val = os.environ.get(name) or _dotenv().get(name)
    if not val:
        legacy = _LEGACY_FILES.get(name)
        if legacy and (HERE / legacy).exists():
            val = (HERE / legacy).read_text(encoding="utf-8").strip()
    if not val and required:
        raise SystemExit(
            f"Missing secret {name}. Set it in your environment or in a .env file "
            f"(see .env.example). This value must never be committed to git."
        )
    return val or None
