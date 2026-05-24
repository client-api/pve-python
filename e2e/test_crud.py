"""SC-30 … SC-34 — CRUD round-trips against real PVE entities."""
from __future__ import annotations

import os
import pytest

from clientapi_pve import Pve
from clientapi_pve.exceptions import ApiException
from clientapi_pve.models.access_acl_update_acl_request import AccessAclUpdateAclRequest
from clientapi_pve.models.access_users_create_user_request import (
    AccessUsersCreateUserRequest,
)
from clientapi_pve.models.pve_storage_dir_config import PveStorageDirConfig
from clientapi_pve.models.storage_create_storage_request import (
    StorageCreateStorageRequest,
)


def test_users_list_contains_root(pve: Pve) -> None:
    """SC-30 — root@pam is always present."""
    users = pve.accessUsers.get_users().data or []
    ids = {getattr(u, "userid", None) for u in users}
    assert "root@pam" in ids, ids


def test_user_crud_roundtrip(pve: Pve) -> None:
    """SC-31 — create → list → delete cycle for a transient e2e user."""
    user_id = "e2e-user-01@pve"
    pve.accessUsers.create_user(
        AccessUsersCreateUserRequest(
            userid=user_id,
            password="long-enough-password-1234",
            comment="SC-31 transient",
        )
    )
    try:
        users = pve.accessUsers.get_users().data or []
        assert any(getattr(u, "userid", None) == user_id for u in users)
    finally:
        pve.accessUsers.delete_user(userid=user_id)

    users_after = pve.accessUsers.get_users().data or []
    assert all(getattr(u, "userid", None) != user_id for u in users_after)


def test_storage_crud_dir_type(pve: Pve, tmp_path) -> None:
    """SC-32 — directory-backed storage create / list / delete."""
    storage_id = "e2e-store-01"
    # Use a tmp path on the container — container has write access to /var/tmp.
    target = "/var/tmp/e2e-store-01"
    os.makedirs(target, exist_ok=True)
    req = StorageCreateStorageRequest(
        PveStorageDirConfig(
            storage=storage_id,
            path=target,
            content="iso",
            type="dir",
        )
    )
    pve.storage.create_storage(req)
    try:
        names = {getattr(s, "storage", None) for s in (pve.storage.get_storage().data or [])}
        assert storage_id in names, names
    finally:
        pve.storage.delete_storage(storage=storage_id)


def test_acl_crud_grant_revoke(pve: Pve) -> None:
    """SC-33 — grant an ACL, observe it, revoke it."""
    user_id = "e2e-acl-user@pve"
    pve.accessUsers.create_user(
        AccessUsersCreateUserRequest(
            userid=user_id,
            password="long-enough-password-1234",
        )
    )
    try:
        pve.accessAcl.update_acl(
            AccessAclUpdateAclRequest(path="/", roles="PVEAuditor", users=user_id)
        )
        entries = pve.accessAcl.read_acl().data or []
        matched = [
            e
            for e in entries
            if getattr(e, "ugid", None) == user_id and getattr(e, "roleid", None) == "PVEAuditor"
        ]
        assert matched, f"ACL not present after grant: {entries!r}"

        # Revoke.
        pve.accessAcl.update_acl(
            AccessAclUpdateAclRequest(
                path="/", roles="PVEAuditor", users=user_id, delete=1
            )
        )
        entries_after = pve.accessAcl.read_acl().data or []
        remaining = [
            e
            for e in entries_after
            if getattr(e, "ugid", None) == user_id and getattr(e, "roleid", None) == "PVEAuditor"
        ]
        assert not remaining, f"ACL still present after revoke: {entries_after!r}"
    finally:
        try:
            pve.accessUsers.delete_user(userid=user_id)
        except ApiException:
            pass


def test_users_list_is_iterable(pve: Pve) -> None:
    """SC-34 — paginated-walk shape.

    The /access/users endpoint doesn't paginate, so this is a degenerate walk:
    the list materializes in one call and the suite asserts it's iterable +
    every entry has a `userid` field. When PVE introduces pagination upstream,
    swap this for a true cursor walk.
    """
    response = pve.accessUsers.get_users()
    users = response.data or []
    assert isinstance(users, list)
    for u in users:
        assert getattr(u, "userid", None), u
