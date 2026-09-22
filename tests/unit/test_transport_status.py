"""An empty result must say which kind of empty it is (DSR-666 / DSR-672).

DSR-629: a dead network read as a biological negative. The tool returned an empty payload,
the agent read "no association found", and nothing anywhere said the source had never
answered. 1,957 of 2,241 tools declare no status field at all.

Roughly 105 tools reach their data without HTTP, and the interceptor records nothing for
any of them. So the rule is: **absence of call records is not evidence of unreachability.
Only a record of a failed call is.** The vocabulary is deliberately generic — a central
layer can say the source was unreachable; it cannot say "gene not measured".
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

# The real REST envelope, captured live from sempart. Two things about that shape defeated
# the first cut of this module: `status` is the envelope's own success flag rather than a
# domain vocabulary, and `metadata` holds non-empty strings beside an empty `data`.
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


# --- the decision is a pure function, testable with no network ---


@pytest.mark.parametrize(
    "records,result,expected",
    [
        # DSR-672: a SOAP, subprocess, local-file or LLM tool made no HTTP call.
        ([], {}, None),
        ([FAILED], {}, transport_status.SOURCE_UNREACHABLE),
        ([REACHED], {}, transport_status.NO_DATA),
        # A tool that tries a mirror, fails, then succeeds has genuinely seen the data.
        ([FAILED, REACHED], {}, transport_status.NO_DATA),
        # Nothing is ambiguous when data came back, so nothing is added.
        ([REACHED], {"hits": [{"id": 1}]}, None),
        ([FAILED], {"hits": [{"id": 1}]}, None),
        # DSR-667 stamps source_url. Emptiness is judged on the payload, not on our own
        # annotation — otherwise install order would decide the verdict.
        ([FAILED], {"source_url": "https://x.org/q?a=1"}, transport_status.SOURCE_UNREACHABLE),
    ],
)
def test_the_verdict_follows_only_from_records_and_payload(records, result, expected):
    assert transport_status.decide(records, result) == expected


# --- what counts as empty ---


@pytest.mark.parametrize(
    "result",
    [None, {}, [], "", "   ", {"results": []}, {"data": None, "meta": {}},
     {"source_url": "https://x.org/q?a=1"}, CT_EMPTY, PMC_EMPTY],
)
def test_these_payloads_carry_no_data(result):
    assert transport_status.is_empty(result)


@pytest.mark.parametrize(
    "result",
    [{"hits": [{"id": 1}]}, [1], "text", {"count": 0, "rows": [{"a": 1}]}, UNIPROT_FULL],
)
def test_these_payloads_carry_data(result):
    assert not transport_status.is_empty(result)


# --- the annotation is additive ---


@pytest.mark.parametrize(
    "result,records,expected",
    [
        ({"results": [], "query": "SSTR2"}, [FAILED], transport_status.SOURCE_UNREACHABLE),
        (CT_EMPTY, [FAILED], transport_status.SOURCE_UNREACHABLE),
        # The envelope's own success flag must not suppress the transport verdict: the
        # annotation writes a DIFFERENT key and overwrites nothing.
        (CT_EMPTY, [REACHED], transport_status.NO_DATA),
        (PMC_EMPTY, [REACHED], transport_status.NO_DATA),
        # A tool's own domain vocabulary is left alone; the two read coherently — the
        # source answered, and the domain reason the answer is empty is gene_not_measured.
        ({"status": "gene_not_measured", "rows": []}, [REACHED], transport_status.NO_DATA),
    ],
)
def test_annotation_adds_a_status_without_disturbing_the_payload(result, records, expected):
    annotated = transport_status.annotate(result, records)

    assert annotated["transport_status"] == expected
    assert {k: v for k, v in annotated.items() if k in result} == result


def test_the_annotation_says_unreachable_is_not_evidence_of_absence():
    note = transport_status.annotate({}, [FAILED])["transport_note"]

    assert "not evidence" in note.lower(), note


def test_an_existing_transport_verdict_is_not_written_twice():
    already = {"rows": [], "transport_status": "source_unreachable"}

    assert transport_status.annotate(already, [REACHED]) == already


@pytest.mark.parametrize(
    "result,records",
    [
        # DSR-672's headline: no records must not become a false accusation.
        ({"answer": ""}, []),
        # Annotation is additive or nothing; it never changes a payload's type.
        ([], [FAILED]),
        ("plain text", [FAILED]),
    ],
)
def test_annotation_is_additive_or_nothing(result, records):
    assert transport_status.annotate(result, records) == result


def test_annotating_does_not_mutate_the_original_result():
    result = {"results": []}

    transport_status.annotate(result, [FAILED])

    assert "transport_status" not in result


def test_a_non_http_tool_that_errors_is_still_distinguishable_from_one_with_no_data():
    """Its own status survives; the central layer does not flatten the distinction."""
    errored = transport_status.annotate({"status": "error", "rows": []}, [])
    empty = transport_status.annotate({"rows": []}, [])

    assert errored["status"] == "error"
    assert errored != empty


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

    assert dead["transport_status"] == transport_status.SOURCE_UNREACHABLE
    assert answered["transport_status"] == transport_status.NO_DATA


def test_install_is_idempotent(empty_server):
    transport_status.install(_Host)
    transport_status.install(_Host)

    result = _Host(f"{empty_server}/search").run_one_function({"name": "t"})

    assert result["transport_status"] == transport_status.NO_DATA


# --- DSR-672: the transport families that never reach the interceptor ---
# Measured, the ticket's model needed two corrections. ComposeTool is NOT in the blind spot
# (a record reports to every open scope), and neither is SOAP (zeep goes through requests).
# What genuinely goes unrecorded is anything bypassing requests -- local file readers,
# subprocess shell-outs, and LLM SDKs built on httpx. Each returns an EMPTY result, the
# only case that could be mislabelled, so passing means no false accusation.


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
