"""The FAERS signal table travels to the writer as rows, and the literature search is
one query per flagged reaction. Parallel lists let a footnote be mis-indexed; a row cannot.
"""
import json
import tempfile
from pathlib import Path

import pytest

from tooluniverse.skill_graph import GRAPHS_DIR, load_graph
from tooluniverse.skill_runner import SkillRunner, _COMPUTE_OPS, absorb, loop_items, source_total


def _records():
    return tempfile.mkdtemp(prefix="working-records-")

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
RECORDED_COUNTS = json.loads((FIXTURES / "openfda" / "faers_count_reactions_2026-09-24.json").read_text())
# The recorded list's first twelve reactions once the process sets its noise terms aside.
TERMS = ["NAUSEA", "PLATELET COUNT DECREASED", "COVID-19", "FATIGUE", "DIARRHOEA", "MALAISE",
         "ABDOMINAL PAIN", "VOMITING", "THROMBOCYTOPENIA", "DECREASED APPETITE",
         "METASTASES TO LIVER", "NEUROENDOCRINE TUMOUR"]
# PRR per term; a term not named here reports 1.0.
PRR = {"THROMBOCYTOPENIA": 7.5, "PLATELET COUNT DECREASED": 2.3, "NAUSEA": 1.1}


def _url(term):
    return f"https://api.fda.gov/drug/event.json?search={term.replace(' ', '+')}"


RECORDED_SEARCH = json.loads((Path(__file__).resolve().parents[1] / "fixtures" / "web"
                              / "exa_search_2026-09-21.json").read_text())


def _agent(question, web_pages=RECORDED_SEARCH["results"]):
    """The agent's side of a run: it does the compute step's arithmetic, as the task asks."""
    if "web_queries" in question["wants"]:
        # One query per subject, in the agent's own words -- the process holds no query text.
        # Nothing flagged and nothing requested means the combine wrote no fact at all.
        subjects = question["context"].get("web_subjects", [])
        return {"web_queries": [f"{subject} published risk estimate" for subject in subjects]}
    if "web_rows" in question["wants"]:
        # The agent runs each composed call and answers one row per page the tool returned.
        return {"web_rows": [
            {"query": call["arguments"]["query"], "title": page["title"], "url": page["url"],
             "source": page.get("author"), "date": page.get("publishedDate"), "content": page["text"]}
            for call in question["calls"] for page in web_pages]}
    if "prr_table" not in question["wants"]:
        return {name: ["stub"] for name in question["wants"]}
    arguments = question["calls"][0]["arguments"]
    rows, indication = arguments["rows"], arguments["indication_terms"]
    table = [{**row, "flagged": row.get("prr") is not None and row["prr"] >= 2}
             for row in sorted(rows, key=lambda r: (r.get("prr") is None, -(r.get("prr") or 0)))]
    flagged = [row["term"] for row in table if row["flagged"]]
    return {"prr_table": table,
            "flagged_aes": [t for t in flagged if t not in indication],
            "excluded_aes": [t for t in flagged if t in indication],
            "method": "computed without code"}


RECORDED_LABELS = json.loads((Path(__file__).resolve().parents[1] / "fixtures" / "openfda"
                              / "label_indications_2026-09-21.json").read_text())


def _indication_mapping(question, indication):
    """The agent reads the label's indication onto the FAERS terms the question offers."""
    listed = question["choices"]["indication_meddra"]
    return {"indication_meddra": [
        {"of": "the labelled indication", "term": t, "reason": "the treated disease or its course",
         "concept": ["disease", "treated"]} for t in indication if t in listed]}


RECORDED_PLACING = json.loads((Path(__file__).resolve().parents[1] / "fixtures" / "ols"
                               / "placing_probe_2026-09-21.json").read_text())


def _recorded_lookup(term):
    return RECORDED_PLACING.get(term, {})


READINGS = {"nephrotoxicity": (("ACUTE KIDNEY INJURY",), ["kidney", "renal"]),
            "secondary malignancy": (("MYELODYSPLASTIC SYNDROME", "ACUTE MYELOID LEUKAEMIA"),
                                     ["bone marrow", "neoplasm"])}


