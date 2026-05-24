"""SC-40 … SC-42 — error-path correctness."""
from __future__ import annotations

import pytest

from clientapi_pve import Configuration, Pve
from clientapi_pve.exceptions import ApiException
from clientapi_pve.models.access_users_create_user_request import (
    AccessUsersCreateUserRequest,
)
from clientapi_pve.models.access_users_generate_token_request import (
    AccessUsersGenerateTokenRequest,
)
from e2e.helpers.credentials import Credentials


def test_unknown_vmid_returns_error(pve: Pve, node: str) -> None:
    """SC-40 — querying a nonexistent vmid raises a structured ApiException (4xx/5xx)."""
    with pytest.raises(ApiException) as excinfo:
        pve.qemu.vm_status(node=node, vmid=999999)
    # PVE returns 500 with a descriptive body; some endpoints use 404. Accept either.
    assert excinfo.value.status in (404, 500), excinfo.value


def test_invalid_password_length_rejected(pve: Pve) -> None:
    """SC-41 — invalid input (password too short) is caught client-side or server-side.

    The pydantic schema enforces `min_length=8`, so SC-41 is satisfied by the
    SDK rejecting the call before it leaves the process. We assert *some*
    validation error fires.
    """
    with pytest.raises(Exception) as excinfo:
        pve.accessUsers.create_user(
            AccessUsersCreateUserRequest(userid="e2e-tooshort@pve", password="abc")
        )
    # pydantic ValidationError or ApiException (if the schema let it through) both count.
    assert excinfo.type.__name__ in {"ValidationError", "BadRequestException", "ApiException"}, excinfo.value


def test_privsep_token_without_acl_is_forbidden(pve: Pve, creds: Credentials) -> None:
    """SC-42 — token with privsep=1 and no ACL receives 403 on writes."""
    user_id = "e2e-noacl@pve"
    pve.accessUsers.create_user(
        AccessUsersCreateUserRequest(
            userid=user_id, password="long-enough-password-1234"
        )
    )
    try:
        token_response = pve.accessUsers.generate_token(
            userid=user_id,
            tokenid="noacl",
            access_users_generate_token_request=AccessUsersGenerateTokenRequest(privsep=1),
        )
        full_tokenid = token_response.data.full_tokenid
        value = token_response.data.value
        header_value = f"PVEAPIToken={full_tokenid}={value}"

        cfg = Configuration(host=f"{creds.url}/api2/json")
        cfg.verify_ssl = not creds.insecure
        cfg.api_key["PVEApiToken"] = header_value
        client = Pve(cfg)

        with pytest.raises(ApiException) as excinfo:
            client.accessUsers.create_user(
                AccessUsersCreateUserRequest(
                    userid="e2e-blocked2@pve",
                    password="long-enough-password-1234",
                )
            )
        assert excinfo.value.status in (401, 403), excinfo.value
    finally:
        try:
            pve.accessUsers.delete_user(userid=user_id)
        except ApiException:
            pass
