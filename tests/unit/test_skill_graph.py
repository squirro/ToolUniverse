"""Skills as a process graph: `next_step` is pure. Given the graph and the steps already
done it returns the one step to run now, with its tool calls and their arguments."""

import sys
from functools import lru_cache
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from tooluniverse.skill_graph import (  # noqa: E402
    GRAPHS_DIR,
    SkillGraphError,
    graph_directive,
    load_graph,
    next_step,
    skipped_gates,
    unbound_gates,
    undeclared_tables,
    unmade_products,
)

pytestmark = pytest.mark.unit

SHIPPED = sorted(p.stem for p in GRAPHS_DIR.glob("*.yaml"))

GRAPH = {
    "skill": "demo",
    "inputs": ["drug_name"],
    "steps": [
        {"id": "resolve", "label": "Resolve the drug",
         "calls": [{"tool": "OpenTargets_get_drug_chembId_by_generic_name",
                    "arguments": {"drugName": "{drug_name}"}}],
         "produces": ["chembl_id"]},
        {"id": "profile", "label": "Count reactions", "requires": ["resolve"],
         "calls": [{"tool": "FAERS_count_reactions_by_drug_event",
                    "arguments": {"medicinalproduct": "{drug_name}"}}],
         "produces": ["top_aes"]},
        {"id": "stratify", "label": "Stratify strong signals",
         "requires": ["profile"], "when": "strong_signal",
         "calls": [{"tool": "FAERS_stratify_by_demographics",
                    "arguments": {"drug_name": "{drug_name}"}}]},
        {"id": "report", "label": "Write the report", "requires": ["profile"],
         "calls": []},
    ],
}


def _step(done=(), facts=None):
    return next_step(GRAPH, done=list(done), facts=facts or {"drug_name": "cisplatin"})


# --- ordering, dependencies and gateways ------------------------------------

@pytest.mark.parametrize("done, facts, expected", [
    ((), None, "resolve"),                          # `profile` requires `resolve`, so it cannot come first
    (("resolve",), None, "profile"),
    (("resolve", "profile"), None, "report"),       # no strong signal: stratification is not demanded
    (("resolve", "profile"), {"drug_name": "cisplatin", "strong_signal": True}, "stratify"),
    (("resolve", "profile", "report"), None, None),  # the unmet gateway does not block the end
])
def test_the_step_offered_is_the_one_the_dependencies_and_the_gateways_allow(done, facts, expected):
    step = _step(done, facts)
    assert (step["id"] if step else None) == expected


# --- what the agent receives -------------------------------------------------

def test_the_step_carries_its_tool_calls_with_arguments_filled_in():
    """The agent is handed the call, not asked to compose it."""
    call = _step()["calls"][0]
    assert call["tool"] == "OpenTargets_get_drug_chembId_by_generic_name"
    assert call["arguments"] == {"drugName": "cisplatin"}


def test_a_missing_input_is_named_rather_than_templated_into_the_call():
    with pytest.raises(SkillGraphError) as exc:
        next_step(GRAPH, done=[], facts={})
    assert "drug_name" in str(exc.value)


def test_the_step_says_what_it_produces_so_the_agent_knows_what_to_extract():
    assert _step()["produces"] == ["chembl_id"]


# --- loops -------------------------------------------------------------------
# One call per item, composed by the graph: a placeholder the agent has to fill is
# exactly the guesswork this design removes.

LOOP_GRAPH = {
    "skill": "loopy",
    "inputs": ["drug_name"],
    "steps": [
        {"id": "profile", "calls": [], "produces": ["top_aes"]},
        {"id": "signals", "requires": ["profile"],
         "for_each": "top_aes", "as": "adverse_event",
         "calls": [{"tool": "FAERS_calculate_disproportionality",
                    "arguments": {"drug_name": "{drug_name}",
                                  "adverse_event": "{adverse_event}"}}]},
    ],
}


