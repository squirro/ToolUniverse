"""An env-file inline comment is not part of the credential.

A shell strips `KEY=value  # note`; Docker's `--env-file` does not — everything
after the first `=` becomes the value, and comments are only honoured on their
own line. `deploy/.env` and the tracked `deploy/.env.template` both use inline
comments heavily, so 12 variables reach the container carrying prose.

Two distinct failures came out of that, both diagnosed 2026-08-03:

* **a real key gets corrupted.** `UMLS_API_KEY` is a valid 36-character key
  followed by a comment. Sent as-is it is rejected; stripped, it returns 25
  results from the UTS API. Five tools (`umls_*`, `snomed_*`, `loinc_*`,
  `icd_search_codes`) had been written off as having no credential at all.
* **an absent key looks present.** `SEMANTIC_SCHOLAR_API_KEY=     # higher rate
  limit …` has no key before the comment, so the value is pure prose. It passes
  the "is it set" check, then goes out as an HTTP header, and the request dies
  with *"Invalid leading whitespace, reserved character(s), or return
  character(s) in header value"* — a rate-limit tool failing on header
  validation, which names nothing a reader could act on.

`.env` is not ours to police, so the sanitising belongs at the point of use.
"""

import pytest

from tooluniverse.execute_function import ToolUniverse


@pytest.fixture
def tu():
    return ToolUniverse()


@pytest.mark.unit
def test_a_trailing_comment_is_stripped_from_a_real_key(tu, monkeypatch):
    """The UMLS case: valid key, comment appended, rejected by the service."""
    monkeypatch.setenv("SOME_API_KEY", "abcd1234-5678-90ef  # get one at example.org")

    assert tu._get_api_key("SOME_API_KEY") == "abcd1234-5678-90ef"


@pytest.mark.unit
def test_a_value_that_is_only_a_comment_counts_as_absent(tu, monkeypatch):
    """The Semantic Scholar case: prose must never reach an HTTP header."""
    monkeypatch.setenv("SOME_API_KEY", "     # higher rate limit for Semantic Scholar")

    assert not tu._get_api_key("SOME_API_KEY")


@pytest.mark.unit
def test_surrounding_whitespace_and_quotes_go_too(tu, monkeypatch):
    monkeypatch.setenv("SOME_API_KEY", '  "abcd1234"  ')

    assert tu._get_api_key("SOME_API_KEY") == "abcd1234"


@pytest.mark.unit
def test_a_key_that_legitimately_contains_a_hash_is_not_truncated(tu, monkeypatch):
    """Only a hash that starts a comment — preceded by whitespace — is one."""
    monkeypatch.setenv("SOME_API_KEY", "abcd#1234")

    assert tu._get_api_key("SOME_API_KEY") == "abcd#1234"


@pytest.mark.unit
def test_an_unset_key_is_still_absent(tu, monkeypatch):
    monkeypatch.delenv("SOME_API_KEY", raising=False)

    assert not tu._get_api_key("SOME_API_KEY")