def _mapping(question):
    """The agent reads the question's word onto the source's list, as far down as it goes."""
    (word,) = question["context"]["requested_aes"]
    terms, concept = READINGS[word]
    listed = question["choices"]["requested_meddra"]
    return {"requested_meddra": [{"of": word, "term": t, "reason": "the injury the word names",
                                  "concept": concept} for t in terms if t in listed]}


def _drive(prr=PRR, graph=None, drug_name="lutetium Lu 177 dotatate", counts="LUTATHERA",
           requested_aes=None, indication=(), web_pages=RECORDED_SEARCH["results"], records=None):
    calls, asked = [], []

    def execute(tool, a):
        calls.append((tool, a))
        if tool == "DailyMed_search_spls":
            return {"data": [{"setid": "s1", "title": "LUTATHERA (lutetium Lu 177 dotatate)"}]}
        if tool == "FDA_get_indications_by_drug_name":
            return RECORDED_LABELS["metformin" if "metformin" in drug_name else "cisplatin"]
        if tool == "FAERS_count_reactions_by_drug_event":
            return RECORDED_COUNTS[counts]
        if tool == "FAERS_calculate_disproportionality":
            ae = a["adverse_event"]
            return {"data": {"metrics": {"PRR": {"value": prr.get(ae, 1.0)}}}, "source_url": _url(ae)}
        if tool == "FAERS_filter_serious_events":
            # the shape recorded from the live tool
            kind = a["seriousness_type"]
            return {"status": "success", "source_url": _url(kind), "data": {
                "drug_name": a["drug_name"], "seriousness_type": kind,
                "case_definition": {"resolved_field": "patient.drug.openfda.brand_name", "drug_report_total": 5683},
                "total_serious_events": {"hospitalization": 694, "death": 439}[kind],
                "top_serious_reactions": [{"reaction": "ILL-DEFINED DISORDER", "count": 100},
                                          {"reaction": "MALIGNANT NEOPLASM PROGRESSION", "count": 94}]
                if kind == "hospitalization" else [{"reaction": "DEATH", "count": 439}]}}
        if tool == "FAERS_stratify_by_demographics":
            return {"status": "success", "source_url": _url("sex"), "data": {
                "drug_name": a["drug_name"], "stratified_by": "sex", "total_reports": 1851,
                "case_definition": {"resolved_field": "patient.drug.openfda.brand_name", "drug_report_total": 5683},
                "stratification": [{"group": "Male", "count": 957, "percentage": 51.7},
                                   {"group": "Female", "count": 894, "percentage": 48.3}]}}
        if tool == "PubMed_search_articles":
            # the shape recorded from the live tool
            return {"status": "success",
                    "data": [{"pmid": "1", "title": "t", "pub_year": 2024, "doi_url": "d"}],
                    "metadata": {"count": 1, "total": 4120, "query": a["query"], "source": "PubMed"}}
        if tool == "search_clinical_trials":
            return {"data": {"total_count": 866, "studies": [
                {"NCT ID": "NCT1", "brief_title": "A", "overall_status": "COMPLETED", "phase": "PHASE3"},
                {"NCT ID": "NCT2", "brief_title": "B", "overall_status": "TERMINATED"}]}}
        return {}

    def agent(question):
        asked.append(question)
        if "requested_meddra" in question["wants"]:
            return _mapping(question)
        if "indication_meddra" in question["wants"]:
            return _indication_mapping(question, indication)
        return _agent(question, web_pages)

    runner = SkillRunner(graph or load_graph("clinical-data-integration"), execute=execute,
                         ask=agent, lookup=_recorded_lookup, records=records)
    inputs = {"drug_name": drug_name, **({"requested_aes": requested_aes} if requested_aes else {})}
    run_id = runner.start(inputs)["run_id"]
    for _ in range(100):
        if runner.advance(run_id)["finished"]:
            break
    else:
        raise AssertionError("the run did not finish")
    state = runner.state(run_id)
    state["handover"], state["records"], state["run_id"] = runner.handover(run_id), records, run_id
    return state, calls, asked


