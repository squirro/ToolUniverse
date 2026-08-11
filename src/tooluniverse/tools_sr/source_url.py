"""Stamps the call that produced an answer, with credentials stripped (DSR-667).

71% of tools return no source URL at all, and of the 233 that do, 109 drop their query
parameters -- URL construction substitutes path parameters only, so the link that exists
often points at a bare endpoint rather than the query that produced the answer. A claim a
researcher cannot reopen is a claim they have to take on trust.

The DSR-658 interceptor already holds what is needed: ``HTTPAdapter.send`` receives a
``PreparedRequest`` whose ``url`` is fully resolved with its query string attached. So this
module only has to choose which call to cite and remove what must never be published.

**Redaction is a hard requirement.** 24 modules pass ``api_key``, and several put ``email``
or ``password`` in the query string. The redactor is deliberately aggressive: degrading a
link costs a little convenience, publishing a key is an incident. It masks values rather
than dropping parameters, so the stamped URL still shows that the call needed a credential.
"""

from __future__ import annotations

import functools
from collections.abc import Mapping
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from . import http_record, source_url_templates

__all__ = ["install", "pick", "redact", "stamp"]

_MASK = "REDACTED"

# Exact parameter names (normalised: lowercased, non-alphanumerics removed). Matching
# exactly rather than by substring is deliberate -- "keyword" contains "key" and is an
# ordinary search parameter, so a substring rule would corrupt real queries.
_CREDENTIAL_PARAMS = {
    "apikey", "key", "token", "accesstoken", "authtoken", "auth", "secret",
    "clientsecret", "clientid", "password", "passwd", "pwd", "email", "mail",
    "username", "user", "signature", "sig", "credential", "credentials",
    "sessionid", "session", "bearer", "jwt",
}


def _normalise(name: str) -> str:
    return "".join(char for char in name.lower() if char.isalnum())


def redact(url: str) -> str:
    """The URL with every credential-bearing query value masked.

    Values are masked in place rather than removed, so the stamped link still records that
    the call required a credential -- useful when a researcher cannot reproduce it.
    """
    parsed = urlparse(url)
    if not parsed.query:
        return url

    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    cleaned = [
        (name, _MASK if _normalise(name) in _CREDENTIAL_PARAMS else value)
        for name, value in pairs
    ]
    return urlunparse(parsed._replace(query=urlencode(cleaned)))


# Methods whose URL identifies the query. A GET puts its parameters in the URL; a POST
# puts them in the body, so every call to a GraphQL endpoint shares one URL and citing it
# says nothing about the question asked.
_CITABLE_METHODS = frozenset({"GET", "HEAD"})


def pick(records) -> str | None:
    """The URL to cite: the **last** call that reached its source with a citable method.

    Last, not first, because tools routinely resolve an identifier before querying with it
    (symbol -> Ensembl ID -> associations). Citing the first hands the researcher the
    lookup rather than the query their answer came from. Failed calls are never cited --
    there is nothing at the other end to open.

    POSTs are skipped even when they succeed. All 63 OpenTargets tools POST to a single
    GraphQL endpoint, so a stamped URL would be identical for every question and would
    render as a footnote that looks checked and lands nowhere useful -- which DSR-631
    rates as worse than no citation at all. Those families need a declarative
    ``source_url`` template instead (DSR-671).
    """
    for record in reversed(list(records)):
        if record.reached and getattr(record, "method", "GET").upper() in _CITABLE_METHODS:
            return record.url
    return None


def stamp(result, records, tool_name=None, arguments=None, config=None):
    """Return ``result`` with a redacted ``source_url``, if one can be cited.

    Additive and non-mutating, like the transport-status annotation. A tool that already
    cites its own source keeps it: a domain-aware link to a human-readable record is
    better than the raw API call, and overwriting it would be a downgrade.

    A declared template outranks the intercepted URL for the same reason (DSR-671). The
    interception can only report the endpoint that was called; the template names the
    record a reader can actually open, and for the tools that share one GraphQL endpoint
    it is the only thing that distinguishes one question from another.
    """
    if not isinstance(result, Mapping) or "source_url" in result:
        return result

    url = source_url_templates.declared_url(tool_name, arguments, config) or pick(records)
    if url is None:
        return result

    stamped = dict(result)
    stamped["source_url"] = redact(url)
    return stamped


def _call_parts(call):
    """``(tool name, arguments)`` from a function-call payload, defensively.

    Callers pass a mapping, but the wrapper sits on the hot path for every tool result and
    a citation must never be the thing that raises. Anything unexpected yields
    ``(None, None)``, which downgrades to the intercepted URL.
    """
    if not isinstance(call, Mapping):
        return None, None
    name = call.get("name")
    arguments = call.get("arguments")
    return (name if isinstance(name, str) else None,
            arguments if isinstance(arguments, Mapping) else None)


def install(cls) -> None:
    """Stamp every ``run_one_function`` result on ``cls``. Safe to call repeatedly.

    Wraps the class from outside rather than editing ``execute_function.py``, which
    re-syncs from upstream (ADR-0014).
    """
    original = cls.run_one_function
    if getattr(original, "_sr_source_url", False):
        return

    http_record.install()

    @functools.wraps(original)
    def wrapper(self, *args, **kwargs):
        call = kwargs.get("function_call_json")
        if call is None and args:
            call = args[0]
        name, arguments = _call_parts(call)
        # Missing registry, unknown tool: both give None, and the template lookup falls
        # back to the intercepted URL. Never let citation raise into a tool result.
        config = (getattr(self, "all_tool_dict", None) or {}).get(name)

        with http_record.recording() as records:
            result = original(self, *args, **kwargs)
            return stamp(result, records, tool_name=name, arguments=arguments,
                         config=config)

    wrapper._sr_source_url = True
    cls.run_one_function = wrapper
