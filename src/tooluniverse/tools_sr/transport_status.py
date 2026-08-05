"""Says which kind of empty an empty result is (DSR-666 / DSR-672).

DSR-629: a dead network read as a biological negative. The tool returned an empty payload,
the agent reported "no association found", and nothing in the result said the source had
never answered. 1,957 of 2,241 tools declare no ``status`` field at all, so there is
nowhere for that answer to live today -- which is why the annotation here is *additive*.

**The rule that makes this safe:** absence of call records is not evidence of
unreachability. Only a record of a *failed* call is.

That single line is why DSR-672 needs no separate mechanism. Roughly 105 tools reach their
data without touching HTTP -- AgenticTool ~50, XMLTool ~19, ComposeTool ~11, plus SOAP,
subprocess and local-file readers -- and the DSR-658 interceptor records nothing for any of
them. A "no successful call means unreachable" rule would stamp all 105 as broken while
they work perfectly. Today those tools are merely mute; that rule would make them lie.

The vocabulary is deliberately generic, per ADR-0014. A central layer can say the source
was unreachable; it cannot say ``gene_not_measured`` and must not pretend to. A tool that
carries its own domain status keeps it -- ``tools_sr/differential.py``'s ``_STATUS_DETAIL``
is the reference for when a tool genuinely needs one.
"""

from __future__ import annotations

import functools
from collections.abc import Mapping, Sequence
from typing import Any

from . import http_record

__all__ = [
    "NO_DATA",
    "SOURCE_UNREACHABLE",
    "annotate",
    "decide",
    "install",
    "is_empty",
]

SOURCE_UNREACHABLE = "source_unreachable"
NO_DATA = "no_data"

# Carried beside the status because the status alone is a label, and the inference the
# agent must NOT make -- empty means absent -- is the whole defect.
_NOTE = {
    SOURCE_UNREACHABLE: (
        "The source could not be reached, so this empty result is not evidence of "
        "absence. Do not report it as a negative finding; retry or say the check "
        "could not be completed."
    ),
    NO_DATA: (
        "The source answered and returned no matching records. This is a real "
        "negative for the query as asked."
    ),
}

# A result may already speak for itself. Overwriting any of these would replace a specific
# domain answer with a vaguer central one.
_OWN_STATUS_KEYS = ("status", "transport_status")


def _is_container(value: Any) -> bool:
    return isinstance(value, Mapping) or (
        isinstance(value, Sequence) and not isinstance(value, (str, bytes))
    )


def is_empty(result: Any) -> bool:
    """True when the payload carries no data.

    It has to look inside a mapping, because the shape that caused DSR-629 is
    ``{"results": [], "query": "SSTR2"}`` -- truthy, non-trivial, and carrying nothing but
    an echo of the question.

    Payload and echo are told apart structurally rather than by field name. Where a mapping
    has container values, those hold the payload and scalars beside them are metadata, so
    the echoed ``query`` does not make an empty ``results`` look like data. Only when a
    mapping has no containers at all does a bare scalar count as the answer, which keeps
    ``{"answer": "text"}`` honest. Naming the echo fields instead would mean maintaining a
    vocabulary that the next API extends.
    """
    if result is None:
        return True
    if isinstance(result, str):
        return not result.strip()
    if isinstance(result, Mapping):
        containers = [value for value in result.values() if _is_container(value)]
        if containers:
            return all(is_empty(value) for value in containers)
        return all(is_empty(value) for value in result.values())
    if isinstance(result, Sequence):
        return len(result) == 0
    return False


def decide(records, result: Any) -> str | None:
    """The status for this result, or ``None`` when none applies.

    Pure -- a function of the call records and the payload, with no network and no clock.

    ``None`` covers the two cases where a verdict would be noise or a lie: a result that
    carries data (nothing is ambiguous), and a tool that made no HTTP call at all (we know
    nothing about its transport, and guessing is the DSR-672 regression).
    """
    if not records:
        return None
    if not is_empty(result):
        return None
    # One source answering is enough: a tool that failed over to a mirror and succeeded
    # has genuinely seen the data, so its emptiness is real.
    if any(record.reached for record in records):
        return NO_DATA
    return SOURCE_UNREACHABLE


def annotate(result: Any, records) -> Any:
    """Return ``result`` with a transport status attached, if one applies.

    Additive and non-mutating. Only mappings are annotated -- attaching a key to a list or
    a string would change the payload's type, and 87.3% of tools have consumers expecting
    the shape they already return. Non-mapping results are therefore returned untouched,
    and that gap is recorded rather than silent.
    """
    if not isinstance(result, Mapping):
        return result
    if any(key in result for key in _OWN_STATUS_KEYS):
        return result

    status = decide(records, result)
    if status is None:
        return result

    annotated = dict(result)
    annotated["transport_status"] = status
    annotated["transport_note"] = _NOTE[status]
    return annotated


def install(cls) -> None:
    """Annotate every ``run_one_function`` result on ``cls``. Safe to call repeatedly.

    Wraps the class from outside rather than editing ``execute_function.py``, which
    re-syncs from upstream -- the same reasoning ADR-0014 applies to the 110 swallowing
    modules, applied to the seam itself.
    """
    original = cls.run_one_function
    if getattr(original, "_sr_transport_status", False):
        return

    http_record.install()

    @functools.wraps(original)
    def wrapper(self, *args, **kwargs):
        with http_record.recording() as records:
            result = original(self, *args, **kwargs)
            return annotate(result, records)

    wrapper._sr_transport_status = True
    # Marked for http_record too, so install_invocation_scope does not wrap this again and
    # open a redundant inner scope.
    wrapper._sr_http_record = True
    cls.run_one_function = wrapper
