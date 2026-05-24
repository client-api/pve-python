"""Capability gates for kernel features the test container may or may not have.

The proxmox-docker-action exposes `kvm-available` and `cgroupv2-available` as
step outputs; the workflow mirrors them into env vars. Locally, set them by hand.
"""
from __future__ import annotations

import os


def _truthy(name: str) -> bool:
    return os.environ.get(name, "").lower() in ("1", "true", "yes")


def kvm_available() -> bool:
    """True when /dev/kvm is usable inside the container (PVE can boot VMs)."""
    return _truthy("PROXMOX_KVM_AVAILABLE")


def cgroupv2_available() -> bool:
    """True when the host exposes cgroup v2 unified hierarchy (LXC requires it)."""
    return _truthy("PROXMOX_CGROUPV2_AVAILABLE")


def network_available() -> bool:
    """True unless PROXMOX_NO_NETWORK is set (air-gapped runners)."""
    return os.environ.get("PROXMOX_NO_NETWORK", "") != "1"
