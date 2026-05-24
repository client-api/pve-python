"""Polling helper for asynchronous PVE operations.

PVE returns task UPIDs for long-running calls (VM start, storage create, …).
The caller polls until a predicate is satisfied or the timeout elapses.
"""
from __future__ import annotations

import time
from typing import Callable, Optional, TypeVar

T = TypeVar("T")


class WaitTimeout(RuntimeError):
    """Raised when wait_until exhausts its timeout."""


def wait_until(
    predicate: Callable[[], Optional[T]],
    *,
    timeout_s: float = 60.0,
    interval_s: float = 1.0,
    label: str = "predicate",
) -> T:
    deadline = time.monotonic() + timeout_s
    last_exc: Optional[BaseException] = None
    while time.monotonic() < deadline:
        try:
            result = predicate()
        except Exception as exc:  # transient API errors are OK while polling
            last_exc = exc
            result = None
        if result is not None and result is not False:
            return result  # type: ignore[return-value]
        time.sleep(interval_s)
    msg = f"timed out after {timeout_s}s waiting for {label}"
    if last_exc is not None:
        msg += f" (last error: {last_exc!r})"
    raise WaitTimeout(msg)
