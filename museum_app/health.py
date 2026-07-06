"""
Connectivity + local-gallery helpers for the Future Transport kiosk.

Two responsibilities, both offline-safe (no external dependency):
  * check_internet()  -- is the kiosk online right now?
  * recent_images()   -- the last N generated PNGs, for the offline gallery.
"""

import socket
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent / "output"

# TCP:53 to public DNS resolvers is a fast, firewall-friendly reachability probe.
_PROBE_TARGETS = [("1.1.1.1", 53), ("8.8.8.8", 53)]


def check_internet(timeout: float = 1.5) -> bool:
    """Return True if any probe target is reachable (i.e. the kiosk is online)."""
    for host, port in _PROBE_TARGETS:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except OSError:
            continue
    return False


def recent_images(limit: int = 10) -> list[Path]:
    """Return the newest generated images (most recent first), up to `limit`."""
    if not OUTPUT_DIR.exists():
        return []
    pngs = sorted(
        OUTPUT_DIR.glob("transport_*.png"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return pngs[:limit]
