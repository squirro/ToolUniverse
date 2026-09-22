"""Reading one agent turn off the wire. No cluster, no network: bytes in, a result out."""

import json
import sys
from pathlib import Path

import pytest

DEPLOY = Path(__file__).resolve().parents[2] / "deploy"
sys.path.insert(0, str(DEPLOY))

from skill_audit.squirro_chat import lines_of, parse_sse  # noqa: E402

pytestmark = pytest.mark.unit

# A PubMed title carried U+2028 into a tool output; the turn then read as dead.
TITLE = "Cisplatin ototoxicity\u2028in children"


def _stream(result: dict) -> bytes:
    return ("event: progress\ndata: {}\n\n"
            "event: result\ndata: " + json.dumps(result, ensure_ascii=False) + "\n\n"
            ).encode("utf-8")


def test_a_line_separator_inside_a_tool_output_does_not_cut_the_result_frame():
    result = {"output": "done", "actions": [{"tool_name": "PubMed", "content": TITLE}]}

    parsed, error = parse_sse(lines_of([_stream(result)]))

    assert error == ""
    assert parsed == result


def test_a_frame_split_across_chunks_is_read_whole():
    result = {"output": TITLE}
    wire = _stream(result)
    cut = wire.index("\u2028".encode("utf-8")) + 1      # mid-character, mid-frame

    parsed, _ = parse_sse(lines_of([wire[:cut], wire[cut:]]))

    assert parsed == result


def test_a_turn_without_a_result_frame_keeps_its_raw_stream(tmp_path):
    """The next dead-looking turn must be readable: was it the agent, or was it us?"""
    from skill_audit.squirro_chat import turn_from

    wire = b"event: progress\ndata: {\"step\": 1}\n\nevent: resu"

    turn = turn_from([wire], http_status=200, dump_dir=tmp_path)

    (saved,) = list(tmp_path.iterdir())
    assert turn.error.startswith("missing_result") and str(saved) in turn.error
    assert saved.read_bytes() == wire


def test_the_conversation_id_travels_inside_runtime_config_so_tools_can_see_it():
    """The streaming route builds the agent's runtime config from the body's `runtime_config`
    only; a top-level `conversation_id` never reaches a tool's placeholder. Measured 2026-09-22:
    the agent logged conversation_id=None on every API-driven turn, and stage_run_data could
    not find the conversation's code container."""
    from skill_audit.squirro_chat import payload_for

    payload = payload_for(agent_id="A", instruction="q", conversation_id="conv-1",
                          refresh_token="r", cluster="https://c", project_id="p")

    assert payload["conversation_id"] == "conv-1"
    assert payload["runtime_config"]["conversation_id"] == "conv-1"
    assert payload["runtime_config"]["squirro_project_id"] == "p"


def test_a_turn_with_a_result_frame_is_returned_and_nothing_is_saved(tmp_path):
    from skill_audit.squirro_chat import turn_from

    result = {"answer": "PRR 54.766", "actions": [{"tool_name": "run_skill"}]}

    turn = turn_from([_stream(result)], http_status=200, dump_dir=tmp_path)

    assert (turn.answer, turn.calls, turn.error) == ("PRR 54.766", ["run_skill"], None)
    assert list(tmp_path.iterdir()) == []
