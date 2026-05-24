# E2E tests for `clientapi_pve`

Live-server pytest suite. Runs against a real Proxmox VE instance — by default the
`ghcr.io/client-api/proxmox-docker/pve-test` container, either spun up locally
via `docker compose up -d` or in CI via
[`client-api/proxmox-docker-action@v1`](https://github.com/client-api/proxmox-docker-action).

## Quick start (local)

```bash
docker compose up -d
sleep 20  # wait for healthcheck

export PROXMOX_URL=https://localhost:8006
export PROXMOX_USER=root@pam
export PROXMOX_PASSWORD=proxmox123
# Read the joined token header from the container:
export PROXMOX_TOKEN_HEADER_VALUE="$(docker exec pve-test cat /run/credentials.json | jq -r .token_header_value)"
export PROXMOX_INSECURE=1
export PROXMOX_KVM_AVAILABLE=$(test -e /dev/kvm && echo true || echo false)
export PROXMOX_CGROUPV2_AVAILABLE=$(test -d /sys/fs/cgroup/cgroup.controllers && echo true || echo false)

pip install -e .[test]
pytest e2e/ -v
```

## Environment contract

| Var | Source | Notes |
|---|---|---|
| `PROXMOX_URL` | `proxmox-docker-action` | e.g. `https://localhost:8006` (no `/api2/json`) |
| `PROXMOX_USER` | action | typically `root@pam` |
| `PROXMOX_PASSWORD` | action | password ticket auth (SC-10..11, SC-14) |
| `PROXMOX_TOKEN_HEADER_VALUE` | action | whole `PVEAPIToken=root@pam!test=<uuid>` string |
| `PROXMOX_TOKEN_VALUE` | action | UUID half only (rarely needed) |
| `PROXMOX_INSECURE` | local | set to `1` to skip TLS verification (self-signed dev cert) |
| `PROXMOX_KVM_AVAILABLE` | action output | `true`/`false`; gates SC-60, SC-62 |
| `PROXMOX_CGROUPV2_AVAILABLE` | action output | `true`/`false`; gates SC-61 |
| `PROXMOX_NO_NETWORK` | manual | `1` to skip network-egress tests (SC-35, SC-62) |

> Never reconstruct `PROXMOX_TOKEN_HEADER_VALUE` by hand — the Perl family
> (PVE, PMG) joins with `=`, the Rust family (PBS, PDM) with `:`. The
> container pre-joins it correctly.

## Capability gates

Tests that need kernel features import the marker symbol, never an inline env check:

```python
from e2e.conftest import requires_kvm

@requires_kvm
def test_vm_lifecycle(pve, node):
    ...
```

When the gate is closed the test is **skipped**, not failed.

## Fixture convention

All entities created during the suite are named `e2e-…` (users, storages,
ACLs) and live in the VM-ID range `101..199`. `cleanup_e2e()` runs at session
start and end. VM 100 (`tiny-test`) and CT 200 (`tiny-ct`) are pre-seeded by
the container and are never touched.

## Scenario index (SC-01 … SC-62)

| File | Scenarios |
|---|---|
| `test_version.py` | SC-01 |
| `test_auth.py` | SC-10 … SC-14 |
| `test_authz.py` | SC-20 … SC-22 |
| `test_crud.py` | SC-30 … SC-34 |
| `test_iso_upload.py` | SC-35 |
| `test_errors.py` | SC-40 … SC-42 |
| `test_types.py` | SC-50 … SC-52 |
| `test_vm_lifecycle.py` | SC-60 (kvm-gated) |
| `test_ct_lifecycle.py` | SC-61 (cgroupv2-gated) |
| `test_vm_cdrom.py` | SC-62 (kvm+network-gated) |

## Known SDK gaps surfaced by this suite

These are real generator gaps the live tests uncovered; each has a focused
workaround in `e2e/helpers/` so the rest of the suite stays clean, and the
SC-NN that exercises it stays in the suite so it will auto-promote when the
upstream template is fixed.

1. **Ticket cookie format.** `Configuration.auth_settings` emits
   `Cookie: <ticket>` for `PVEAuthCookie`. PVE expects
   `Cookie: PVEAuthCookie=<ticket>`. Workaround in
   `e2e/helpers/clients.py::ticket_client` pre-joins the prefix.
2. **`NodesStorageApi.upload` carries no file body.** The OpenAPI spec models
   the upload field as `tmpfilename` (a server-side path reference), so the
   generated SDK can only send metadata. Workaround: raw multipart POST in
   `e2e/helpers/upload.py::upload_iso`.
3. **`NodesStorageDiridxResponse.data` types inner items as
   `AccessGetAccessResponseDataInner`.** The generator picked the wrong inner
   model, so `volid` deserializes as empty. Workaround:
   `e2e/helpers/upload.py::list_storage_content` parses the raw JSON.
4. **`QemuCreateVmRequest.to_dict()` references undefined indexed-family
   fields** (`ide0`, `net0`, …). The model exposes collapsed `ides`/`nets`
   maps but the serializer reaches for individual numbered properties.
   SC-62 is marked `xfail` until the template is fixed.
5. **POST endpoints with optional request models drop the body entirely.**
   `vm_start` / `vm_stop` (etc.) send no body when no request model is
   supplied; PVE returns 500 "malformed JSON". Tests always pass an empty
   request model (`QemuVmStartRequest()`) instead of relying on the default.

## Downstream cells

`pbs-py`, `pmg-py`, `pdm-py` follow the same shape — copy `e2e/`, the
pyproject test group, `docker-compose.yml`, and `.github/workflows/e2e.yml`,
then swap product-specific bits (image tag, port, token separator). PMG skips
SC-12/13 (no API tokens). PDM uses `/api2/extjs` in raw HTTP paths.
