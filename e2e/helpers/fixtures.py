"""Test fixture conventions and cleanup primitives.

All entities created by E2E tests are named with the `e2e-` prefix and live in
the VM ID range 101..199 (VM 100 is the pre-seeded `tiny-test` fixture; VMs
below 100 are PVE internal). Cleanup is best-effort and idempotent.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from clientapi_pve import Pve

log = logging.getLogger(__name__)

E2E_PREFIX = "e2e-"
VM_ID_MIN = 101
VM_ID_MAX = 199


def first_node(pve: "Pve") -> str:
    """Return the first node name reported by /nodes (single-node test cluster)."""
    response = pve.nodes.get_nodes()
    nodes = getattr(response, "data", None) or []
    if not nodes:
        raise RuntimeError("no PVE nodes found — is the cluster running?")
    name = getattr(nodes[0], "node", None)
    if not name:
        raise RuntimeError(f"first node has no .node attribute: {nodes[0]!r}")
    return name


def cleanup_e2e(pve: "Pve", node: str) -> None:
    """Best-effort cleanup of every e2e-* entity created by this suite.

    Errors are logged and swallowed so a partial environment doesn't block
    subsequent setup. Safe to call before AND after the test session.
    """
    _cleanup_users(pve)
    _cleanup_storages(pve)
    _cleanup_vms(pve, node)


def _cleanup_users(pve: "Pve") -> None:
    try:
        response = pve.accessUsers.get_users()
    except Exception as exc:
        log.debug("user list failed during cleanup: %r", exc)
        return
    for user in getattr(response, "data", None) or []:
        userid = getattr(user, "userid", "") or ""
        if userid.startswith(E2E_PREFIX):
            try:
                pve.accessUsers.delete_user(userid=userid)
            except Exception as exc:
                log.debug("delete_user(%s) failed: %r", userid, exc)


def _cleanup_storages(pve: "Pve") -> None:
    try:
        response = pve.storage.get_storage()
    except Exception as exc:
        log.debug("storage list failed during cleanup: %r", exc)
        return
    for storage in getattr(response, "data", None) or []:
        storage_id = getattr(storage, "storage", "") or ""
        if storage_id.startswith(E2E_PREFIX):
            try:
                pve.storage.delete_storage(storage=storage_id)
            except Exception as exc:
                log.debug("delete_storage(%s) failed: %r", storage_id, exc)


def _cleanup_vms(pve: "Pve", node: str) -> None:
    try:
        response = pve.qemu.vmlist(node=node)
    except Exception as exc:
        log.debug("qemu list failed during cleanup: %r", exc)
        return
    for vm in getattr(response, "data", None) or []:
        vmid = getattr(vm, "vmid", None)
        if vmid is None or not (VM_ID_MIN <= int(vmid) <= VM_ID_MAX):
            continue
        try:
            pve.qemu.destroy_vm(node=node, vmid=int(vmid), purge=1, skiplock=1)
        except Exception as exc:
            log.debug("destroy_vm(%s) failed: %r", vmid, exc)