def test_a_loop_step_emits_one_call_per_item():
    step = next_step(LOOP_GRAPH, done=["profile"],
                     facts={"drug_name": "cisplatin",
                            "top_aes": ["nephropathy toxic", "acute renal failure"]})
    events = [c["arguments"]["adverse_event"] for c in step["calls"]]
    assert events == ["nephropathy toxic", "acute renal failure"]
    assert all(c["arguments"]["drug_name"] == "cisplatin" for c in step["calls"])


def test_a_loop_step_says_which_list_it_needs_when_it_is_missing():
    with pytest.raises(SkillGraphError) as exc:
        next_step(LOOP_GRAPH, done=["profile"], facts={"drug_name": "cisplatin"})
    assert "top_aes" in str(exc.value)


def test_a_loop_over_an_empty_list_is_not_a_step_to_run():
    """No reactions came back, so the procedure moves on rather than demand an impossible call."""
    assert next_step(LOOP_GRAPH, done=["profile"],
                     facts={"drug_name": "cisplatin", "top_aes": []}) is None


def test_a_loop_over_an_empty_list_still_lets_the_steps_after_it_run():
    """An empty loop is vacuously complete, not a dead end for everything downstream."""
    graph = {**LOOP_GRAPH, "steps": LOOP_GRAPH["steps"] + [
        {"id": "assessment", "requires": ["signals"], "calls": []}]}

    step = next_step(graph, done=["profile"],
                     facts={"drug_name": "cisplatin", "top_aes": []})

    assert step is not None and step["id"] == "assessment"
    assert step["remaining"] == 0


# --- telling the agent a graph exists ----------------------------------------
# A graph nobody is told about changes nothing: get_skill still serves the prose
# phases, and the agent plans from them exactly as before.

def test_a_graphed_skill_is_told_to_run_the_graph():
    text = graph_directive("adverse-event-detection")
    assert "next_skill_step" in text
    assert "adverse-event-detection" in text


def test_a_skill_without_a_graph_gets_no_directive():
    assert graph_directive("disease-research") == ""


def test_the_directive_demotes_the_prose_phases_to_reference():
    """Two sets of instructions that disagree is worse than either alone."""
    text = graph_directive("adverse-event-detection").lower()
    assert "reference" in text or "do not plan" in text


# --- loading -----------------------------------------------------------------

def test_a_graph_loads_by_skill_name():
    graph = load_graph("adverse-event-detection")
    assert graph["skill"] == "adverse-event-detection"
    assert graph["steps"], graph


def test_an_unknown_skill_has_no_graph():
    with pytest.raises(SkillGraphError):
        load_graph("no-such-skill")


def test_every_call_in_a_shipped_graph_names_a_tool():
    """A call with no tool would reintroduce the invented-tool-name defect."""
    for step in load_graph("adverse-event-detection")["steps"]:
        for call in step.get("calls", []):
            assert call.get("tool"), step


@lru_cache(maxsize=None)
def _registry() -> dict:
    """tool name -> declared parameter properties, from the shipped registry."""
    import glob
    import json
    out: dict[str, dict] = {}
    root = Path(__file__).resolve().parents[2] / "src" / "tooluniverse" / "data"
    for path in glob.glob(str(root / "*.json")):
        try:
            with open(path) as handle:
                loaded = json.load(handle)
        except (ValueError, OSError):
            continue
        if isinstance(loaded, list):
            out.update({t["name"]: (t.get("parameter") or {}).get("properties") or {}
                        for t in loaded if isinstance(t, dict) and "name" in t})
    return out


@pytest.mark.parametrize("skill", SHIPPED)
def test_every_shipped_graph_calls_only_registered_tools(skill):
    """A graph that guesses a tool name is worse than the prose: the agent is told to trust it."""
    registry = _registry()
    assert registry, "no tools found in the registry"
    unknown = sorted({call["tool"] for step in load_graph(skill)["steps"]
                      for call in step.get("calls", [])
                      if call["tool"] not in registry})
    assert not unknown, f"{skill} names tools the registry does not hold: {unknown}"


