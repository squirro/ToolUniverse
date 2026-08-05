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

from . import http_record

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


def pick(records) -> str | None:
    """The URL to cite: the **last** call that actually reached its source.

    Last, not first, because tools routinely resolve an identifier before querying with it
    (symbol -> Ensembl ID -> associations). Citing the first hands the researcher the
    lookup rather than the query their answer came from. Failed calls are never cited --
    there is nothing at the other end to open.
    """
    for record in reversed(list(records)):
        if record.reached:
            return record.url
    return None


def stamp(result, records):
    """Return ``result`` with a redacted ``source_url``, if one can be cited.

    Additive and non-mutating, like the transport-status annotation. A tool that already
    cites its own source keeps it: a domain-aware link to a human-readable record is
    better than the raw API call, and overwriting it would be a downgrade.
    """
    if not isinstance(result, Mapping) or "source_url" in result:
        return result

    url = pick(records)
    if url is None:
        return result

    stamped = dict(result)
    stamped["source_url"] = redact(url)
    return stamped


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
        with http_record.recording() as records:
            result = original(self, *args, **kwargs)
            return stamp(result, records)

    wrapper._sr_source_url = True
    cls.run_one_function = wrapper
