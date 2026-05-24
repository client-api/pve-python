"""ISO/snippet upload + listing helpers.

The PVE `/nodes/{node}/storage/{storage}/upload` endpoint is multipart/form-data
with a binary file part. The OpenAPI spec models the file as a `tmpfilename`
reference, so the generated `NodesStorageApi.upload` method cannot carry actual
bytes — it just sends the metadata. We use a raw multipart POST that reuses
the ApiClient's host + Authorization header.

Tracked as a generator gap; document on the SC-35 test.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import requests

if TYPE_CHECKING:
    from clientapi_pve import Pve


class UploadError(RuntimeError):
    """Raised when the multipart upload returns a non-2xx response."""


def _auth_url(pve: "Pve", path: str) -> tuple[str, dict[str, str], bool]:
    cfg = pve.api_client.configuration
    url = f"{cfg.host.rstrip('/')}{path}"
    auth_header = cfg.api_key.get("PVEApiToken")
    if not auth_header:
        raise UploadError("raw-upload helpers require PVEApiToken auth")
    return url, {"Authorization": auth_header}, cfg.verify_ssl


def upload_iso(pve: "Pve", node: str, storage: str, filename: str, data: bytes) -> str:
    url, headers, verify = _auth_url(
        pve, f"/nodes/{node}/storage/{storage}/upload"
    )
    files = {
        "content": (None, "iso"),
        "filename": (filename, data, "application/octet-stream"),
    }
    response = requests.post(url, headers=headers, files=files, verify=verify, timeout=120)
    if response.status_code >= 400:
        raise UploadError(
            f"upload failed: HTTP {response.status_code} {response.text[:300]}"
        )
    return (response.json() or {}).get("data") or ""


def list_storage_content(pve: "Pve", node: str, storage: str) -> list[dict]:
    """Return the raw content list for a storage.

    The SDK's `NodesStorageApi.diridx` response model mistypes the inner items
    (data deserializes as the wrong class and `volid` comes back empty), so we
    parse the raw JSON ourselves. Tracked as a generator gap.
    """
    url, headers, verify = _auth_url(
        pve, f"/nodes/{node}/storage/{storage}/content"
    )
    response = requests.get(url, headers=headers, verify=verify, timeout=30)
    if response.status_code >= 400:
        raise UploadError(
            f"list failed: HTTP {response.status_code} {response.text[:300]}"
        )
    return (response.json() or {}).get("data") or []
