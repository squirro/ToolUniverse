"""Records whether a tool's HTTP calls happened, so an empty result can be told apart from
an unanswered one.

The seam is ``HTTPAdapter.send`` rather than ``Session.request``: every session funnels
through it, and it receives a URL already resolved with its query string. The scope is
thread-local, so HTTP issued from a thread the tool spawns itself is recorded only if that
thread opens its own scope.
"""

from __future__ import annotations

import functools
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator

import requests.adapters

__all__ = [
    "CallRecord",
    "current_records",
    "install",
    "install_invocation_scope",
    "last_invocation_records",
    "recording",
]


@dataclass(frozen=True)
class CallRecord:
    """One HTTP attempt made inside a recording scope.

    ``reached`` says whether the source answered at all. A 404 or a 500 is ``reached=True``,
    so an empty result beside it is a real "no data"; a refused connection, DNS failure or
    timeout is ``reached=False``, and an empty result beside that is evidence of nothing.
    """

    url: str
    status_code: int | None
    reached: bool
    error: str | None
    # Whether the URL identifies the query: a GET carries its parameters, a POST does not.
    method: str = "GET"


_local = threading.local()


def _stack() -> list[list[CallRecord]]:
    stack = getattr(_local, "stack", None)
    if stack is None:
        stack = []
        _local.stack = stack
    return stack


def _append(record: CallRecord) -> None:
    """Report to every open scope, innermost last.

    An inner invocation's traffic is also the outer invocation's: if the inner call's source
    was unreachable, the outer result is just as compromised.
    """
    for records in _stack():
        records.append(record)


@contextmanager
def recording() -> Iterator[list[CallRecord]]:
    """Collect the HTTP calls made in this block, on this thread."""
    records: list[CallRecord] = []
    stack = _stack()
    stack.append(records)
    try:
        yield records
    finally:
        stack.pop()


def current_records() -> tuple[CallRecord, ...]:
    """The innermost open scope's records; empty when there is no open scope."""
    stack = _stack()
    return tuple(stack[-1]) if stack else ()


def _patched_send(self, request, **kwargs):
    if not _stack():
        # Outside any invocation: stay out of the way.
        return _patched_send.__wrapped__(self, request, **kwargs)

    try:
        response = _patched_send.__wrapped__(self, request, **kwargs)
    except Exception as exc:
        # No response object exists, so the URL must come off the request.
        _append(
            CallRecord(
                url=request.url,
                status_code=None,
                reached=False,
                error=repr(exc),
                method=(request.method or "GET").upper(),
            )
        )
        raise

    _append(
        CallRecord(
            url=request.url,
            status_code=response.status_code,
            reached=True,
            error=None,
            method=(request.method or "GET").upper(),
        )
    )
    return response


_patched_send._sr_http_record = True


def install() -> None:
    """Patch ``HTTPAdapter.send`` once per process. Safe to call repeatedly."""
    current = requests.adapters.HTTPAdapter.send
    if getattr(current, "_sr_http_record", False):
        return
    _patched_send.__wrapped__ = current
    requests.adapters.HTTPAdapter.send = _patched_send


def last_invocation_records() -> tuple[CallRecord, ...]:
    """What the most recent completed invocation on this thread recorded."""
    return getattr(_local, "last", ())


def install_invocation_scope(cls) -> None:
    """Make one ``run_one_function`` call one recording scope. Safe to call repeatedly.

    Wraps the class from outside rather than editing ``execute_function.py``, which
    re-syncs from upstream.
    """
    original = cls.run_one_function
    if getattr(original, "_sr_http_record", False):
        return

    install()

    @functools.wraps(original)
    def wrapper(self, *args, **kwargs):
        with recording() as records:
            try:
                return original(self, *args, **kwargs)
            finally:
                # Snapshot in `finally` so a raising tool still leaves its evidence.
                _local.last = tuple(records)

    wrapper._sr_http_record = True
    cls.run_one_function = wrapper
