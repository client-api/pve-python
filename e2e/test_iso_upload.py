"""SC-35 — ISO download + upload + list + delete against a real storage."""
from __future__ import annotations

import os
import time

import pytest

from clientapi_pve import Pve
from clientapi_pve.exceptions import ApiException
from clientapi_pve.models.pve_storage_dir_config import PveStorageDirConfig
from clientapi_pve.models.storage_create_storage_request import (
    StorageCreateStorageRequest,
)
from e2e.conftest import requires_network
from e2e.helpers.iso import download_boot_iso
from e2e.helpers.upload import list_storage_content, upload_iso


@pytest.fixture
def iso_storage(pve: Pve):
    storage_id = "e2e-iso-store"
    path = "/var/tmp/e2e-iso-store"
    os.makedirs(path, exist_ok=True)
    pve.storage.create_storage(
        StorageCreateStorageRequest(
            PveStorageDirConfig(
                storage=storage_id,
                path=path,
                content="iso",
                type="dir",
            )
        )
    )
    # Give the storage manager a moment to register the new path.
    time.sleep(1)
    yield storage_id
    try:
        pve.storage.delete_storage(storage=storage_id)
    except ApiException:
        pass


@requires_network
def test_iso_download_upload_list_delete(pve: Pve, node: str, iso_storage: str) -> None:
    data = download_boot_iso()
    assert len(data) > 0

    filename = "e2e-boot.iso"
    upload_iso(pve, node, iso_storage, filename, data)

    listing = list_storage_content(pve, node, iso_storage)
    volids = [item.volid for item in listing]
    matching = [v for v in volids if v.endswith(f"/{filename}")]
    assert matching, f"uploaded ISO not in listing: {volids!r}"

    pve.nodesStorage.delete_content(node=node, storage=iso_storage, volume=matching[0])

    listing_after = list_storage_content(pve, node, iso_storage)
    volids_after = [item.volid for item in listing_after]
    assert not [v for v in volids_after if v.endswith(f"/{filename}")], volids_after
