"""Client factories for the two auth modes PVE supports.

Token clients use the Authorization header and don't need a CSRF dance.
Ticket clients require a paired ticket cookie + CSRFPreventionToken header
for non-GET requests; SDK already wires both when both api_key entries are set.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from clientapi_pve import Configuration, Pve

if TYPE_CHECKING:
    from e2e.helpers.credentials import Credentials


def token_client(creds: "Credentials") -> Pve:
    cfg = Configuration(host=f"{creds.url}/api2/json")
    cfg.verify_ssl = not creds.insecure
    cfg.api_key["PVEApiToken"] = creds.token_header_value
    return Pve(cfg)


def ticket_client(
    creds: "Credentials",
    *,
    ticket: str,
    csrf: str | None = None,
) -> Pve:
    """Build a Pve client authenticated with a ticket cookie and (optionally) a CSRF header.

    Omit `csrf` to deliberately simulate the SC-14 "missing CSRF header on write" case.
    """
    cfg = Configuration(host=f"{creds.url}/api2/json")
    cfg.verify_ssl = not creds.insecure
    cfg.api_key["PVEAuthCookie"] = ticket
    if csrf is not None:
        cfg.api_key["CSRFPreventionToken"] = csrf
    return Pve(cfg)


def issue_ticket(creds: "Credentials", *, password: str | None = None) -> Pve:
    """Log in with username+password and return a Pve client wired for ticket auth.

    Raises ApiException(401) when the password is wrong (SC-11).
    """
    from clientapi_pve.models.access_ticket_create_ticket_request import (
        AccessTicketCreateTicketRequest,
    )

    anon = Configuration(host=f"{creds.url}/api2/json")
    anon.verify_ssl = not creds.insecure
    bootstrap = Pve(anon)

    response = bootstrap.accessTicket.create_ticket(
        AccessTicketCreateTicketRequest(
            username=creds.user,
            password=password if password is not None else creds.password,
        )
    )
    data = response.data
    if data is None or not data.ticket:
        raise RuntimeError(f"ticket login returned no ticket: {response!r}")
    return ticket_client(
        creds,
        ticket=data.ticket,
        csrf=data.csrf_prevention_token,
    )
