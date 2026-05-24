"""ISO/snippet upload + content-listing helpers — thin SDK shims."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from clientapi_pve import Pve


def upload_iso(pve: "Pve", node: str, storage: str, filename: str, data: bytes) -> str:
    response = pve.nodesStorage.upload(
        node=node,
        storage=storage,
        content="iso",
        filename=(filename, data),
    )
    return getattr(response, "data", "") or ""


def list_storage_content(pve: "Pve", node: str, storage: str) -> list:
    response = pve.nodesStorage.get_content(node=node, storage=storage)
    return getattr(response, "data", None) or []