# --- rows, not lists ------------------------------------------------------------

def _prr(term, prr=PRR):
    return prr.get(term, 1.0)


def test_each_signal_row_carries_the_term_its_prr_its_flag_and_its_own_query_url():
    state, _, asked = _drive()
    table = state["facts"]["prr_table"]
    assert table[:3] == [
        {"term": "THROMBOCYTOPENIA", "prr": 7.5, "flagged": True, "url": _url("THROMBOCYTOPENIA")},
        {"term": "PLATELET COUNT DECREASED", "prr": 2.3, "flagged": True, "url": _url("PLATELET COUNT DECREASED")},
        {"term": "NAUSEA", "prr": 1.1, "flagged": False, "url": _url("NAUSEA")},
    ]
    assert sorted(r["term"] for r in table) == sorted(TERMS)
    assert all(r["url"] == _url(r["term"]) and r["flagged"] is (r["prr"] >= 2) for r in table)
    compute = [q for q in asked if q["step"] == "compute"]
    assert len(compute) == 1, "the agent does the arithmetic once; the check found nothing to re-ask"
    assert "problem" not in compute[0]


def test_the_signals_travel_as_rows_only_and_the_gateway_reads_the_rows():
    """A reaction without a PRR drops out of one parallel list and not the other."""
    state, _, _ = _drive()
    facts = state["facts"]
    assert facts["signal_aes"] == TERMS
    assert "prrs" not in facts and "prr_urls" not in facts
    assert [(r["term"], r["prr"], r["url"]) for r in facts["prr_rows"]] == [
        (t, _prr(t), _url(t)) for t in TERMS]
    assert facts["strong_signal"] is True


def test_seriousness_and_the_sex_split_reach_the_report_as_facts_tagged_by_their_call():
    """The rows travel as facts, each tagged with the call that made it."""
    state, calls, _ = _drive()
    facts = state["facts"]

    assert [(r["seriousness"], r["reaction"], r["count"]) for r in facts["serious_rows"]] == [
        ("hospitalization", "ILL-DEFINED DISORDER", 100),
        ("hospitalization", "MALIGNANT NEOPLASM PROGRESSION", 94),
        ("death", "DEATH", 439)]
    assert [(r["seriousness"], r["reports"], r["url"]) for r in facts["serious_totals"]] == [
        ("hospitalization", 694, _url("hospitalization")), ("death", 439, _url("death"))]
    assert facts["strong_signal"] is True
    assert [(r["group"], r["count"], r["percentage"]) for r in facts["sex_rows"]] == [
        ("Male", 957, 51.7), ("Female", 894, 48.3)]
    assert facts["sex_reports"] == 1851


# --- the question's words are read onto the source's terms, and the reading is shown ----

def test_a_requested_reaction_is_mapped_onto_faers_terms_before_any_loop_sees_it():
    """Reading the word onto the source's terms is judged: checked, placed, handed over."""
    state, calls, asked = _drive(prr={"ACUTE KIDNEY INJURY": 17.7}, requested_aes=["nephrotoxicity"])

    looped = [a["adverse_event"] for tool, a in calls if tool == "FAERS_calculate_disproportionality"]
    # far below the top twelve in the recorded list, the mapped term still leads
    assert looped == ["ACUTE KIDNEY INJURY"] + TERMS, "the mapped term leads; the word never reaches FAERS"
    (mapping_question,) = [q for q in asked if "requested_meddra" in q["wants"]]
    assert "term" in mapping_question["notes"] and "reason" in mapping_question["notes"]
    assert len(mapping_question["choices"]["requested_meddra"]) == 100, "the whole recorded list"
    (row,) = state["facts"]["requested_meddra"]
    assert (row["of"], row["term"], row["placing"]) == ("nephrotoxicity", "ACUTE KIDNEY INJURY", "placed")
    assert row["reason"] and row["under"]
    assert state["facts"]["signal_aes"] == ["ACUTE KIDNEY INJURY"] + TERMS


