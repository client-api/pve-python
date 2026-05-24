"""SC-50 … SC-52 — type-correctness checks on the generated SDK."""
from __future__ import annotations

import inspect
import typing

import pytest

from clientapi_pve import Pve
from clientapi_pve.models.nodes_storage_read_status_response_data import (
    NodesStorageReadStatusResponseData,
)
from clientapi_pve.models.pve_storage_dir_config import PveStorageDirConfig
from clientapi_pve.models.storage_create_storage_request import (
    StorageCreateStorageRequest,
)


def test_int64_fields_are_python_int(pve: Pve, node: str) -> None:
    """SC-50 — bytes counters round-trip as `int`, not `float`.

    Python's `int` is arbitrary-precision, so values above 2^53 survive the
    serialization round-trip. We assert both the type and that the storage
    `total`/`avail`/`used` fields deserialize as actual ints from the live API.
    """
    # 1. Static check: the model annotates these fields as int, not float.
    hints = typing.get_type_hints(NodesStorageReadStatusResponseData)
    for field in ("avail", "total", "used"):
        annotation = hints[field]
        # Optional[StrictInt] resolves to Union[StrictInt, None]; check that int is in the Union.
        members = typing.get_args(annotation) or (annotation,)
        assert any(m is int or getattr(m, "__name__", "") == "StrictInt" for m in members), (
            f"{field} annotation is {annotation!r} — must include int"
        )

    # 2. Live check: query a real storage and verify the runtime types.
    storages = pve.storage.get_storage().data or []
    storage_id = next((getattr(s, "storage", None) for s in storages), None)
    assert storage_id, "no storages configured on test node"
    status = pve.nodesStorage.read_status(node=node, storage=storage_id).data
    for field in ("avail", "total", "used"):
        value = getattr(status, field, None)
        if value is not None:
            assert isinstance(value, int) and not isinstance(value, bool), (
                f"{field} = {value!r} (type {type(value).__name__})"
            )


def test_nullable_fields_deserialize_to_none(pve: Pve) -> None:
    """SC-51 — Optional fields that the server omits arrive as `None`, not "" or 0."""
    # `comment` is Optional[str] on user records; root@pam typically has no comment set.
    users = pve.accessUsers.get_users().data or []
    assert users, "expected at least one user"
    omitted = [u for u in users if getattr(u, "comment", None) is None]
    # At least one user (anywhere in the system) must legitimately have a missing comment.
    assert omitted, "no user had a None comment — model may be silently coercing to empty string"


def test_oneof_storage_discriminator_roundtrip() -> None:
    """SC-52 — oneOf discriminator round-trips dict → typed instance → dict."""
    cfg = PveStorageDirConfig(
        storage="e2e-oneof",
        path="/var/tmp/e2e-oneof",
        type="dir",
        content="iso",
    )
    wrapped = StorageCreateStorageRequest(cfg)
    payload = wrapped.to_dict()
    assert payload.get("type") == "dir", payload

    parsed = StorageCreateStorageRequest.from_dict(payload)
    assert isinstance(parsed.actual_instance, PveStorageDirConfig), parsed.actual_instance
    assert parsed.actual_instance.storage == "e2e-oneof"
    assert parsed.actual_instance.path == "/var/tmp/e2e-oneof"
