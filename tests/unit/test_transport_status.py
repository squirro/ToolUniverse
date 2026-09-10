"""An empty result must say which kind of empty it is (DSR-666 / DSR-672).

DSR-629: a dead network read as a biological negative. The tool returned an empty payload,
the agent read "no association found", and nothing anywhere said the source had never
answered. 1,957 of 2,241 tools declare no status field at all, so there is currently
nowhere for that answer to live.

These two tickets are one release unit, and the reason is the rule below. Roughly 105 tools
reach their data without HTTP -- AgenticTool ~50, XMLTool ~19, ComposeTool ~11 -- and the
interceptor records nothing for any of them. A naive "no successful call means unreachable"
rule would stamp all 105 as broken while they work perfectly, which is worse than the
defect being fixed: today they are merely mute, afterwards they would be lying.

So the rule is: **absence of call records is not evidence of unreachability. Only a record
of a failed call is.** DSR-672 then needs no separate mechanism.

The vocabulary is deliberately generic. A central layer can say the source was unreachable;
it cannot say "gene not measured" and must not pretend to. Tools carrying their own domain
vocabulary keep it.
"""

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
import requests

from tooluniverse.tools_sr import http_record, transport_status

REACHED = http_record.CallRecord(
    url="https://api.example/x?gene=SSTR2", status_code=200, reached=True, error=None
)
FAILED = http_record.CallRecord(
    url="https://api.example/x?gene=SSTR2",
    status_code=None,
    reached=False,
    error="ConnectionError('refused')",
)


# --- the decision is a pure function, testable with no network ---


def test_no_records_at_all_yields_no_verdict():
    """The DSR-672 case: a SOAP, subprocess, local-file or LLM tool made no HTTP call."""
    assert transport_status.decide([], {}) is None


def test_an_empty_result_after_a_failed_call_is_unreachable():
    assert transport_status.decide([FAILED], {}) == transport_status.SOURCE_UNREACHABLE


def test_an_empty_result_after_a_successful_call_is_no_data():
    assert transport_status.decide([REACHED], {}) == transport_status.NO_DATA


def test_one_source_answering_is_enough_to_mean_no_data():
    """A tool that tries a mirror, fails, then succeeds has genuinely seen the data."""
    assert transport_status.decide([FAILED, REACHED], {}) == transport_status.NO_DATA


def test_a_non_empty_result_needs_no_verdict():
    """Nothing is ambiguous when data came back, so nothing is added."""
    assert transport_status.decide([REACHED], {"hits": [{"id": 1}]}) is None
    assert transport_status.decide([FAILED], {"hits": [{"id": 1}]}) is None


# --- what counts as empty ---


@pytest.mark.parametrize(
    "result", [None, {}, [], "", "   ", {"results": []}, {"data": None, "meta": {}}]
)
def test_these_payloads_carry_no_data(result):
    assert transport_status.is_empty(result)


@pytest.mark.parametrize(
    "result", [{"hits": [{"id": 1}]}, [1], "text", {"count": 0, "rows": [{"a": 1}]}]
)
def test_these_payloads_carry_data(result):
    assert not transport_status.is_empty(result)


# --- the annotation is additive ---


def test_annotation_adds_a_status_without_disturbing_the_payload():
    result = {"results": [], "query": "SSTR2"}

    annotated = transport_status.annotate(result, [FAILED])

    assert annotated["query"] == "SSTR2"
    assert annotated["results"] == []
    assert annotated["transport_status"] == transport_status.SOURCE_UNREACHABLE


def test_the_annotation_says_unreachable_is_not_evidence_of_absence():
    annotated = transport_status.annotate({}, [FAILED])

    note = annotated["transport_note"].lower()
    assert "not evidence" in note, annotated["transport_note"]


# --- the real REST envelope, captured live from sempart ---
# Every BaseREST-family tool answers {status, data, metadata, source_url}. Two things about
# that shape defeated the first cut of this module, and between them they made DSR-666
# inert on precisely the family where DSR-629 lives:
#
#   1. `status` is the envelope's own success flag, not a domain vocabulary. Skipping
#      annotation whenever a `status` key exists suppressed every one of these tools --
#      and it was never needed, because the annotation writes a DIFFERENT key and
#      overwrites nothing.
#   2. `metadata` holds non-empty strings beside an empty `data`, so an emptiness rule that
#      looks at every container reads the envelope as carrying data when it carries none.

