"""Per-invocation HTTP call recording (DSR-658).

The registry swallows transport failures: 245 broad handlers across 110 modules return an
empty value without surfacing that the call died, and 87.3% of tools have no schema slot to
report it in. That is how a dead network came to read as a biological negative (DSR-629).

Fixing 110 modules is not an option -- they re-sync from upstream. Instead a single
interception point records, per tool invocation, whether the call actually happened
(ADR-0014). This slice only *observes*; DSR-666 is what turns a record into a status on the
result, and DSR-667 is what stamps the URL.

Tests drive a real localhost HTTP server rather than mocking ``requests``. The whole point
is that interception catches calls made by modules that build their own sessions, and a
mock of the thing being intercepted cannot show that.
"""

import threading
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
import requests

from tooluniverse.tools_sr import http_record


class _Handler(BaseHTTPRequestHandler):
    """Echoes the requested path; 404s anything under /missing."""

    def do_GET(self):
        if self.path.startswith("/missing"):
            self.send_response(404)
        else:
            self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *args):
        pass


@pytest.fixture(scope="module")
def server():
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()


@pytest.fixture(autouse=True)
def installed():
    http_record.install()


def _closed_port_url() -> str:
    """A port with nothing listening, so the connection is refused immediately."""
    import socket

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    return f"http://127.0.0.1:{port}/gone"


def test_a_successful_call_is_recorded_with_its_status(server):
    with http_record.recording() as records:
        requests.get(f"{server}/hello")

    assert len(records) == 1
    assert records[0].reached is True
    assert records[0].status_code == 200


def test_an_error_status_is_recorded_as_reached(server):
    """A 404 means the source answered. That is not a transport failure."""
    with http_record.recording() as records:
        requests.get(f"{server}/missing")

    assert records[0].reached is True
    assert records[0].status_code == 404


def test_the_recorded_url_retains_its_query_string(server):
    with http_record.recording() as records:
        requests.get(f"{server}/search", params={"gene": "SSTR2", "size": 5})

    assert records[0].url.endswith("/search?gene=SSTR2&size=5"), records[0].url


def test_a_call_that_never_reaches_a_server_is_recorded_as_unreached():
    url = _closed_port_url()

    with http_record.recording() as records:
        with pytest.raises(requests.exceptions.ConnectionError):
            requests.get(url, timeout=5)

    assert len(records) == 1
    assert records[0].reached is False
    assert records[0].status_code is None
    assert records[0].error


def test_a_scope_that_makes_no_call_records_nothing():
    with http_record.recording() as records:
        pass

    assert list(records) == []


def test_a_session_built_by_the_caller_is_also_recorded(server):
    """The 74 modules each construct their own Session; the adapter catches them all."""
    session = requests.Session()

    with http_record.recording() as records:
        session.get(f"{server}/hello")

    assert len(records) == 1


def test_calls_outside_any_scope_are_not_recorded_and_still_work(server):
    response = requests.get(f"{server}/hello")

    assert response.status_code == 200
    assert http_record.current_records() == ()


def test_recording_does_not_alter_the_response(server):
    with http_record.recording():
        response = requests.get(f"{server}/hello")

    assert response.status_code == 200
    assert response.text == "ok"


def test_concurrent_scopes_do_not_see_each_others_calls(server):
    """Fifteen workers serve this registry; a shared record list would cross-contaminate."""

    def invocation(index: int) -> list[str]:
        with http_record.recording() as records:
            for _ in range(3):
                requests.get(f"{server}/worker", params={"id": index})
            return [r.url for r in records]

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(invocation, range(8)))

    for index, urls in enumerate(results):
        assert len(urls) == 3, f"worker {index} saw {len(urls)} records, expected 3"
        assert all(f"id={index}" in url for url in urls), (
            f"worker {index} saw another worker's calls: {urls}"
        )


def test_a_nested_scope_reports_to_its_parent_too(server):
    """Compose tools invoke other tools; the outer call owns the inner one's traffic."""
    with http_record.recording() as outer:
        requests.get(f"{server}/outer")
        with http_record.recording() as inner:
            requests.get(f"{server}/inner")

    assert len(inner) == 1
    assert "/inner" in inner[0].url
    assert len(outer) == 2, [r.url for r in outer]


def test_install_is_idempotent(server):
    """Re-installing must not double-record; the server calls it per process, not once."""
    http_record.install()
    http_record.install()

    with http_record.recording() as records:
        requests.get(f"{server}/hello")

    assert len(records) == 1


# --- the scope boundary is one tool invocation ---
# The records are only useful if their scope matches the thing being judged: DSR-666 asks
# "this tool returned empty -- did its source answer?", which is a question about one
# invocation. install_invocation_scope() puts that boundary on run_one_function without
# editing execute_function.py, which re-syncs from upstream.


@pytest.fixture
def unwrapped_tooluniverse():
    """Restore the class method, so wrapping it cannot leak into other tests."""
    from tooluniverse import ToolUniverse

    original = ToolUniverse.run_one_function
    yield ToolUniverse
    ToolUniverse.run_one_function = original


class _Host:
    """Stand-in for the invocation host, so the wrapper is tested without a tool load."""

    def __init__(self, url=None):
        self.url = url

    def run_one_function(self, function_call_json, **kwargs):
        if self.url:
            requests.get(self.url)
        return {"name": function_call_json["name"], "result": "done"}


def test_an_invocation_records_the_calls_its_tool_made(server):
    http_record.install_invocation_scope(_Host)
    host = _Host(f"{server}/fetch")

    host.run_one_function({"name": "some_tool"})

    records = http_record.last_invocation_records()
    assert len(records) == 1
    assert "/fetch" in records[0].url


def test_the_invocation_result_is_returned_unchanged(server):
    """This slice only observes -- DSR-666 is what changes the result."""
    http_record.install_invocation_scope(_Host)
    host = _Host(f"{server}/fetch")

    result = host.run_one_function({"name": "some_tool"})

    assert result == {"name": "some_tool", "result": "done"}


def test_records_do_not_leak_between_sequential_invocations(server):
    http_record.install_invocation_scope(_Host)
    _Host(f"{server}/first").run_one_function({"name": "a"})

    _Host().run_one_function({"name": "b"})

    assert http_record.last_invocation_records() == ()


def test_install_invocation_scope_is_idempotent(server):
    http_record.install_invocation_scope(_Host)
    http_record.install_invocation_scope(_Host)
    host = _Host(f"{server}/fetch")

    host.run_one_function({"name": "some_tool"})

    assert len(http_record.last_invocation_records()) == 1


def test_a_real_tool_invocation_making_no_http_call_records_nothing(
    unwrapped_tooluniverse,
):
    """Against the real ToolUniverse, not a stand-in.

    all_tool_dict is pre-seeded because run_one_function auto-loads all 2,236 tools when it
    is empty, which no unit test can afford. The unknown-tool path returns without touching
    the network, which is exactly the "completes normally with an empty record set" case.
    """
    http_record.install_invocation_scope(unwrapped_tooluniverse)
    tu = unwrapped_tooluniverse()
    tu.all_tool_dict = {"placeholder": {"name": "placeholder"}}

    result = tu.run_one_function({"name": "definitely_not_a_tool", "arguments": {}})

    assert result["status"] == "error"
    assert http_record.last_invocation_records() == ()
