"""Five of the eleven criteria measured by script, and the spread between two runs of one arm.

A judge's opinion costs a turn and varies; a script over saved traces costs nothing and
gives the same number every time. Each pre-flight check comes from a real run failure.
"""

import sys
from pathlib import Path

import pytest

DEPLOY = Path(__file__).resolve().parents[2] / "deploy"
sys.path.insert(0, str(DEPLOY))

from skill_audit.criteria import (  # noqa: E402
    WEB_ARM_LIMIT,
    aggregate,
    citations_resolve,
    consistency,
    cost,
    preflight,
    quantities,
    spread,
    traceability,
)

pytestmark = pytest.mark.unit

RUN_A = ("Signals: OTOTOXICITY (PRR 54.766), NEPHROPATHY TOXIC (PRR 17.811), DEAFNESS (PRR 11.7). "
         "The label cites 866 trials.")
RUN_B = ("Signals: OTOTOXICITY (PRR 54.77), NEPHROPATHY TOXIC (PRR 17.811), TINNITUS (PRR 9.2). "
         "The label cites 866 trials and 2,078 papers.")


# --- 1. number traceability ----------------------------------------------------------------

def test_traceability_is_the_share_of_stated_numbers_found_in_a_stored_row():
    received = '{"term": "OTOTOXICITY", "prr": 54.766} {"term": "NEPHROPATHY TOXIC", "prr": 17.8112} 866'

    measured = traceability(RUN_A, received)

    assert measured["stated"] == ["54.766", "17.811", "11.7", "866"]
    assert measured["vouched"] == ["54.766", "17.811", "866"], "17.8112 rounds to 17.811"
    assert measured["share"] == 0.75


# --- 2. variation in numbers: the same quantity in two runs -------------------------------

def test_a_stated_number_is_keyed_by_its_term_and_its_label():
    assert quantities(RUN_A) == {"OTOTOXICITY PRR": 54.766, "NEPHROPATHY TOXIC PRR": 17.811,
                                 "DEAFNESS PRR": 11.7}


def test_the_spread_between_two_runs_counts_differences_and_quantities_stated_once():
    out = spread(RUN_A, RUN_B, judged=(20.7, 17.5))

    assert out["differences"] == {"OTOTOXICITY PRR": 0.004, "NEPHROPATHY TOXIC PRR": 0.0}
    assert out["median_difference"] == 0.002
    assert sorted(out["stated_in_one_run_only"]) == ["DEAFNESS PRR", "TINNITUS PRR"]
    assert out["judged_difference"] == 3.2


# --- 3. consistency of the conclusion ------------------------------------------------------

def test_the_conclusion_is_consistent_when_the_top_signal_is_the_same_in_both_runs():
    assert consistency(RUN_A, RUN_B) == {"top": ["OTOTOXICITY", "OTOTOXICITY"], "same": True,
                                         "top3_overlap": 2 / 4}
    assert consistency(RUN_A, "Signals: DEAFNESS (PRR 99.0), OTOTOXICITY (PRR 54.766).")["same"] is False


# --- 4. citations resolve -----------------------------------------------------------------

def test_a_citation_resolves_when_the_page_opens_and_holds_the_statements_number():
    answer = ("Ototoxicity PRR was 80.58 in 2017–2021.[^1^] Nephrotoxicity is dose-related.[^2^]\n\n"
              "[^1^]: https://example.org/faers-study\n[^2^]: https://example.org/gone\n")
    pages = {"https://example.org/faers-study": "The PRR for ototoxicity was 80.58 (2017-2021)."}

    out = citations_resolve(answer, fetch_text=lambda url: pages.get(url))

    assert out == [
        {"url": "https://example.org/faers-study", "opens": True, "numbers": ["80.58", "2017", "2021"],
         "contains_statement": True},
        {"url": "https://example.org/gone", "opens": False, "numbers": [], "contains_statement": False},
    ]


# --- 5. cost -------------------------------------------------------------------------------

def test_cost_reports_seconds_and_says_when_tokens_are_not_exposed():
    out = cost({"answer": RUN_A, "seconds": 435.4})

    assert out["seconds"] == 435.4 and out["answer_chars"] == len(RUN_A)
    assert out["tokens"] is None and "not exposed" in out["note"]


# --- the aggregation: one line per arm for totals, one for numbers ------------------------

