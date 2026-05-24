"""SC-62 — boot VM 101 from an uploaded ISO (depends on SC-35).

This is the most kernel-bound scenario: KVM must be available **and** we must
have network access to download the boot.iso. We also need cgroup support for
the storage to be active. If any gate is closed the test soft-skips.
"""
from __future__ import annotations

import os
import time

import pytest

from clientapi_pve import Pve
from clientapi_pve.exceptions import ApiException
from clientapi_pve.models.pve_memory_config import PveMemoryConfig
from clientapi_pve.models.pve_memory_field import PveMemoryField
from clientapi_pve.models.pve_storage_dir_config import PveStorageDirConfig
from clientapi_pve.models.qemu_create_vm_request import QemuCreateVmRequest
from clientapi_pve.models.qemu_vm_start_request import QemuVmStartRequest
from clientapi_pve.models.qemu_vm_stop_request import QemuVmStopRequest
from clientapi_pve.models.storage_create_storage_request import (
    StorageCreateStorageRequest,
)
from e2e.conftest import requires_kvm, requires_network
from e2e.helpers.iso import download_boot_iso
from e2e.helpers.poll import wait_until
from e2e.helpers.upload import list_storage_content, upload_iso

CDROM_VMID = 101


@requires_kvm
@requires_network
@pytest.mark.xfail(
    reason=(
        "Generator gap: QemuCreateVmRequest.to_dict() references undefined "
        "indexed-family fields (ide0/net0/…) instead of the collapsed `ides`/`nets` "
        "maps the model actually defines. Tracked upstream in pve-openapi; the "
        "test stays here so it auto-promotes once the template is fixed."
    ),
    strict=False,
    raises=AttributeError,
)
def test_vm_boot_from_iso(pve: Pve, node: str) -> None:
    storage_id = "e2e-cdrom-store"
    path = "/var/tmp/e2e-cdrom-store"
    os.makedirs(path, exist_ok=True)
    pve.storage.create_storage(
        StorageCreateStorageRequest(
            PveStorageDirConfig(
                storage=storage_id, path=path, content="iso", type="dir"
            )
        )
    )
    time.sleep(1)

    iso_name = "e2e-cdrom-boot.iso"
    try:
        upload_iso(pve, node, storage_id, iso_name, download_boot_iso())

        listing = list_storage_content(pve, node, storage_id)
        volids = [item.get("volid", "") for item in listing]
        volid = next((v for v in volids if v.endswith(f"/{iso_name}")), None)
        assert volid, f"ISO not found after upload: {volids!r}"

        # Create a tiny VM that boots from the CDROM volume.
        pve.qemu.create_vm(
            node=node,
            qemu_create_vm_request=QemuCreateVmRequest(
                vmid=CDROM_VMID,
                memory=PveMemoryField(PveMemoryConfig(current=64)),
                cores=1,
                cdrom=f"{volid},media=cdrom",
            ),
        )
        try:
            pve.qemu.vm_start(
                node=node, vmid=CDROM_VMID, qemu_vm_start_request=QemuVmStartRequest()
            )

            def _is_running() -> bool:
                status = pve.qemu.vm_status(node=node, vmid=CDROM_VMID).data
                return status is not None and str(status.status).endswith("RUNNING")

            wait_until(_is_running, timeout_s=60, interval_s=2, label=f"VM {CDROM_VMID} RUNNING")

            pve.qemu.vm_stop(
                node=node, vmid=CDROM_VMID, qemu_vm_stop_request=QemuVmStopRequest()
            )
        finally:
            try:
                pve.qemu.destroy_vm(node=node, vmid=CDROM_VMID, purge=1, skiplock=1)
            except ApiException:
                pass
    finally:
        try:
            pve.storage.delete_storage(storage=storage_id)
        except ApiException:
            pass
