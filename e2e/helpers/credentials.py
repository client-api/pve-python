"""Load PROXMOX_* environment variables exported by client-api/proxmox-docker-action@v1.

The action writes credentials into $GITHUB_ENV; locally `docker-compose.yml`
plus `/run/credentials.json` in the container supply the same shape.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


class MissingCredentialError(RuntimeError):
    """Raised when a required PROXMOX_* env var is missing."""


@dataclass(frozen=True)
class Credentials:
    url: str
    user: str
    password: str
    token_header_value: str
    token_value: str
    insecure: bool

    @classmethod
    def from_env(cls) -> "Credentials":
        url = _required("PROXMOX_URL")
        return cls(
            url=url.rstrip("/"),
            user=_required("PROXMOX_USER"),
            password=_required("PROXMOX_PASSWORD"),
            token_header_value=_required("PROXMOX_TOKEN_HEADER_VALUE"),
            token_value=os.environ.get("PROXMOX_TOKEN_VALUE", ""),
            insecure=os.environ.get("PROXMOX_INSECURE", "").lower() in ("1", "true", "yes"),
        )


def _required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise MissingCredentialError(
            f"{name} is not set. Run client-api/proxmox-docker-action@v1 in CI "
            f"or export it manually for local runs."
        )
    return value