def test_without_a_requested_reaction_the_mapping_step_is_skipped_and_the_top_terms_drive_the_loop():
    state, calls, asked = _drive()
    assert [q for q in asked if "requested_meddra" in q["wants"]] == []
    assert "requested_meddra" not in state["facts"]
    assert state["facts"]["signal_aes"] == TERMS


# --- literature as a loop --------------------------------------------------------

def test_the_literature_loop_fans_over_exactly_the_flagged_reactions():
    state, calls, _ = _drive()
    queries = [a["query"] for tool, a in calls if tool == "PubMed_search_articles"]
    # Untagged on purpose: PubMed maps the INN to its substance record and the
    # reaction to its MeSH heading.
    assert queries == ["lutetium Lu 177 dotatate AND THROMBOCYTOPENIA",
                       "lutetium Lu 177 dotatate AND PLATELET COUNT DECREASED"]
    # One row for each paper, carrying its reaction and its own links: a paper without a
    # DOI cannot shift the DOI of the next one.
    assert state["facts"]["literature_rows"] == [
        {"reaction": reaction, "pmid": "1", "title": "t", "year": 2024, "doi": "d"}
        for reaction in ("THROMBOCYTOPENIA", "PLATELET COUNT DECREASED")]


def test_no_flagged_reaction_means_no_literature_search():
    state, calls, _ = _drive(prr={})
    assert [tool for tool, _ in calls if tool == "PubMed_search_articles"] == []
    assert state["facts"]["flagged_aes"] == []


# --- the two compute ops ---------------------------------------------------------

FLAGGABLE = [{"term": "a", "prr": 1.1}, {"term": "b", "prr": 7.5}, {"term": "c", "prr": 2.0}]
PLUCKABLE = [{"term": "b", "flagged": True}, {"term": "a", "flagged": False}, {"term": "c", "flagged": True}]
EXCLUDABLE = [{"term": "NEUROENDOCRINE TUMOUR", "flagged": True}, {"term": "MDS", "flagged": True},
              {"term": "METASTASES TO LIVER", "flagged": True}, {"term": "NAUSEA", "flagged": False}]


@pytest.mark.parametrize("op, rule, store, expected", [
    # flag sorts by the field and flags at the threshold
    ("flag", {"rows": "r", "field": "prr", "threshold": 2}, {"r": FLAGGABLE},
     [{"term": "b", "prr": 7.5, "flagged": True}, {"term": "c", "prr": 2.0, "flagged": True},
      {"term": "a", "prr": 1.1, "flagged": False}]),
    ("flag", {"rows": "r", "field": "prr", "threshold": 2}, {}, None),   # the rows never arrived
    # pluck takes one field from the rows that pass
    ("pluck", {"rows": "r", "field": "term", "where": "flagged"}, {"r": PLUCKABLE}, ["b", "c"]),
    ("pluck", {"rows": "r", "field": "term"}, {"r": PLUCKABLE}, ["b", "a", "c"]),
    ("pluck", {"rows": "r", "field": "term"}, {}, None),
    # the reported disease is set aside: pluck drops the rows its pattern matches
    ("pluck", {"rows": "r", "field": "term", "where": "flagged", "exclude_pattern": "TUMOU?R|METASTA"},
     {"r": EXCLUDABLE}, ["MDS"]),
])
def test_a_compute_op_reads_the_rows_it_names_and_is_unresolved_without_them(op, rule, store, expected):
    out = _COMPUTE_OPS[op](rule, store)

    assert out == expected and (out is None) == (expected is None)


# --- the loop item inside a longer template --------------------------------------

def test_the_loop_item_is_recovered_when_its_marker_sits_inside_a_longer_argument():
    spec = {"for_each": "flagged_aes", "as": "reaction",
            "calls": [{"tool": "PubMed_search_articles",
                       "arguments": {"query": "{drug_name}[Title/Abstract] AND {reaction}[Title/Abstract]"}}]}
    calls = [{"tool": "PubMed_search_articles",
              "arguments": {"query": "Lutathera[Title/Abstract] AND RENAL IMPAIRMENT[Title/Abstract]"}}]
    assert loop_items(spec, calls) == ["RENAL IMPAIRMENT"]


# --- compute rules resolve regardless of the order a store hands them back -------

