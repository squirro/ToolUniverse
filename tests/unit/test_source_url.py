"""A claim should arrive with a link the researcher can open (DSR-667).

Measured: 71% of tools return no source URL at all, and of the 233 that do, 109 drop their
query parameters, because URL construction substitutes path parameters only. So the link
that exists often lands on a bare endpoint rather than the query that produced the answer.

The DSR-658 interceptor already holds the fully resolved URL -- ``HTTPAdapter.send``
receives a ``PreparedRequest`` whose ``url`` has the query string attached -- so this is
mostly a matter of choosing which call to cite and stripping what must never be published.

Redaction is a hard requirement, not polish: 24 modules pass ``api_key`` and several put
``email``/``password`` in the query string. A stamped URL that leaks one is a security
incident, so the redactor is deliberately aggressive -- degrading a link is cheap,
publishing a key is not.
"""

import pytest

from tooluniverse.tools_sr import http_record, source_url


def _record(url, reached=True, status=200, method="GET"):
    return http_record.CallRecord(
        url=url,
        status_code=status if reached else None,
        reached=reached,
        error=None if reached else "ConnectionError('refused')",
        method=method,
    )


# --- a citation must identify the query (DSR-631) ---
# All 63 OpenTargets tools POST to one GraphQL endpoint, so the captured URL is identical
# for every question asked. Stamping it would produce a footnote that looks checked and
# lands somewhere useless -- which DSR-631 calls worse than no citation at all.


def test_a_post_is_not_cited_because_its_url_does_not_identify_the_query():
    records = [_record("https://api.platform.opentargets.org/api/v4/graphql", method="POST")]

    assert source_url.pick(records) is None


def test_a_get_beside_a_post_is_still_cited():
    """A tool that resolves over REST then queries GraphQL can still cite the REST call."""
    records = [
        _record("https://rest.ensembl.org/lookup/symbol/human/SSTR2?content-type=json"),
        _record("https://api.platform.opentargets.org/api/v4/graphql", method="POST"),
    ]

    assert source_url.pick(records).startswith("https://rest.ensembl.org/")


def test_a_graphql_only_tool_returns_a_well_formed_result_with_no_source_url():
    result = {"associations": [{"id": 1}]}

    stamped = source_url.stamp(
        result, [_record("https://api.platform.opentargets.org/api/v4/graphql", method="POST")]
    )

    assert stamped == result
    assert "source_url" not in stamped


# --- redaction ---


@pytest.mark.parametrize(
    "param", ["api_key", "apiKey", "apikey", "API_KEY", "access_token", "token"]
)
def test_a_credential_parameter_never_survives_into_the_stamped_url(param):
    url = f"https://api.fda.gov/drug/event.json?search=aspirin&{param}=s3cr3t"

    redacted = source_url.redact(url)

    assert "s3cr3t" not in redacted, redacted
    assert "search=aspirin" in redacted


@pytest.mark.parametrize("param", ["email", "password", "client_secret", "secret"])
def test_contact_and_secret_parameters_are_redacted_too(param):
    """Unpaywall requires email in the query; BRENDA passes email and password."""
    url = f"https://example.org/q?term=TP53&{param}=someone%40example.com"

    assert "someone" not in source_url.redact(url)


def test_the_parameter_is_kept_but_its_value_masked():
    """Keeping the key name shows the call needed credentials; the value is what leaks."""
    redacted = source_url.redact("https://x.org/q?api_key=abc&gene=TP53")

    assert "api_key=REDACTED" in redacted
    assert "gene=TP53" in redacted


def test_an_ordinary_parameter_that_merely_contains_key_is_not_redacted():
    """'keyword' is not a credential; a blunt substring rule would break real queries."""
    redacted = source_url.redact("https://x.org/search?keyword=kinase&monkey=1")

    assert "keyword=kinase" in redacted
    assert "monkey=1" in redacted


def test_a_url_with_no_query_is_returned_unchanged():
    assert source_url.redact("https://x.org/entry/P04637") == "https://x.org/entry/P04637"


# --- which call gets cited ---


def test_the_last_successful_call_is_cited_not_the_first():
    """A tool that resolves an ID then queries should cite the query, not the lookup."""
    records = [
        _record("https://x.org/resolve?symbol=TP53"),
        _record("https://x.org/associations?id=ENSG00000141510"),
    ]

    assert source_url.pick(records) == "https://x.org/associations?id=ENSG00000141510"


