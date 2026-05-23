"""Example: open a terminal session against a QEMU VM.

Run with:
    PVE_HOST=https://pve.example.com:8006 \\
    PVE_TOKEN='PVEAPIToken=root@pam!auto=...' \\
    PVE_NODE=orca PVE_VMID=100 \\
    python examples/terminal.py

Requires: pip install websocket-client
"""

from __future__ import annotations

import os
import sys
import time

from clientapi_pve.configuration import Configuration
from clientapi_pve.pve import Pve
from clientapi_pve.websocket import QemuTarget


def main() -> None:
    config = Configuration(host=f"{os.environ.get('PVE_HOST', 'https://localhost:8006')}/api2/json")
    # `PVEApiToken` is the OpenAPI auth-scheme name the REST client keys
    # by; the *header* it lands on is `Authorization`. Put the full
    # `PVEAPIToken=…` string in here (no `api_key_prefix`).
    config.api_key["PVEApiToken"] = os.environ.get("PVE_TOKEN", "")

    pve = Pve(config)
    target = QemuTarget(
        node=os.environ.get("PVE_NODE", "pve1"),
        vmid=int(os.environ.get("PVE_VMID", "100")),
    )

    print(f"Opening terminal on {target.node}:qemu/{target.vmid}...")
    session = pve.connect_terminal(
        target,
        on_message=lambda text: sys.stdout.write(text),
        on_close=lambda code, reason: print(f"\n[closed: {code} {reason}]"),
        on_error=lambda exc: print(f"\n[error: {exc}]"),
    )

    session.resize(120, 32)
    session.send("uname -a\n")

    time.sleep(5)
    session.close()


if __name__ == "__main__":
    main()