def test_a_compute_that_reads_another_compute_resolves_whatever_the_declared_order():
    """The store hands the rules back alphabetically, so a rule can be reached first."""
    spec = {"id": "compute", "calls": [],
            "compute": {"flagged_aes": {"op": "pluck", "rows": "prr_table", "field": "term", "where": "flagged"},
                        "prr_table": {"op": "flag", "rows": "prr_rows", "field": "prr", "threshold": 2}}}
    out = absorb(spec, [], {"prr_rows": [{"term": "a", "prr": 7.5}, {"term": "b", "prr": 1.0}]})
    assert out["unresolved"] == []
    assert out["facts"]["flagged_aes"] == ["a"]


def test_the_process_read_back_from_the_store_still_searches_per_flagged_reaction():
    from rdflib import Graph
    from tooluniverse.skill_graph_bbo import from_bbo, to_bbo
    stored = from_bbo(Graph().parse(data=to_bbo(load_graph("clinical-data-integration")), format="turtle"))
    state, calls, _ = _drive(graph=stored)
    assert [u for u in state["unresolved"] if u["step"] == "compute"] == []
    assert [b for b in state["blocked"] if b["step"] == "literature"] == []
    assert state["facts"]["flagged_aes"] == ["THROMBOCYTOPENIA", "PLATELET COUNT DECREASED"]
    assert len([1 for tool, _ in calls if tool == "PubMed_search_articles"]) == 2


def test_the_literature_search_uses_the_inn_from_the_label_even_when_the_agent_bound_the_brand():
    """Untagged, a brand name maps to the element, so the query uses the label's INN."""
    _, calls, _ = _drive(drug_name="Lutathera")
    queries = [a["query"] for tool, a in calls if tool == "PubMed_search_articles"]
    assert queries == ["lutetium Lu 177 dotatate AND THROMBOCYTOPENIA",
                       "lutetium Lu 177 dotatate AND PLATELET COUNT DECREASED"]


# --- reported disease is not searched as an adverse event -------------------------

def test_the_literature_loop_skips_indication_terms_and_the_bundle_says_which():
    """The disease treated stays in the table, flagged; the loop spends no search on it."""
    prr = {"NEUROENDOCRINE TUMOUR": 393.4, "METASTASES TO LIVER": 21.4, "THROMBOCYTOPENIA": 7.5}
    state, calls, _ = _drive(prr=prr, indication=["NEUROENDOCRINE TUMOUR", "METASTASES TO LIVER"])
    facts = state["facts"]
    assert [r["term"] for r in facts["prr_table"] if r["flagged"]] == [
        "NEUROENDOCRINE TUMOUR", "METASTASES TO LIVER", "THROMBOCYTOPENIA"]
    assert facts["flagged_aes"] == ["THROMBOCYTOPENIA"]
    assert [a["query"] for tool, a in calls if tool == "PubMed_search_articles"] == [
        "lutetium Lu 177 dotatate AND THROMBOCYTOPENIA"]
    assert facts["excluded_aes"] == ["NEUROENDOCRINE TUMOUR", "METASTASES TO LIVER"]


# --- the indication is the drug's own, judged from its label, not a fixed cancer pattern ---

def test_a_flagged_cancer_term_that_is_not_the_indication_stays_a_signal():
    """A fixed cancer pattern would set aside a second malignancy with the treated tumour."""
    prr = {"MYELODYSPLASTIC SYNDROME": 7.5, "ACUTE MYELOID LEUKAEMIA": 4.1, "NEUROENDOCRINE TUMOUR": 393.4}
    state, calls, _ = _drive(prr=prr, requested_aes=["secondary malignancy"],
                             indication=["NEUROENDOCRINE TUMOUR"])
    facts = state["facts"]

    assert facts["signal_aes"][:2] == ["MYELODYSPLASTIC SYNDROME", "ACUTE MYELOID LEUKAEMIA"]
    assert facts["flagged_aes"] == ["MYELODYSPLASTIC SYNDROME", "ACUTE MYELOID LEUKAEMIA"]
    assert facts["excluded_aes"] == ["NEUROENDOCRINE TUMOUR"]
    assert [a["query"] for tool, a in calls if tool == "PubMed_search_articles"] == [
        "lutetium Lu 177 dotatate AND MYELODYSPLASTIC SYNDROME",
        "lutetium Lu 177 dotatate AND ACUTE MYELOID LEUKAEMIA"]


