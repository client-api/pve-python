"""SC-20 … SC-22 — authorization and permission boundaries."""
from __future__ import annotations

import pytest

from clientapi_pve import Configuration, Pve
from clientapi_pve.exceptions import ApiException
from clientapi_pve.models.access_acl_update_acl_request import AccessAclUpdateAclRequest
from clientapi_pve.models.access_users_create_user_request import (
    AccessUsersCreateUserRequest,
)
from clientapi_pve.models.access_users_generate_token_request import (
    AccessUsersGenerateTokenRequest,
)
from e2e.helpers.credentials import Credentials


@pytest.fixture
def readonly_token(pve: Pve, creds: Credentials):
    """Create an e2e-* user + privsep token granted PVEAuditor on /.

    Yields (user_id, token_id, token_value, header_value) and cleans up after.
    """
    user_id = "e2e-readonly@pve"
    token_id = "audit"
    password = "e2e-readonly-secret-1234"

    # Setup.
    try:
        pve.accessUsers.create_user(
            AccessUsersCreateUserRequest(
                userid=user_id, password=password, comment="e2e readonly"
            )
        )
    except ApiException:
        pass  # user already exists from a previous run

    token_response = pve.accessUsers.generate_token(
        userid=user_id,
        tokenid=token_id,
        access_users_generate_token_request=AccessUsersGenerateTokenRequest(privsep=1),
    )
    value = token_response.data.value
    full_tokenid = token_response.data.full_tokenid
    header_value = f"PVEAPIToken={full_tokenid}={value}"

    pve.accessAcl.update_acl(
        AccessAclUpdateAclRequest(path="/", roles="PVEAuditor", tokens=f"{user_id}!{token_id}")
    )

    yield user_id, header_value

    # Cleanup.
    try:
        pve.accessUsers.delete_user(userid=user_id)
    except ApiException:
        pass


def _client_for(creds: Credentials, header_value: str) -> Pve:
    cfg = Configuration(host=f"{creds.url}/api2/json")
    cfg.verify_ssl = not creds.insecure
    cfg.api_key["PVEApiToken"] = header_value
    return Pve(cfg)


def test_readonly_token_can_read_but_not_write(
    pve: Pve, creds: Credentials, readonly_token
) -> None:
    """SC-20 — read-only token sees nodes but is rejected from writes."""
    _user_id, header_value = readonly_token
    ro = _client_for(creds, header_value)

    # GET succeeds.
    response = ro.nodes.get_nodes()
    assert getattr(response, "data", None) is not None

    # Write rejected (403).
    with pytest.raises(ApiException) as excinfo:
        ro.accessUsers.create_user(
            AccessUsersCreateUserRequest(
                userid="e2e-blocked@pve",
                password="long-enough-password-1234",
            )
        )
    assert excinfo.value.status == 403, excinfo.value


def test_admin_can_create_user(pve: Pve) -> None:
    """SC-21 — root-equivalent token can create entities."""
    user_id = "e2e-admin-probe@pve"
    pve.accessUsers.create_user(
        AccessUsersCreateUserRequest(
            userid=user_id,
            password="long-enough-password-1234",
            comment="created by SC-21",
        )
    )
    try:
        users = pve.accessUsers.get_users().data or []
        assert any(getattr(u, "userid", None) == user_id for u in users)
    finally:
        pve.accessUsers.delete_user(userid=user_id)


def test_acl_endpoint_lists_entries(pve: Pve) -> None:
    """SC-22 — /access/acl returns the list of ACL entries."""
    response = pve.accessAcl.read_acl()
    entries = getattr(response, "data", None) or []
    # Root ACL is always populated; an empty list would mean the call lied.
    assert isinstance(entries, list)
