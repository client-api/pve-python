"""Shared pytest fixtures and capability gates for the E2E suite."""
from __future__ import annotations

from typing import Iterator

import pytest

from clientapi_pve import Configuration, Pve
from e2e.helpers.capability_gate import (
    cgroupv2_available,
    kvm_available,
    network_available,
)
from e2e.helpers.credentials import Credentials, MissingCredentialError
from e2e.helpers.fixtures import cleanup_e2e, first_node

# Declared once here so test files import a symbol rather than re-checking env vars.
requires_kvm = pytest.mark.skipif(not kvm_available(), reason="KVM not available")
requires_cgroupv2 = pytest.mark.skipif(
    not cgroupv2_available(), reason="cgroup v2 not available"
)
requires_network = pytest.mark.skipif(
    not network_available(), reason="network not available (PROXMOX_NO_NETWORK=1)"
)


@pytest.fixture(scope="session")
def creds() -> Credentials:
    try:
        return Credentials.from_env()
    except MissingCredentialError as exc:
        pytest.skip(str(exc))


def _token_client(creds: Credentials) -> Pve:
    cfg = Configuration(host=f"{creds.url}/api2/json")
    cfg.verify_ssl = not creds.insecure
    cfg.api_key["PVEApiToken"] = creds.token_header_value
    return Pve(cfg)


@pytest.fixture(scope="session")
def pve(creds: Credentials) -> Pve:
    """Default client: API-token auth (no CSRF dance)."""
    return _token_client(creds)


@pytest.fixture(scope="session")
def node(pve: Pve) -> str:
    return first_node(pve)


@pytest.fixture(scope="session", autouse=True)
def _session_cleanup(creds: Credentials, pve: Pve) -> Iterator[None]:
    """Wipe any e2e-* leftovers before and after the suite."""
    try:
        node = first_node(pve)
    except Exception:
        node = ""
    if node:
        cleanup_e2e(pve, node)
    yield
    if node:
        cleanup_e2e(pve, node)