@pytest.mark.parametrize("skill", SHIPPED)
def test_a_graph_only_passes_arguments_the_tool_declares(skill):
    """A misspelled parameter is baked into the composed call and repeats on every run."""
    declared = _registry()
    wrong = []
    for step in load_graph(skill)["steps"]:
        for call in step.get("calls", []):
            props = declared.get(call["tool"])
            if not props:
                continue
            wrong += [f"{step['id']}: {call['tool']}({name})"
                      for name in (call.get("arguments") or {}) if name not in props]
    assert not wrong, wrong


def test_every_step_of_a_shipped_graph_is_reachable():
    """A step whose dependency is never satisfiable would silently drop a phase."""
    graph = load_graph("adverse-event-detection")
    ids = {s["id"] for s in graph["steps"]}
    for step in graph["steps"]:
        missing = [d for d in step.get("requires", []) if d not in ids]
        assert not missing, f"{step['id']} requires unknown steps: {missing}"


@pytest.mark.parametrize("skill", SHIPPED)
def test_a_judged_fact_is_one_the_step_says_it_produces(skill):
    """A judged name outside `produces` is a declaration nobody reads downstream."""
    stray = [f"{step['id']}: {name}" for step in load_graph(skill)["steps"]
             for name in step.get("judge", [])
             if name not in step.get("produces", [])]
    assert not stray, stray


def test_rare_disease_diagnosis_declares_its_judgement_points():
    """Phase 0 has no tool at all; the process says what comes from the model."""
    graph = load_graph("rare-disease-diagnosis")
    judged = {s["id"]: s.get("judge") for s in graph["steps"] if s.get("judge")}
    # `genes` is looked up per resolved candidate; the discriminating pair is computed
    # from HPO disease counts, and the judge is reached only when the counts tie.
    assert judged == {
        "hypothesis": ["primary_keyword", "working_hypothesis", "discriminating_features"],
        "discriminating": ["discriminating_hpo_ids"],
        "keyword_search": ["top_candidate"],
    }
    phenotypes = next(s for s in graph["steps"] if s["id"] == "phenotypes")
    assert phenotypes["collect"]["hpo_ids"] == {"path": "data.items[].id", "match": "^HP:"}


def test_a_step_tells_the_model_driven_caller_which_names_it_must_judge():
    graph = {"skill": "j", "inputs": [], "steps": [
        {"id": "hypothesis", "calls": [], "produces": ["keyword"], "judge": ["keyword"]}]}
    assert next_step(graph, done=[], facts={})["judge"] == ["keyword"]


def test_with_temporal_the_directive_points_at_run_skill_and_forbids_self_execution():
    text = graph_directive("clinical-data-integration", server_runs=True)
    assert "run_skill(" in text and "continue_skill(" in text
    # the model-driven loop is named only as what to do when run_skill errors
    assert "next_skill_step" not in text.partition("answers `error`")[0]
    assert "Do not call `execute_tool`" in text
    # and without Temporal the model-driven loop is still the instruction
    assert "next_skill_step" in graph_directive("clinical-data-integration")


def test_rare_disease_diagnosis_carries_report_guidance_and_notes_on_every_step():
    """A bundle that carries data without the author's rules is written up worse than prose."""
    graph = load_graph("rare-disease-diagnosis")
    assert graph["optional_inputs"] == ["variant_id", "age_years"]
    assert [s["id"] for s in graph["steps"] if not s.get("notes")] == []
    report = graph["report"]
    # The writer must be told which facts the model supplied, where genes may come from,
    # how to cite, and what the Limitations section is built from.
    for needle in ("working_hypothesis", "discriminating_hpo_ids", "top_candidate",
                   "orphanet_gene_rows", "opentargets_rows", "optimuskg_genes",
                   "hpo.jax.org", "orpha.net", "platform.opentargets.org", "europepmc.org",
                   "failures", "blocked", "unresolved", "No variant data provided",
                   # the discriminating-tests line: what separates the top two
                   "same disease family", "inheritance", "clinical reasoning",
                   "disease_inheritance", "ranked_rows", "prevalence"):
        assert needle in report, needle
    assert "no tool in this run returned it" not in report     # inheritance now comes from a row
    assert "supplied by the model" in report and "genes" not in report.split("supplied by the model")[0].rsplit(".", 1)[-1]


