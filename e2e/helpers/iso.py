"""Download and cache the 256-byte-vm boot.iso fixture with SHA-256 integrity check.

The release lives at github.com/client-api/256-byte-vm and is pinned by hash
so a tampered or partial download fails loudly instead of being silently used
in upload tests.
"""
from __future__ import annotations

import hashlib
import urllib.request
from pathlib import Path

BOOT_ISO_URL = (
    "https://github.com/client-api/256-byte-vm/releases/download/v1.0.0/boot.iso"
)
BOOT_ISO_SHA256 = "356703056dc4c605084411ef8614d9520d1cc14bb6727d39456e3464dc84bb02"

_CACHE_DIR = Path(__file__).resolve().parent.parent / ".cache"
_CACHE_PATH = _CACHE_DIR / "boot.iso"


class IsoIntegrityError(RuntimeError):
    """Raised when the downloaded ISO doesn't match BOOT_ISO_SHA256."""


def download_boot_iso() -> bytes:
    """Return the boot.iso bytes, cached on disk after the first call."""
    if _CACHE_PATH.exists():
        data = _CACHE_PATH.read_bytes()
        if _sha256(data) == BOOT_ISO_SHA256:
            return data
        _CACHE_PATH.unlink()  # stale cache, re-download

    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(BOOT_ISO_URL, timeout=30) as response:
        data = response.read()
    actual = _sha256(data)
    if actual != BOOT_ISO_SHA256:
        raise IsoIntegrityError(
            f"boot.iso SHA-256 mismatch: got {actual}, expected {BOOT_ISO_SHA256}"
        )
    _CACHE_PATH.write_bytes(data)
    return data


def _sha256(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()
