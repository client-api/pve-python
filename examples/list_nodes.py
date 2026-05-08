"""Example: list cluster nodes.

Run with:
    PVE_HOST=https://pve.example.com:8006 \\
    PVE_TOKEN='PVEAPIToken=root@pam!auto=...' \\
    python examples/list_nodes.py
"""

from __future__ import annotations

import os

from pve_client.configuration import Configuration
from pve_client.pve import Pve


def main() -> None:
    config = Configuration(host=f"{os.environ.get('PVE_HOST', 'https://localhost:8006')}/api2/json")
    # OpenAPI auth-scheme name (NOT the `Authorization` header name).
    # The full `PVEAPIToken=…` string goes in here; no api_key_prefix.
    config.api_key["PVEApiToken"] = os.environ.get("PVE_TOKEN", "")

    pve = Pve(config)
    response = pve.nodes.get_nodes()
    nodes = getattr(response, "data", None) or []
    print(f"Found {len(nodes)} node(s):")
    for node in nodes:
        print(
            f"  - {getattr(node, 'node', None)} "
            f"(status={getattr(node, 'status', None)}, "
            f"cpu={getattr(node, 'cpu', None)}, "
            f"mem={getattr(node, 'mem', None)}/{getattr(node, 'maxmem', None)})",
        )


if __name__ == "__main__":
    main()
