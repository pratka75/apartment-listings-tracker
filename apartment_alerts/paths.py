"""Shared filesystem paths. Runtime data (config, secrets, snapshot) lives at the
repository root, regardless of where these modules sit inside the package."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # repo root (apartment_alerts/ -> root)
