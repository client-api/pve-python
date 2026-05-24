"""SC-61 — LXC container lifecycle against the pre-seeded vmid 200 ('tiny-ct')."""
from __future__ import annotations

import pytest

from clientapi_pve import Pve
from clientapi_pve.models.lxc_vm_start_request import LxcVmStartRequest
from clientapi_pve.models.lxc_vm_stop_request import LxcVmStopRequest
from e2e.conftest import requires_cgroupv2
from e2e.helpers.poll import wait_until

TINY_CT_VMID = 200


@requires_cgroupv2
def test_ct_start_status_stop(pve: Pve, node: str) -> None:
    initial = pve.lxc.vm_status(node=node, vmid=TINY_CT_VMID).data
    assert initial is not None

    if not str(initial.status).endswith("RUNNING"):
        pve.lxc.vm_start(
            node=node, vmid=TINY_CT_VMID, lxc_vm_start_request=LxcVmStartRequest()
        )

    def _is_running() -> bool:
        status = pve.lxc.vm_status(node=node, vmid=TINY_CT_VMID).data
        return status is not None and str(status.status).endswith("RUNNING")

    wait_until(_is_running, timeout_s=60, interval_s=2, label="CT 200 RUNNING")

    pve.lxc.vm_stop(
        node=node, vmid=TINY_CT_VMID, lxc_vm_stop_request=LxcVmStopRequest()
    )

    def _is_stopped() -> bool:
        status = pve.lxc.vm_status(node=node, vmid=TINY_CT_VMID).data
        return status is not None and str(status.status).endswith("STOPPED")

    wait_until(_is_stopped, timeout_s=60, interval_s=2, label="CT 200 STOPPED")