def test_the_aggregation_compares_the_spread_of_the_two_arms_per_question():
    rows = [
        {"question": "q1", "arm": "modelled", "spread": {"judged_difference": 1.0, "median_difference": 0.0, "stated_in_one_run_only": []}},
        {"question": "q1", "arm": "web", "spread": {"judged_difference": 4.0, "median_difference": 9.0, "stated_in_one_run_only": ["X PRR"]}},
        {"question": "q2", "arm": "modelled", "spread": {"judged_difference": 2.0, "median_difference": 3.0, "stated_in_one_run_only": []}},
        {"question": "q2", "arm": "web", "spread": {"judged_difference": 1.0, "median_difference": 2.0, "stated_in_one_run_only": ["Y PRR", "Z PRR"]}},
    ]

    lines = aggregate(rows)

    assert lines["totals"] == ["modelled: median judged difference 1.5; narrower in 1 of 2 questions",
                               "web: median judged difference 2.5; narrower in 1 of 2 questions"]
    assert lines["numbers"] == ["modelled: median number difference 1.5; narrower in 1 of 2 questions; 0 quantities stated in one run only",
                                "web: median number difference 5.5; narrower in 1 of 2 questions; 3 quantities stated in one run only"]
    assert lines["limit"] == WEB_ARM_LIMIT and "Exa" in WEB_ARM_LIMIT and "internal document search" in WEB_ARM_LIMIT


# --- the pre-flight: four checks, each from a real failure --------------------------------

AGENTS = {
    "web": {"id": "w", "name": "Web", "extra_runtime_config": {"sqgpt_config_suffix": ".gpt45"},
            "toolkit": {"tools": [{"custom_name": "exa_web_search", "enabled": True},
                                  {"custom_name": "openai_web_search", "enabled": True},
                                  {"custom_name": "squirro_retriever", "enabled": True}]}},
    "modelled": {"id": "m", "name": "TU", "extra_runtime_config": {"max_agent_iterations": 60},
                 "toolkit": {"tools": []}},
}
GOOD_TURN = {"actions": [
    {"tool_name": "exa_web_search", "content": '{"output": "see https://a.org/x"}'},
    {"tool_name": "openai_web_search", "content": '{"output": "([b.org](https://b.org/y))"}'},
]}


def test_the_preflight_passes_when_the_models_match_every_web_tool_ran_with_links_and_the_log_is_clean():
    same = {**AGENTS, "modelled": {**AGENTS["modelled"], "extra_runtime_config": {"sqgpt_config_suffix": ".gpt45"}}}

    assert preflight(same, GOOD_TURN, log_lines=["GENAI(stream) success=True"]) == []


def test_the_preflight_names_the_two_model_configurations_when_they_differ():
    (failure,) = [f for f in preflight(AGENTS, GOOD_TURN, log_lines=[]) if "model" in f]

    assert ".gpt45" in failure and "project default" in failure


def test_the_preflight_fails_a_web_tool_that_is_enabled_but_never_called_in_the_live_turn():
    turn = {"actions": GOOD_TURN["actions"][:1]}

    failures = preflight(AGENTS, turn, log_lines=[])

    assert any("openai_web_search" in f and "not called" in f for f in failures)


def test_the_preflight_fails_a_web_call_that_gave_no_links():
    turn = {"actions": [{"tool_name": "exa_web_search", "content": '{"output": "nothing"}'},
                        GOOD_TURN["actions"][1]]}

    assert any("exa_web_search" in f and "no link" in f for f in preflight(AGENTS, turn, log_lines=[]))


def test_the_preflight_fails_on_a_plugin_that_failed_to_load():
    log = ["... Failed to create plugin tool 'Openai Web Search': missing field ..."]

    assert any("Failed to create plugin tool" in f for f in preflight(AGENTS, GOOD_TURN, log_lines=log))


def test_a_tool_called_in_any_of_the_per_tool_probe_turns_counts_as_present():
    """One question cannot make an agent use six tools; the live probe asks for each by name."""
    same = {**AGENTS, "modelled": {**AGENTS["modelled"], "extra_runtime_config": {"sqgpt_config_suffix": ".gpt45"}}}
    turns = [{"actions": GOOD_TURN["actions"][:1]}, {"actions": GOOD_TURN["actions"][1:]}]

    assert preflight(same, turns, log_lines=[]) == []


def test_an_unreadable_genai_log_is_a_failure_not_a_pass():
    same = {**AGENTS, "modelled": {**AGENTS["modelled"], "extra_runtime_config": {"sqgpt_config_suffix": ".gpt45"}}}

    (failure,) = preflight(same, GOOD_TURN, log_lines=None)

    assert "could not be read" in failure


def test_the_limit_sentence_names_the_web_tool_families_the_arm_actually_has():
    from skill_audit.criteria import web_arm_limit

    assert "Exa and Perplexity;" in web_arm_limit(["exa_web_search", "Perplexity_web_Search_API"])
    assert "Exa, Perplexity and OpenAI web search;" in web_arm_limit(["exa_web_answer", "perplexity_x", "openai_web_search"])
    assert "internal document search" in web_arm_limit([])
