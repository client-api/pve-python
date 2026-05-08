"""Example: resilient terminal session that auto-reconnects on glitch.

Run with:
    PVE_HOST=https://pve.example.com:8006 \\
    PVE_TOKEN='PVEAPIToken=root@pam!auto=...' \\
    PVE_NODE=orca PVE_VMID=100 \\
    python examples/resilient_terminal.py
"""

from __future__ import annotations

import os
import sys
import time

from pve_client.configuration import Configuration
from pve_client.websocket import QemuTarget
from pve_client.websocket_resilient import RetryOptions, connect_terminal_resilient


def main() -> None:
    config = Configuration(host=f"{os.environ.get('PVE_HOST', 'https://localhost:8006')}/api2/json")
    # OpenAPI auth-scheme name (NOT the `Authorization` header name).
    # The full `PVEAPIToken=…` string goes in here; no api_key_prefix.
    config.api_key["PVEApiToken"] = os.environ.get("PVE_TOKEN", "")

    target = QemuTarget(
        node=os.environ.get("PVE_NODE", "pve1"),
        vmid=int(os.environ.get("PVE_VMID", "100")),
    )

    session = connect_terminal_resilient(
        config, target,
        on_message=lambda text: sys.stdout.write(text),
        on_close=lambda code, reason: print(f"\n[final close: {code}]"),
        on_reconnect=lambda attempt: print(f"\n[reconnected after {attempt} attempts]"),
        on_give_up=lambda err: print(f"\n[retries exhausted: {err}]"),
        retry=RetryOptions(max_retries=20, initial_delay_s=0.25),
    )

    # Long-running session: send a command every 30 s for 5 minutes.
    session.send("date\n")
    deadline = time.monotonic() + 5 * 60
    while time.monotonic() < deadline:
        time.sleep(30)
        session.send("date\n")
    session.close()


if __name__ == "__main__":
    main()