def test_a_collected_table_the_process_does_not_declare_is_named():
    """No silent default: the author says whether the agent gets a table whole or described."""
    process = {"skill": "d", "inputs": [], "tables": {"prr_rows": "fact"}, "steps": [
        {"id": "signals", "calls": [], "collect": {"prr_rows": {"path": "data.rows"}}},
        {"id": "literature", "calls": [], "collect": {"papers": {"path": "data.articles"}}}]}

    assert undeclared_tables(process) == ["papers"]


@pytest.mark.parametrize("skill", SHIPPED)
def test_every_shipped_process_declares_each_table_it_collects(skill):
    assert undeclared_tables(load_graph(skill)) == []


def test_a_process_that_collects_an_undeclared_table_is_refused_by_name(tmp_path):
    (tmp_path / "leaky.yaml").write_text(
        "skill: leaky\ninputs: []\nsteps:\n"
        "  - id: literature\n    calls: []\n"
        "    collect:\n      papers: {path: data.articles}\n")

    with pytest.raises(SkillGraphError, match="papers"):
        load_graph("leaky", graphs_dir=tmp_path)


def test_the_directive_tells_the_agent_to_write_from_the_handover_and_to_fetch_the_rest():
    text = graph_directive("clinical-data-integration", server_runs=True)

    assert "`handover`" in text and "fetch_run_data(" in text
    assert "bundle" not in text


def test_a_skipped_gate_says_whether_its_condition_was_decided():
    graph = {"skill": "demo", "inputs": ["drug_name"], "steps": [
        {"id": "signals", "calls": []},
        {"id": "stratify", "requires": ["signals"], "when": "strong_signal", "calls": []},
    ]}

    rejected = skipped_gates(graph, ["signals"], {"strong_signal": False})
    never = skipped_gates(graph, ["signals"], {})

    assert rejected[0]["decided"] is True
    assert never[0]["decided"] is False


# --- a gate and a declared product must each have something that can make them ----

def _write(tmp_path, name, steps, extra=""):
    (tmp_path / f"{name}.yaml").write_text(
        f"skill: {name}\ninputs: [drug_name]\n{extra}steps:\n{steps}")


def test_a_gate_on_a_name_nothing_can_bind_is_refused_by_name(tmp_path):
    _write(tmp_path, "shut", (
        "  - id: signals\n    calls: []\n"
        "  - id: comparative\n    requires: [signals]\n    when: comparator\n    calls: []\n"))

    with pytest.raises(SkillGraphError, match="comparator"):
        load_graph("shut", graphs_dir=tmp_path)


@pytest.mark.parametrize("extra, steps", [
    ("optional_inputs: [comparator]\n", ""),
    ("constants:\n  comparator: carboplatin\n", ""),
    ("", "    extract: {comparator: data.name}\n"),
    ("", "    judge: [comparator]\n    produces: [comparator]\n"),
    ("", "    delegate:\n      - tool: web_search\n        arguments: {query: '{drug_name}'}\n"
         "    produces: [comparator]\n"),
], ids=["optional-input", "constant", "extract", "judge", "delegate"])
def test_a_gate_opens_on_an_input_a_constant_or_a_name_a_step_makes(tmp_path, extra, steps):
    _write(tmp_path, "open", (
        "  - id: choose\n    calls: []\n" + steps
        + "  - id: comparative\n    requires: [choose]\n    when: comparator\n    calls: []\n"), extra)

    assert load_graph("open", graphs_dir=tmp_path)["skill"] == "open"