def test_a_non_cancer_drug_sets_aside_its_own_indication_read_from_its_label():
    """The metformin label's indication, not a cancer pattern, decides what is set aside."""
    prr = {"BLOOD GLUCOSE INCREASED": 3.1, "LACTIC ACIDOSIS": 4.0}
    state, calls, asked = _drive(prr=prr, drug_name="metformin", counts="metformin",
                                 indication=["BLOOD GLUCOSE INCREASED"])
    facts = state["facts"]

    assert facts["flagged_aes"] == ["LACTIC ACIDOSIS"]
    assert facts["excluded_aes"] == ["BLOOD GLUCOSE INCREASED"]
    assert [(r["term"], "placing" in r) for r in facts["indication_meddra"]] == [
        ("BLOOD GLUCOSE INCREASED", True)]
    assert facts["indication_text"] == RECORDED_LABELS["metformin"]["results"][0]["indications_and_usage"][0]
    (question,) = [q for q in asked if "indication_meddra" in q["wants"]]
    assert "BLOOD GLUCOSE INCREASED" in question["choices"]["indication_meddra"]
    assert [a["query"] for tool, a in calls if tool == "PubMed_search_articles"] == [
        "lutetium Lu 177 dotatate AND LACTIC ACIDOSIS"]


def test_the_process_carries_no_fixed_disease_pattern_and_no_cancer_wording():
    source = (GRAPHS_DIR / "clinical-data-integration.yaml").read_text()
    process = load_graph("clinical-data-integration")

    assert "TUMOU?R" not in source and "oncology" not in source.lower()
    assert "the inputs the question names" in process["report"]
    assert "indication_meddra" in process["report"]
    compute = next(s for s in process["steps"] if s["id"] == "compute")
    assert compute["check"]["flagged_aes"][1] == {"not_in": "indication_meddra_terms"}
    assert compute["check"]["excluded_aes"][1] == {"only_in": "indication_meddra_terms"}


def test_covid_19_is_not_on_the_fixed_noise_list_of_either_process():
    """For a vaccine or an antiviral it is the indication, which the judged step handles."""
    for skill in ("clinical-data-integration", "adverse-event-detection"):
        excluded = [t for s in load_graph(skill)["steps"]
                    for rule in (s.get("extract") or {}).values() if isinstance(rule, dict)
                    for t in rule.get("exclude", [])]
        assert "COVID-19" not in excluded, skill


# --- web search inside the process: the agent writes the queries, the pages become rows ------

def test_the_agents_queries_reach_the_delegated_calls_unchanged_one_per_subject():
    """The query is not fixed text in the process; with no input named, the subjects are the signals."""
    state, _, asked = _drive(records=_records())

    (queries,) = [q for q in asked if "web_queries" in q["wants"]]
    assert queries["context"]["web_subjects"] == ["THROMBOCYTOPENIA", "PLATELET COUNT DECREASED"]
    written = state["facts"]["web_queries"]
    assert written == ["THROMBOCYTOPENIA published risk estimate",
                       "PLATELET COUNT DECREASED published risk estimate"]
    (search,) = [q for q in asked if "web_rows" in q["wants"]]
    assert search["kind"] == "delegate"
    assert [c["arguments"]["query"] for c in search["calls"]] == written
    assert {c["tool"] for c in search["calls"]} == {"exa_web_search"}


def test_a_requested_word_gets_its_own_query_beside_the_signals():
    state, _, _ = _drive(prr={**PRR, "ACUTE KIDNEY INJURY": 17.7}, requested_aes=["nephrotoxicity"],
                         records=_records())

    assert state["facts"]["web_subjects"] == [
        "nephrotoxicity", "ACUTE KIDNEY INJURY", "THROMBOCYTOPENIA", "PLATELET COUNT DECREASED"]


