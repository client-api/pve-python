"""SC-01 — anonymous /version endpoint returns the expected shape."""
from __future__ import annotations

import re

from clientapi_pve import Pve


def test_version_returns_release_and_version(pve: Pve) -> None:
    response = pve.version.version()
    data = response.data
    assert data.release, "release missing"
    assert data.version, "version missing"
    assert data.repoid, "repoid missing"
    # Spec constraint: 8..64 hex chars (matches the field validator).
    assert re.match(r"^[0-9a-fA-F]{8,64}$", data.repoid), data.repoid
    # release looks like "9.0" / "9.2" — major.minor
    assert re.match(r"^\d+\.\d+$", data.release), data.release