def test_a_gate_opens_on_the_term_list_a_judged_mapping_makes(tmp_path):
    _write(tmp_path, "mapped", (
        "  - id: terms\n    calls: []\n    judge: [chosen]\n    produces: [chosen]\n"
        "    mapping:\n      chosen: {of: drug_name, onto: {rows: rows, field: term}}\n"
        "  - id: loop\n    requires: [terms]\n    when: chosen_terms\n    calls: []\n"))

    assert load_graph("mapped", graphs_dir=tmp_path)["skill"] == "mapped"


def test_a_declared_product_no_rule_makes_is_refused_by_name(tmp_path):
    _write(tmp_path, "promise", (
        "  - id: identity\n    calls: []\n"
        "    extract: {setid: data.0.setid}\n    produces: [setid, approval_history]\n"))

    with pytest.raises(SkillGraphError, match="approval_history"):
        load_graph("promise", graphs_dir=tmp_path)
    graph = yaml.safe_load((tmp_path / "promise.yaml").read_text())
    assert unmade_products(graph) == ["identity: approval_history"]


@pytest.mark.parametrize("rules", [
    "    extract: {made: data.x}\n",
    "    collect: {made: {path: data}}\n",
    "    combine: {made: {union: [a, b]}}\n",
    "    compute: {made: {op: sum, of: [a]}}\n",
    "    derive: {made: {from: rows, field: x, op: '>=', value: 1}}\n",
    "    judge: [made]\n",
    "    delegate:\n      - tool: web_search\n        arguments: {query: '{drug_name}'}\n",
], ids=["extract", "collect", "combine", "compute", "derive", "judge", "delegate"])
def test_a_declared_product_is_made_by_one_of_the_seven_rules(tmp_path, rules):
    _write(tmp_path, "made", "  - id: step\n    calls: []\n" + rules + "    produces: [made]\n",
           "tables: {made: fact}\n")

    assert load_graph("made", graphs_dir=tmp_path)["skill"] == "made"


def test_a_product_made_by_another_step_is_still_refused(tmp_path):
    """`produces` is what this step makes; a name another step extracts is not this step's."""
    _write(tmp_path, "elsewhere", (
        "  - id: a\n    calls: []\n    extract: {setid: data.0.setid}\n    produces: [setid]\n"
        "  - id: b\n    requires: [a]\n    calls: []\n    produces: [setid]\n"))

    with pytest.raises(SkillGraphError, match="setid"):
        load_graph("elsewhere", graphs_dir=tmp_path)


@pytest.mark.parametrize("skill", SHIPPED)
def test_every_shipped_graph_passes_both_guards(skill):
    graph = yaml.safe_load((GRAPHS_DIR / f"{skill}.yaml").read_text(encoding="utf-8"))

    assert unbound_gates(graph) == []
    assert unmade_products(graph) == []


@pytest.mark.parametrize("facts, expected", [
    ({"target": "EGFR", "disease": "lung cancer"}, {"q": "EGFR", "condition": "lung cancer"}),
    ({"target": "EGFR"}, {"q": "EGFR"}),
    ({"target": "EGFR", "disease": None}, {"q": "EGFR"}),
    ({"target": "EGFR", "disease": ""}, {"q": "EGFR"}),
])
def test_an_optional_argument_is_sent_only_when_the_run_holds_its_value(facts, expected):
    """An absent value leaves the argument out; it never travels as null or as a placeholder."""
    graph = {"skill": "demo", "steps": [{"id": "search", "calls": [
        {"tool": "T", "arguments": {"q": "{target}"},
         "optional_arguments": {"condition": "{disease}"}}]}]}

    assert next_step(graph, done=[], facts=facts)["calls"] == [{"tool": "T", "arguments": expected}]


def test_the_server_run_directive_says_what_to_do_when_run_skill_errors():
    """The run can still fail at turn time; the body must not leave the agent with nothing."""
    text = graph_directive("clinical-data-integration", server_runs=True)
    before, _, after = text.partition("answers `error`")

    assert after, "the directive names no `error` answer"
    assert "next_skill_step(" in after and "tell the user" in after.lower()
    assert "next_skill_step" not in before          # the fallback is only for an error
