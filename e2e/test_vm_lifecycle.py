"""SC-60 — QEMU VM lifecycle against the pre-seeded vmid 100 ('tiny-test')."""
from __future__ import annotations

import pytest

from clientapi_pve import Pve
from clientapi_pve.models.qemu_vm_start_request import QemuVmStartRequest
from clientapi_pve.models.qemu_vm_stop_request import QemuVmStopRequest
from e2e.conftest import requires_kvm
from e2e.helpers.poll import wait_until

TINY_TEST_VMID = 100


@requires_kvm
def test_vm_start_status_stop(pve: Pve, node: str) -> None:
    initial = pve.qemu.vm_status(node=node, vmid=TINY_TEST_VMID).data
    assert initial is not None

    # PVE's POST endpoints require a JSON body even when empty; the SDK omits
    # the body unless we pass an explicit (empty) request model. Without this,
    # PVE returns 500 "malformed JSON string".
    if not str(initial.status).endswith("RUNNING"):
        pve.qemu.vm_start(
            node=node, vmid=TINY_TEST_VMID, qemu_vm_start_request=QemuVmStartRequest()
        )

    def _is_running() -> bool:
        status = pve.qemu.vm_status(node=node, vmid=TINY_TEST_VMID).data
        return status is not None and str(status.status).endswith("RUNNING")

    wait_until(_is_running, timeout_s=60, interval_s=2, label="VM 100 RUNNING")

    # Stop and wait for "stopped".
    pve.qemu.vm_stop(
        node=node, vmid=TINY_TEST_VMID, qemu_vm_stop_request=QemuVmStopRequest()
    )

    def _is_stopped() -> bool:
        status = pve.qemu.vm_status(node=node, vmid=TINY_TEST_VMID).data
        return status is not None and str(status.status).endswith("STOPPED")

    wait_until(_is_stopped, timeout_s=60, interval_s=2, label="VM 100 STOPPED")
