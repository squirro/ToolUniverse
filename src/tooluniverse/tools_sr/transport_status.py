"""Says which kind of empty an empty result is.

Most tools declare no ``status`` field, so the annotation is additive, and the vocabulary is
deliberately generic: a central layer can say the source was unreachable, not why a
particular domain has no rows. The rule that makes it safe is that absence of call records
is not evidence of unreachability; only a record of a failed call is. A tool that reaches
its data without touching HTTP records nothing and works perfectly.
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

# Carried beside the status because the status alone is a label; the inference the agent
# must not make is that empty means absent.
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

# Only a verdict we already wrote stops us writing another. `status` is deliberately absent:
# in the BaseREST envelope it is the success flag, not a domain vocabulary, so treating it
# as one suppresses the annotation on the whole family.
_OWN_STATUS_KEYS = ("transport_status",)

# Envelope scaffolding: present whether or not the result carries records, so it must not
# count towards emptiness. `metadata` holds non-empty strings beside an empty payload, and
# the transport keys are our own, so install order must not decide the verdict.
_ENVELOPE_KEYS = frozenset(
    {"transport_status", "transport_note", "source_url", "url", "metadata", "status"}
)


def _is_container(value: Any) -> bool:
    return isinstance(value, Mapping) or (
        isinstance(value, Sequence) and not isinstance(value, (str, bytes))
    )


def is_empty(result: Any) -> bool:
    """True when the payload carries no data.

    It looks inside a mapping, because a result can be truthy and carry nothing but an empty
    list beside an echo of the question. Payload and echo are told apart structurally: where
    a mapping has container values those hold the payload, and only when it has none does a
    bare scalar count as the answer. Naming the echo fields instead would mean maintaining a
    vocabulary that the next API extends.
    """
    if result is None:
        return True
    if isinstance(result, str):
        return not result.strip()
    if isinstance(result, Mapping):
        payload = {
            key: value
            for key, value in result.items()
            if key not in _ENVELOPE_KEYS
        }
        containers = [value for value in payload.values() if _is_container(value)]
        if containers:
            return all(is_empty(value) for value in containers)
        return all(is_empty(value) for value in payload.values())
    if isinstance(result, Sequence):
        return len(result) == 0
    return False


def decide(records, result: Any) -> str | None:
    """The status for this result, or ``None`` when none applies.

    Pure: a function of the call records and the payload. ``None`` covers the two cases
    where a verdict would be noise or a lie: a result that carries data, and a tool that
    made no HTTP call at all, whose transport we know nothing about.
    """
    if not records:
        return None
    if not is_empty(result):
        return None
    # One source answering is enough: a tool that failed over to a mirror has seen the data.
    if any(record.reached for record in records):
        return NO_DATA
    return SOURCE_UNREACHABLE


def annotate(result: Any, records) -> Any:
    """Return ``result`` with a transport status attached, if one applies.

    Additive and non-mutating. Only mappings are annotated: attaching a key to a list or a
    string would change the payload type that consumers already expect.
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
    re-syncs from upstream.
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
    # Marked for http_record too, so install_invocation_scope does not open a redundant
    # inner scope.
    wrapper._sr_http_record = True
    cls.run_one_function = wrapper
