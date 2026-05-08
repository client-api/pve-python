"""Example: connect to a Proxmox host with a self-signed certificate.

The PVE web UI ships with a self-signed cert by default. Production
setups should use a real CA-signed cert (Let's Encrypt via the Proxmox
UI), but home-lab and dev setups commonly need to opt out of cert
verification.

**Security note:** disabling verification is vulnerable to MITM. Use
only on trusted networks, or pass a pinned CA bundle via
``Configuration.ssl_ca_cert`` instead.

Run with:
    PVE_HOST=https://pve.example.com:8006 \\
    PVE_TOKEN='PVEAPIToken=root@pam!auto=...' \\
    PVE_NODE=orca PVE_VMID=100 \\
    python examples/insecure_tls.py
"""

from __future__ import annotations

import os
import sys
import time

from pve_client.configuration import Configuration
from pve_client.pve import Pve
from pve_client.websocket import QemuTarget


def main() -> None:
    host = os.environ.get("PVE_HOST", "https://localhost:8006")
    token = os.environ.get("PVE_TOKEN", "")  # full `PVEAPIToken=root@pam!name=secret`

    config = Configuration(host=f"{host}/api2/json")
    # `PVEApiToken` is the OpenAPI auth-scheme name the REST client
    # keys by — not the `Authorization` *header* name. Put the full
    # `PVEAPIToken=…` string in here (no `api_key_prefix`) because PVE's
    # header has no space between the prefix and the token.
    config.api_key["PVEApiToken"] = token
    # ── single switch: REST (urllib3) AND WebSocket (websocket-client)
    #    both honor this. The WS adapter passes
    #    `sslopt={cert_reqs: CERT_NONE, check_hostname: False}` when set.
    config.verify_ssl = False

    # Silence the urllib3 "InsecureRequestWarning" that otherwise
    # appears on every request.
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    pve = Pve(config)
    nodes = pve.nodes.get_nodes().data or []
    print(f"Connected (insecure TLS): {len(nodes)} node(s)")
    for n in nodes:
        d = n.to_dict() if hasattr(n, "to_dict") else n
        print(f"  - {d.get('node')} (status={d.get('status')})")

    if not (os.environ.get("PVE_NODE") and os.environ.get("PVE_VMID")):
        print("(skip terminal: set PVE_NODE and PVE_VMID to test the WebSocket leg)")
        return

    target = QemuTarget(
        node=os.environ["PVE_NODE"],
        vmid=int(os.environ["PVE_VMID"]),
    )
    print(f"Opening terminal to {target.node}/qemu/{target.vmid}...")
    session = pve.connect_terminal(target, on_message=lambda text: sys.stdout.write(text))
    time.sleep(0.7)
    session.send("uname -a\n")
    time.sleep(3)
    session.close()


if __name__ == "__main__":
    main()
