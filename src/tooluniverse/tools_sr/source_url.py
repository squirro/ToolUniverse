"""Stamps the call that produced an answer, with credentials stripped.

Most tools return no source URL, and many that do drop their query parameters, so the link
points at a bare endpoint rather than the query behind the answer. The HTTP interceptor
already holds a fully resolved URL, so this module only chooses which call to cite and
removes what must never be published. The redactor is deliberately aggressive and masks
values rather than dropping parameters, so the stamped URL still shows that the call needed
a credential.
"""

from __future__ import annotations

import functools
import re
from collections.abc import Mapping
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from . import http_record, source_url_templates

__all__ = ["install", "pick", "redact", "stamp"]

_MASK = "REDACTED"

# Exact parameter names, normalised to lowercase alphanumerics. Exact rather than
# substring: "keyword" contains "key" and is an ordinary search parameter.
_CREDENTIAL_PARAMS = {
    "apikey", "key", "token", "accesstoken", "authtoken", "auth", "secret",
    "clientsecret", "clientid", "password", "passwd", "pwd", "email", "mail",
    "username", "user", "signature", "sig", "credential", "credentials",
    "sessionid", "session", "bearer", "jwt",
}


def _normalise(name: str) -> str:
    return "".join(char for char in name.lower() if char.isalnum())


# A credential parameter inside free text. The same names redact() masks in a URL, on a
# value that runs to the next delimiter; underscores and hyphens in the name are optional,
# so `api_key`, `apiKey` and `api-key` all match.
_IN_TEXT = re.compile(
    r"(?i)(?<![\w-])(" + "|".join(
        r"[_-]?".join(re.escape(ch) for ch in name) for name in sorted(_CREDENTIAL_PARAMS, key=len, reverse=True)
    ) + r")(=)([^&\s\"'<>,;)\]]+)"
)


def scrub(value):
    """``value`` with every credential-bearing ``name=value`` in any string masked.

    Recursive over dicts and lists, non-mutating, and applied to the whole result: a client
    can embed the request URL in an error message, and enumerating field names would leak
    again at the next field a client invents.
    """
    if isinstance(value, str):
        return _IN_TEXT.sub(lambda m: f"{m.group(1)}={_MASK}", value) if "=" in value else value
    if isinstance(value, Mapping):
        return {k: scrub(v) for k, v in value.items()}
    if isinstance(value, list):
        return [scrub(v) for v in value]
    if isinstance(value, tuple):
        return tuple(scrub(v) for v in value)
    return value


def redact(url: str) -> str:
    """The URL with every credential-bearing query value masked.

    Masked in place rather than removed, so the link still records that the call required a
    credential.
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


# Methods whose URL identifies the query. A POST puts its parameters in the body, so every
# call to one GraphQL endpoint shares a URL that says nothing about the question asked.
_CITABLE_METHODS = frozenset({"GET", "HEAD"})


def pick(records) -> str | None:
    """The URL to cite: the **last** call that reached its source with a citable method.

    Last, not first, because a tool routinely resolves an identifier before querying with
    it, and the lookup is not where the answer came from. POSTs are skipped even when they
    succeed: a shared endpoint URL is the same for every question, so it cites nothing.
    Those families need a declarative ``source_url`` template instead.
    """
    for record in reversed(list(records)):
        if record.reached and getattr(record, "method", "GET").upper() in _CITABLE_METHODS:
            return record.url
    return None


def stamp(result, records, tool_name=None, arguments=None, config=None):
    """Return ``result`` with a redacted ``source_url``, if one can be cited.

    Additive and non-mutating. A tool that already cites its own source keeps it, and a
    declared template outranks the intercepted URL: the template names the record a reader
    can open, while the interception can only report the endpoint that was called.
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

    A citation must never be the thing that raises, so anything unexpected yields
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
    re-syncs from upstream.
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
        # A missing registry or unknown tool gives None, and the template lookup then
        # falls back to the intercepted URL.
        config = (getattr(self, "all_tool_dict", None) or {}).get(name)

        with http_record.recording() as records:
            result = original(self, *args, **kwargs)
            return stamp(scrub(result), records, tool_name=name, arguments=arguments,
                         config=config)

    wrapper._sr_source_url = True
    cls.run_one_function = wrapper