CT_EMPTY = {
    "status": "success",
    "data": {"studies": [], "total_count": 0, "next_page_token": None},
    "metadata": {"source": "ClinicalTrials.gov API v2", "operation": "search"},
    "source_url": "https://clinicaltrials.gov/api/v2/studies?format=json",
}
PMC_EMPTY = {
    "status": "success",
    "data": [],
    "metadata": {"count": 0, "query": "zzz", "source": "Europe PMC"},
    "source_url": "https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=zzz",
}
UNIPROT_FULL = {
    "status": "success",
    "data": {"primaryAccession": "P30874", "gene_names": ["SSTR2"]},
    "metadata": {"source": "UniProt"},
    "source_url": "https://rest.uniprot.org/uniprotkb/P30874.json",
}


@pytest.mark.parametrize("envelope", [CT_EMPTY, PMC_EMPTY], ids=["clintrials", "europepmc"])
def test_a_rest_envelope_carrying_no_records_is_empty(envelope):
    assert transport_status.is_empty(envelope)


def test_a_rest_envelope_carrying_records_is_not_empty():
    assert not transport_status.is_empty(UNIPROT_FULL)


@pytest.mark.parametrize("envelope", [CT_EMPTY, PMC_EMPTY], ids=["clintrials", "europepmc"])
def test_a_rest_envelope_still_gets_a_transport_status(envelope):
    """The envelope's own success flag must not suppress the transport verdict."""
    annotated = transport_status.annotate(envelope, [REACHED])

    assert annotated["transport_status"] == transport_status.NO_DATA
    assert annotated["status"] == "success", "the envelope's own status must survive"


def test_a_rest_envelope_after_a_dead_source_says_unreachable():
    annotated = transport_status.annotate(CT_EMPTY, [FAILED])

    assert annotated["transport_status"] == transport_status.SOURCE_UNREACHABLE


def test_a_tool_with_its_own_status_vocabulary_keeps_it_untouched():
    """tools_sr/differential.py's four-member enum is the reference for domain status.

    "Keeps it rather than being overwritten" means exactly that: the domain answer is left
    alone. It does NOT mean suppressing the transport verdict, which goes to its own key
    and contradicts nothing. The first cut suppressed ours whenever any `status` existed,
    and measuring live showed what that cost -- every BaseREST tool answers
    {status: "success", ...}, so the annotation never appeared on the family where the
    defect actually lives.

    The two together read coherently: the source answered, and the domain reason the answer
    is empty is gene_not_measured.
    """
    result = {"status": "gene_not_measured", "rows": []}

    annotated = transport_status.annotate(result, [REACHED])

    assert annotated["status"] == "gene_not_measured"
    assert annotated["transport_status"] == transport_status.NO_DATA


def test_an_existing_transport_verdict_is_not_written_twice():
    already = {"rows": [], "transport_status": "source_unreachable"}

    assert transport_status.annotate(already, [REACHED]) == already


def test_a_non_http_tool_is_never_stamped_unreachable():
    """DSR-672's headline: no records must not become a false accusation."""
    result = {"answer": ""}

    annotated = transport_status.annotate(result, [])

    assert "transport_status" not in annotated
    assert annotated == result


def test_a_result_that_is_not_a_mapping_is_returned_untouched():
    """Annotation is additive or nothing; it never changes a payload's type."""
    assert transport_status.annotate([], [FAILED]) == []
    assert transport_status.annotate("plain text", [FAILED]) == "plain text"


def test_annotating_does_not_mutate_the_original_result():
    result = {"results": []}

    transport_status.annotate(result, [FAILED])

    assert "transport_status" not in result


# --- the defining test: the two empties must be distinguishable ---


class _EmptyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"results": []}')

    def log_message(self, *args):
        pass


@pytest.fixture(scope="module")
def empty_server():
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), _EmptyHandler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()


def _closed_port_url() -> str:
    import socket

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    return f"http://127.0.0.1:{port}/gone"


class _Host:
    """A tool that swallows transport failure and returns empty -- the DSR-629 shape."""

    def __init__(self, url):
        self.url = url

    def run_one_function(self, function_call_json, **kwargs):
        try:
            return requests.get(self.url, timeout=5).json()
        except Exception:
            return {"results": []}


