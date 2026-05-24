"""SC-61 — LXC container lifecycle against the pre-seeded vmid 200 ('tiny-ct')."""
from __future__ import annotations

import pytest

from clientapi_pve import Pve
from e2e.conftest import requires_cgroupv2
from e2e.helpers.poll import wait_until

TINY_CT_VMID = 200


@requires_cgroupv2
@pytest.mark.xfail(
    reason=(
        "Generator gap: LxcVmStatusResponseData.pressure{cpu,io,memory}{some,full} "
        "are typed Union[float, int] but PVE returns string values like '0.00'. "
        "Pydantic rejects the deserialization. Tracked upstream — either the spec "
        "should type these as string or the model should accept str + parse. "
        "Auto-promotes once the template is fixed."
    ),
    strict=False,
    raises=Exception,
)
def test_ct_start_status_stop(pve: Pve, node: str) -> None:
    initial = pve.lxc.vm_status(node=node, vmid=TINY_CT_VMID).data
    assert initial is not None

    if not str(initial.status).endswith("RUNNING"):
        pve.lxc.vm_start(node=node, vmid=TINY_CT_VMID)

    def _is_running() -> bool:
        status = pve.lxc.vm_status(node=node, vmid=TINY_CT_VMID).data
        return status is not None and str(status.status).endswith("RUNNING")

    wait_until(_is_running, timeout_s=60, interval_s=2, label="CT 200 RUNNING")

    pve.lxc.vm_stop(node=node, vmid=TINY_CT_VMID)

    def _is_stopped() -> bool:
        status = pve.lxc.vm_status(node=node, vmid=TINY_CT_VMID).data
        return status is not None and str(status.status).endswith("STOPPED")

    wait_until(_is_stopped, timeout_s=60, interval_s=2, label="CT 200 STOPPED")
