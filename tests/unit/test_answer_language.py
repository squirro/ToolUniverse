"""The answer is written in the language of the question (DSR-811).

Two of four English Skill Process turns on sr-dev were answered in German. The
served bodies said only "respond in the user's language", which the model can read
from anything but the question. The rule rides on the surfaces read while the
answer is written: the served body, the `finished` reply and submit_report.
"""
import re
import shutil
from pathlib import Path

import pytest

from tooluniverse.skill_run_client import progress
from tooluniverse.skill_serving import load_skill_body

pytestmark = pytest.mark.unit

DEPLOY = Path(__file__).resolve().parents[2] / "deploy"
RULE = re.compile(r"language of the (user's )?question", re.IGNORECASE)


@pytest.fixture
def served(tmp_path):
    # As the Dockerfile serves it: persona-<name>.md -> <name>.md.
    shutil.copy(DEPLOY / "persona-clinical-data-integration.md",
                tmp_path / "clinical-data-integration.md")
    return tmp_path


def test_the_served_body_fixes_the_answer_language(served):
    body = load_skill_body(served, "clinical-data-integration")
    assert "respond in the user's language" in body   # the ambiguous line it overrides
    assert RULE.search(body), body[-1500:]


def test_the_finished_reply_fixes_the_answer_language():
    finished = progress("r1", {"finished": True, "done": []}, handover={"skill": "demo"})
    assert RULE.search(finished["next"]), finished["next"]


def test_submit_report_description_fixes_the_answer_language():
    from tooluniverse.smcp import SMCP

    registered = {}

    class _Host:
        def tool(self, **_):
            def register(fn):
                registered[fn.__name__] = fn.__doc__ or ""
                return fn
            return register

    SMCP._add_skill_run_tools(_Host(), "localhost:7233")
    assert RULE.search(registered["submit_report"]), registered["submit_report"]


def test_a_question_the_run_asks_says_its_reasons_follow_the_question_language():
    """The reasons go into the Run Record, which a reader may open."""
    from tooluniverse.skill_run_client import progress

    out = progress("skill-demo-1", {"waiting_for": {"kind": "judge", "step": "s", "wants": ["x_reason"]},
                                    "step_id": "s", "done": []})

    assert out["status"] == "waiting"
    assert "language of the user's question" in out.get("next", "")


def test_the_rule_names_the_search_query_trap_on_both_surfaces():
    """Live: an English question, a German search query the agent chose, then German reasons.
    The rule has to say that a search query's language does not carry over."""
    from tooluniverse.skill_run_client import progress
    from tooluniverse.skill_serving import CITATION_CONTRACT

    waiting = progress("r", {"waiting_for": {"kind": "judge", "wants": ["x_reason"]}, "done": []})
    for text in (CITATION_CONTRACT, waiting["next"]):
        assert "search quer" in text and "language of the user's question" in text, text
    # Live, a German query was followed by German reasons and a partly German answer every time;
    # the body must not license a query in another language.
    body = " ".join(CITATION_CONTRACT.split())
    assert "may be in another language" not in body
    assert "Write your search queries in the language of the user's question" in body