def test_a_dead_source_and_an_empty_answer_are_not_the_same_payload(empty_server):
    """The whole point. Same tool, same empty payload today; they must diverge."""
    transport_status.install(_Host)

    dead = _Host(_closed_port_url()).run_one_function({"name": "t"})
    answered = _Host(f"{empty_server}/search").run_one_function({"name": "t"})

    assert dead != answered
    assert dead["transport_status"] == transport_status.SOURCE_UNREACHABLE
    assert answered["transport_status"] == transport_status.NO_DATA


def test_install_is_idempotent(empty_server):
    transport_status.install(_Host)
    transport_status.install(_Host)

    result = _Host(f"{empty_server}/search").run_one_function({"name": "t"})

    assert result["transport_status"] == transport_status.NO_DATA


# --- DSR-672: the transport families that never reach the interceptor ---
# Measured, the ticket's model needed two corrections. ComposeTool (~11) is NOT in the
# blind spot: it delegates to other tools, and their HTTP lands in the outer scope because
# a record reports to every open scope. SOAP is not either, since zeep issues its calls
# through requests. What genuinely goes unrecorded is anything bypassing requests -- local
# file readers, subprocess shell-outs, and LLM SDKs built on httpx (AgenticTool, ~50).
#
# Each family below returns an EMPTY result, which is the only case that could be
# mislabelled. Passing means no false accusation.


def _local_file_tool(tmp_path):
    empty = tmp_path / "rows.json"
    empty.write_text("[]")

    class LocalFileTool:
        def run_one_function(self, function_call_json, **kwargs):
            import json

            return {"rows": json.loads(empty.read_text())}

    return LocalFileTool


def _subprocess_tool():
    class SubprocessTool:
        def run_one_function(self, function_call_json, **kwargs):
            import subprocess
            import sys

            out = subprocess.run(
                [sys.executable, "-c", "print('')"], capture_output=True, text=True
            )
            return {"rows": [], "stdout": out.stdout.strip()}

    return SubprocessTool


def _non_requests_client_tool(server):
    """Stands for the LLM-client family: real HTTP, but not through requests."""

    class UrllibTool:
        def run_one_function(self, function_call_json, **kwargs):
            import json
            from urllib.request import urlopen

            with urlopen(f"{server}/search") as response:
                return json.loads(response.read())

    return UrllibTool


@pytest.mark.parametrize("family", ["local_file", "subprocess", "llm_client"])
def test_a_non_http_transport_family_is_never_stamped_unreachable(
    family, tmp_path, empty_server
):
    cls = {
        "local_file": lambda: _local_file_tool(tmp_path),
        "subprocess": _subprocess_tool,
        "llm_client": lambda: _non_requests_client_tool(empty_server),
    }[family]()
    transport_status.install(cls)

    result = cls().run_one_function({"name": "t"})

    assert transport_status.is_empty(result), f"{family} fixture should return empty"
    assert "transport_status" not in result, (
        f"{family} works but was stamped {result.get('transport_status')!r}"
    )


def test_a_compose_tool_inherits_the_verdict_of_the_tool_it_delegates_to():
    """Compose is not in the blind spot: inner traffic reports to the outer scope."""
    inner_url = _closed_port_url()

    class ComposeHost:
        def run_one_function(self, function_call_json, **kwargs):
            try:
                requests.get(inner_url, timeout=5)
            except Exception:
                pass
            return {"rows": []}

    transport_status.install(ComposeHost)

    result = ComposeHost().run_one_function({"name": "t"})

    assert result["transport_status"] == transport_status.SOURCE_UNREACHABLE


def test_an_annotation_from_another_layer_does_not_make_a_result_look_full():
    """DSR-667 stamps source_url. Emptiness must be judged on the payload, not on ours.

    Order of installation would otherwise decide the verdict: a result reduced to
    ``{"source_url": ...}`` has no container values, so the scalar fallback would read the
    stamped link as data and suppress the status entirely.
    """
    assert transport_status.is_empty({"source_url": "https://x.org/q?a=1"})
    assert transport_status.decide([FAILED], {"source_url": "https://x.org/q?a=1"}) == (
        transport_status.SOURCE_UNREACHABLE
    )


def test_a_non_http_tool_that_errors_is_still_distinguishable_from_one_with_no_data():
    """Its own status survives; the central layer does not flatten the distinction."""
    errored = transport_status.annotate({"status": "error", "rows": []}, [])
    empty = transport_status.annotate({"rows": []}, [])

    assert errored["status"] == "error"
    assert errored != empty
