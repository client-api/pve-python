"""SC-10 … SC-14 — authentication paths."""
from __future__ import annotations

import pytest

from clientapi_pve import Configuration, Pve
from clientapi_pve.exceptions import ApiException, UnauthorizedException
from clientapi_pve.models.access_ticket_create_ticket_request import (
    AccessTicketCreateTicketRequest,
)
from e2e.helpers.clients import issue_ticket, ticket_client, token_client
from e2e.helpers.credentials import Credentials


def test_ticket_login_returns_ticket_and_csrf(creds: Credentials) -> None:
    """SC-10 — POST /access/ticket with valid creds yields ticket + CSRFPreventionToken."""
    anon = Configuration(host=f"{creds.url}/api2/json")
    anon.verify_ssl = not creds.insecure
    pve = Pve(anon)

    response = pve.accessTicket.create_ticket(
        AccessTicketCreateTicketRequest(username=creds.user, password=creds.password)
    )
    data = response.data
    assert data is not None
    assert data.ticket, "ticket missing"
    assert data.csrf_prevention_token, "CSRFPreventionToken missing"


def test_invalid_password_raises_401(creds: Credentials) -> None:
    """SC-11 — wrong password ⇒ 401 (UnauthorizedException) from the SDK."""
    with pytest.raises(ApiException) as excinfo:
        issue_ticket(creds, password="definitely-not-the-password")
    assert excinfo.value.status == 401, excinfo.value


def test_token_auth_lists_nodes(creds: Credentials) -> None:
    """SC-12 — API-token auth roundtrips against a GET that requires permissions."""
    pve = token_client(creds)
    response = pve.nodes.get_nodes()
    nodes = getattr(response, "data", None) or []
    assert len(nodes) >= 1


def test_malformed_token_raises_401(creds: Credentials) -> None:
    """SC-13 — bogus token UUID ⇒ 401, never silently succeeds."""
    cfg = Configuration(host=f"{creds.url}/api2/json")
    cfg.verify_ssl = not creds.insecure
    cfg.api_key["PVEApiToken"] = "PVEAPIToken=root@pam!test=00000000-0000-0000-0000-000000000000"
    pve = Pve(cfg)
    with pytest.raises(ApiException) as excinfo:
        pve.nodes.get_nodes()
    assert excinfo.value.status == 401, excinfo.value


def test_ticket_write_without_csrf_is_rejected(creds: Credentials) -> None:
    """SC-14 — ticket auth writes require CSRFPreventionToken header.

    Reproduces by issuing a real ticket, building a client without the
    CSRFPreventionToken header, and attempting a write — expect 401.
    GETs still succeed (CSRF is only required for state-changing methods),
    so we verify both halves of the contract here.
    """
    anon = Configuration(host=f"{creds.url}/api2/json")
    anon.verify_ssl = not creds.insecure
    bootstrap = Pve(anon)
    ticket_response = bootstrap.accessTicket.create_ticket(
        AccessTicketCreateTicketRequest(username=creds.user, password=creds.password)
    )
    ticket = ticket_response.data.ticket
    assert ticket

    no_csrf = ticket_client(creds, ticket=ticket, csrf=None)

    # GETs work without CSRF.
    response = no_csrf.nodes.get_nodes()
    assert getattr(response, "data", None) is not None

    # Writes are rejected. Create an e2e user is a cheap state-changing call.
    from clientapi_pve.models.access_users_create_user_request import (
        AccessUsersCreateUserRequest,
    )

    with pytest.raises(ApiException) as excinfo:
        no_csrf.accessUsers.create_user(
            AccessUsersCreateUserRequest(
                userid="e2e-csrf-probe@pve",
                password="not-a-real-secret-1234",
                comment="should fail without CSRF",
            )
        )
    assert excinfo.value.status == 401, excinfo.value
