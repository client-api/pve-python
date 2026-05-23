# clientapi_pve

Python SDK for the Proxmox Virtual Environment (PVE) API. Generated
from the upstream `apidoc.js` via [openapi-generator-cli][gen] with
custom Mustache template overrides.

> **Not an official Proxmox project.** Community SDK derived from the
> upstream `apidoc.js`. Always verify against
> <https://pve.proxmox.com/pve-docs/api-viewer/>.

Requires Python ≥ 3.9.

## Install

```bash
pip install clientapi_pve
```

Or for development:

```bash
pip install -r requirements.txt
```

## Usage

```python
from clientapi_pve import Configuration, Pve

cfg = Configuration(
    host='https://pve1.example.com:8006/api2/json',
    api_key={'Authorization': 'PVEAPIToken=user@realm!tokenid=uuid-secret'},
)
pve = Pve(configuration=cfg)

# Per-tag properties are lazily instantiated and share the same ApiClient.
status = pve.qemu.qemu_vm_status(node='pve1', vmid=100)
nodes = pve.nodes.nodes_index()
```

The unified `Pve` class wraps each per-tag API class (`QemuApi`,
`LxcApi`, `ClusterApi`, `NodesApi`, …) so consumers don't need to
instantiate them individually.

## Compound configs

PVE encodes many fields as CLI-style shorthand strings
(`net0=virtio,bridge=vmbr0,firewall=1`). Round-trip helpers are
emitted for every compound config schema:

```python
from clientapi_pve.models import PveQemuNetConfig

cfg = PveQemuNetConfig(model='virtio', bridge='vmbr0', firewall=1)
shorthand = cfg.to_shorthand()  # → 'virtio,bridge=vmbr0,firewall=1'

parsed = PveQemuNetConfig.from_shorthand(shorthand)
```

## Indexed families

Numbered properties (`net0..net31`, `mp0..mp255`, …) are exposed on
every model as a single collapsed `nets` / `mps` / … field:

```python
req = QemuCreateVmRequest(
    nets={
        0: 'virtio,bridge=vmbr0',
        3: 'e1000,bridge=vmbr1',
    },
)
# Wire format: { 'net0': 'virtio,bridge=vmbr0', 'net3': 'e1000,bridge=vmbr1' }
```

## License

Apache 2.0 — see [LICENSE](./LICENSE).

[gen]: https://openapi-generator.tech
