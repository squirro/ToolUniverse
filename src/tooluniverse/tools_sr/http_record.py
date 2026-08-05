"""Records whether a tool's HTTP calls actually happened (DSR-658).

Two registry-wide defects need the same fact: an empty result means nothing until you know
whether the source answered. 245 broad exception handlers across 110 modules return an
empty value without surfacing the failure, and 87.3% of tools declare no ``status`` field
to report one in -- which is how a dead network read as a biological negative (DSR-629).

Those 110 modules re-sync from ``mims-harvard:main``, so editing them buys a permanent
merge tax and still does nothing for tools upstream has not written yet. ADR-0014 chose
central interception instead, and this is that interception.

**Why the adapter and not ``Session.request``.** The PRD and ADR-0014 both name
``Session.request``. Measured, that is the wrong seam: 74 modules each construct their own
``requests.Session()`` across ~936 call-sites, so session-level patching is easy to get
partially wrong. Every one of those funnels through ``HTTPAdapter.send``, which is also
handed a ``PreparedRequest`` whose ``url`` is already fully resolved with the query string
attached -- exactly what DSR-667 needs to stamp, and what ``Session.request`` would force
us to re-encode by hand.

This module only observes. Turning a record into a status on the result is DSR-666.

**Known boundary:** the scope is thread-local, so HTTP issued from a thread the tool spawns
itself is recorded only if that thread opens its own scope. Calls made inline -- the
overwhelming majority -- are covered.
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

    ``reached`` answers the only question the swallow bug loses: did we get an answer from
    the source at all? A 404 or a 500 is ``reached=True`` -- the source spoke, and an empty
    result alongside it is a real "no data". A refused connection, DNS failure or timeout
    is ``reached=False``, and an empty result alongside *that* is not evidence of anything.
    """

    url: str
    status_code: int | None
    reached: bool
    error: str | None


_local = threading.local()


def _stack() -> list[list[CallRecord]]:
    stack = getattr(_local, "stack", None)
    if stack is None:
        stack = []
        _local.stack = stack
    return stack


def _append(record: CallRecord) -> None:
    """Report to every open scope, innermost last.

    A compose tool invokes other tools, so an inner invocation's traffic is also the outer
    invocation's traffic: if the inner call's source was unreachable, the outer result is
    just as compromised. Recording to all open scopes keeps that visible instead of hiding
    it one level down.
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
        # Outside any invocation. Stay entirely out of the way.
        return _patched_send.__wrapped__(self, request, **kwargs)

    try:
        response = _patched_send.__wrapped__(self, request, **kwargs)
    except Exception as exc:
        # No response object exists, so the URL must come off the request. This is the
        # case the swallowing handlers erase.
        _append(
            CallRecord(
                url=request.url, status_code=None, reached=False, error=repr(exc)
            )
        )
        raise

    _append(
        CallRecord(
            url=request.url,
            status_code=response.status_code,
            reached=True,
            error=None,
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
    """What the most recent completed invocation on this thread recorded.

    Read after the invocation returns, which is where DSR-666 decides whether an empty
    result means ``no_data`` or ``source_unreachable``.
    """
    return getattr(_local, "last", ())


def install_invocation_scope(cls) -> None:
    """Make one ``run_one_function`` call one recording scope. Safe to call repeatedly.

    Wrapping the class from outside rather than editing ``execute_function.py`` keeps the
    fix off a file that re-syncs from upstream -- the same reasoning ADR-0014 applies to
    the 110 swallowing modules, applied to the seam itself. Wrapping also avoids
    re-indenting a 200-line method body around a ``with``, which would be a merge conflict
    on every future sync.
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