def test_a_failed_call_is_never_cited():
    records = [
        _record("https://x.org/good?a=1"),
        _record("https://x.org/dead?b=2", reached=False),
    ]

    assert source_url.pick(records) == "https://x.org/good?a=1"


def test_nothing_is_cited_when_no_call_succeeded():
    assert source_url.pick([_record("https://x.org/dead", reached=False)]) is None


def test_nothing_is_cited_when_there_were_no_calls():
    assert source_url.pick([]) is None


# --- stamping ---


def test_the_stamped_url_keeps_the_query_that_produced_the_answer():
    """The 109 tools whose links dropped their query parameters are the point of this."""
    records = [_record("https://rest.uniprot.org/uniprotkb/search?query=SSTR2&size=5")]

    stamped = source_url.stamp({"results": [{"id": 1}]}, records)

    assert stamped["source_url"].endswith("?query=SSTR2&size=5")


def test_a_tool_making_no_http_call_is_well_formed_with_no_source_url():
    result = {"answer": "computed locally"}

    stamped = source_url.stamp(result, [])

    assert stamped == result
    assert "source_url" not in stamped


def test_stamping_does_not_mutate_the_original_result():
    result = {"results": []}

    source_url.stamp(result, [_record("https://x.org/q?a=1")])

    assert "source_url" not in result


def test_a_result_that_is_not_a_mapping_is_returned_untouched():
    assert source_url.stamp([1, 2], [_record("https://x.org/q")]) == [1, 2]


def test_a_result_that_already_cites_its_source_is_left_alone():
    """A tool that built a better, domain-aware link keeps it."""
    result = {"rows": [], "source_url": "https://x.org/curated/view"}

    stamped = source_url.stamp(result, [_record("https://x.org/api?raw=1")])

    assert stamped["source_url"] == "https://x.org/curated/view"


def test_the_stamped_url_is_redacted():
    """The two requirements meet here: cite the call, never publish the key."""
    records = [_record("https://api.fda.gov/drug/event.json?search=x&api_key=LEAK")]

    stamped = source_url.stamp({"results": [1]}, records)

    assert "LEAK" not in stamped["source_url"]


# --- a credential must not leave through ANY string in a result ----------------
# The openFDA client embeds the full request URL in its HTTPError message, so a 404
# carried `api_key=<real key>` in the `error` field of the result, through the agent's
# trace, into a committed report. `source_url` was redacted; nothing else was.

from tooluniverse.tools_sr.source_url import scrub  # noqa: E402


def test_scrub_masks_a_credential_wherever_a_string_carries_it():
    result = {
        "status": "error",
        "error": ("API request failed: 404 Client Error for url: https://api.fda.gov/drug/"
                  "event.json?search=x&limit=10&api_key=HvU6EZYAgAtaMSoqQvQRjTQ"),
        "detail": [{"note": "retry with token=abc123def456 later"}],
        "count": 3,
        "source_url": "https://api.fda.gov/drug/event.json?search=x&api_key=REDACTED",
    }

    out = scrub(result)

    assert "HvU6EZYAgAtaMSoqQvQRjTQ" not in str(out)
    assert out["error"].endswith("&api_key=REDACTED")
    assert out["detail"][0]["note"] == "retry with token=REDACTED later"
    assert out["count"] == 3 and out["status"] == "error"
    assert result["error"].endswith("HvU6EZYAgAtaMSoqQvQRjTQ"), "non-mutating"


def test_scrub_leaves_ordinary_text_and_non_credential_parameters_alone():
    result = {"data": "keyword=apple&limit=5&api_version=2", "list": ["plain", 7, None]}
    assert scrub(result) == result


def test_the_wrapper_scrubs_before_it_stamps():
    """Through the installed wrapper: an error result with a key in its text comes
    back masked even when no source URL can be cited."""
    from tooluniverse.tools_sr import source_url

    class Registry:
        all_tool_dict = {}

        def run_one_function(self, function_call_json):
            return {"status": "error", "error": "GET https://x.test/?api_key=SECRET12345678901234 failed"}

    source_url.install(Registry)
    out = Registry().run_one_function({"name": "t", "arguments": {}})
    assert "SECRET12345678901234" not in str(out)
    assert out["error"] == "GET https://x.test/?api_key=REDACTED failed"
