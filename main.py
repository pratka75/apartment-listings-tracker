"""
Entry point for the apartment-listings tracker.

Run:
  python main.py            normal run; writes digest.html
  python main.py --email    also email the digest
  python main.py --no-save  dry run; do not update the snapshot
"""

from apartment_alerts.cli import main

if __name__ == "__main__":
    main()