def test_each_page_of_a_recorded_search_result_is_one_row_of_the_web_evidence_table():
    from tooluniverse.skill_working_record import WorkingRecord
    records = _records()
    state, _, _ = _drive(records=records)

    (described,) = [t for t in state["handover"]["tables"] if t["table"] == "web_rows"]
    assert described["rows"] == 6, "two queries, three recorded pages each"
    assert set(described["columns"]) >= {"query", "title", "url", "source", "date", "content"}
    assert "web_rows" not in state["handover"]["facts"], "evidence is fetched, not handed whole"
    fetched = WorkingRecord(records, state["run_id"]).fetch("web_rows", limit=2, rank_by="otoprotection strategies")
    assert fetched["rows"][0]["url"].startswith("https://")


def test_an_empty_search_result_is_a_table_with_no_rows_not_a_failure():
    state, _, _ = _drive(web_pages=[], records=_records())

    (described,) = [t for t in state["handover"]["tables"] if t["table"] == "web_rows"]
    assert described["rows"] == 0
    assert state["handover"]["failures"] == [] and state["handover"]["blocked"] == []
    assert [u for u in state["handover"]["unresolved"] if u["fact"] == "web_rows"] == []
    assert "web_search" in state["handover"]["steps_done"]


def test_the_process_holds_no_query_text_and_no_loose_web_fact():
    process = load_graph("clinical-data-integration")
    assert not any(s["id"] == "web_context" for s in process["steps"])
    search = next(s for s in process["steps"] if s["id"] == "web_search")
    assert search["for_each"] == "web_queries" and search["as"] == "query"
    assert search["delegate"][0]["arguments"]["query"] == "{query}"
    assert process["tables"]["web_rows"] == "evidence"
    assert "web_rows" in process["report"] and "web_context" not in process["report"]


# --- fetch wide: the source's maximum, and its total beside the rows ---------------

def test_trials_are_asked_for_at_the_sources_maximum_and_kept_as_one_row_each():
    """Parallel lists cut short give a few trials with nothing to say how many there were."""
    state, calls, _ = _drive()
    (sent,) = [a for tool, a in calls if tool == "search_clinical_trials"]

    assert sent["pageSize"] == 1000
    assert state["facts"]["trial_rows"] == [
        {"nct_id": "NCT1", "title": "A", "status": "COMPLETED", "phase": "PHASE3"},
        {"nct_id": "NCT2", "title": "B", "status": "TERMINATED"}]
    assert "nct_ids" not in state["facts"]


def test_the_process_names_where_each_wide_source_reports_its_total():
    process = load_graph("clinical-data-integration")
    totals = {s["id"]: s.get("total") for s in process["steps"] if s["id"] in ("trials", "literature")}

    assert totals == {"trials": "data.total_count", "literature": "metadata.total"}
    assert process["tables"]["trial_rows"] == "evidence"


def test_the_declared_paths_find_the_totals_in_the_recorded_payloads():
    """A path that matches an invented payload proves nothing about the real one. Each source
    here returned fewer rows than it holds, so a path to the page size would fail."""
    process = load_graph("clinical-data-integration")
    literature = next(s for s in process["steps"] if s["id"] == "literature")
    trials = next(s for s in process["steps"] if s["id"] == "trials")
    recorded = FIXTURES / "skill_processes" / "clinical_data_integration"
    pubmed = json.loads((recorded / "PubMed_search_articles_2026-09-24.json").read_text())
    ctgov = json.loads((recorded / "search_clinical_trials_2026-09-24.json").read_text())

    assert set(pubmed["arguments"]) == set(literature["calls"][0]["arguments"])
    assert set(ctgov["arguments"]) == set(trials["calls"][0]["arguments"])
    assert pubmed["response"]["metadata"]["count"] == 200
    assert source_total(literature, [pubmed["response"]], ["ACUTE KIDNEY INJURY"]) == {
        "ACUTE KIDNEY INJURY": 2682}
    assert len(ctgov["response"]["data"]["studies"]) < 867
    assert source_total(trials, [ctgov["response"]], None) == 867
