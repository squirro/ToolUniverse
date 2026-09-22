"""The FAERS signal table travels to the writer as rows, and the literature search is
one query per flagged reaction.

Parallel lists let a footnote be mis-indexed; a row cannot be.
"""
import json
import re
from pathlib import Path

import pytest

from tooluniverse.skill_graph import load_graph
from tooluniverse.skill_runner import SkillRunner, _COMPUTE_OPS, loop_items

TERMS = ["MYELODYSPLASTIC SYNDROME", "NAUSEA", "RENAL IMPAIRMENT"]
PRR = {"MYELODYSPLASTIC SYNDROME": 7.5, "NAUSEA": 1.1, "RENAL IMPAIRMENT": 2.3}


def _url(term):
    return f"https://api.fda.gov/drug/event.json?search={term.replace(' ', '+')}"


_INDICATION = re.compile(r"TUMOU?R|NEOPLASM|CARCINOMA|CANCER|METASTA|PROGRESSION", re.I)


RECORDED_SEARCH = json.loads((Path(__file__).resolve().parents[1] / "fixtures" / "web"
                              / "exa_search_2026-09-21.json").read_text())


def _agent(question, web_pages=RECORDED_SEARCH["results"]):
    """The agent's side of a run: it does the compute step's arithmetic, as the task asks."""
    if "web_queries" in question["wants"]:
        # One query per subject, in the agent's own words -- the process holds no query text.
        return {"web_queries": [f"{subject} published risk estimate" for subject in question["context"]["web_subjects"]]}
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


def _recorded_lookup(term):
    import json
    from pathlib import Path
    recorded = json.loads((Path(__file__).resolve().parents[1] / "fixtures" / "ols"
                           / "placing_probe_2026-09-21.json").read_text())
    return recorded.get(term, {})


def _mapping(question):
    """The agent reads the question's word onto the source's list: the closest term wins."""
    (word,) = question["context"]["requested_aes"]
    listed = [row["term"] for row in question["context"]["faers_term_rows"]]
    chosen = [t for t in listed if "DEAF" in t or "HEARING" in t] or listed[:1]
    return {"requested_meddra": [{"of": word, "term": t, "reason": "the injury the word names",
                                  "concept": ["ear", "hearing", "vestibular"]} for t in chosen]}


def _drive(prr=PRR, graph=None, drug_name="lutetium Lu 177 dotatate", terms=TERMS,
           requested_aes=None, indication=(), web_pages=RECORDED_SEARCH["results"], records=None):
    calls, asked = [], []

    def execute(tool, a):
        calls.append((tool, a))
        if tool == "DailyMed_search_spls":
            return {"data": [{"setid": "s1", "title": "LUTATHERA (lutetium Lu 177 dotatate)"}]}
        if tool == "FDA_get_indications_by_drug_name":
            return RECORDED_LABELS["metformin" if "metformin" in drug_name else "cisplatin"]
        if tool == "FAERS_count_reactions_by_drug_event":
            return {"result": [{"term": t} for t in terms]}
        if tool == "FAERS_calculate_disproportionality":
            ae = a["adverse_event"]
            return {"data": {"metrics": {"PRR": {"value": prr[ae]}}}, "source_url": _url(ae)}
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

def test_each_signal_row_carries_the_term_its_prr_its_flag_and_its_own_query_url():
    state, _, asked = _drive()
    assert state["facts"]["prr_table"] == [
        {"term": "MYELODYSPLASTIC SYNDROME", "prr": 7.5, "flagged": True, "url": _url("MYELODYSPLASTIC SYNDROME")},
        {"term": "RENAL IMPAIRMENT", "prr": 2.3, "flagged": True, "url": _url("RENAL IMPAIRMENT")},
        {"term": "NAUSEA", "prr": 1.1, "flagged": False, "url": _url("NAUSEA")},
    ]
    compute = [q for q in asked if q["step"] == "compute"]
    assert len(compute) == 1, "the agent does the arithmetic once; the check found nothing to re-ask"
    assert "problem" not in compute[0]


def test_the_signals_travel_as_rows_only_and_the_gateway_reads_the_rows():
    """A reaction without a PRR drops out of one parallel list and not the other, so the
    rows carry term, value and link together."""
    state, _, _ = _drive()
    facts = state["facts"]
    assert facts["signal_aes"] == TERMS
    assert "prrs" not in facts and "prr_urls" not in facts
    assert [(r["term"], r["prr"], r["url"]) for r in facts["prr_rows"]] == [
        (t, PRR[t], _url(t)) for t in TERMS]
    assert facts["strong_signal"] is True


def test_seriousness_and_the_sex_split_reach_the_report_as_facts_tagged_by_their_call():
    """A step that runs and produces no fact leaves the report with no section on serious
    outcomes, so the rows travel as facts, each tagged with the call that made it."""
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
    """Reading the question's word onto the source's terms is a judged step: checked
    against the source's own list, placed by an ontology, and handed over."""
    terms = ["NAUSEA", "DEAFNESS", "FALL"]
    prr = {"NAUSEA": 1.1, "DEAFNESS": 17.7, "FALL": 2.5}
    state, calls, asked = _drive(prr=prr, terms=terms, requested_aes=["ototoxicity"])

    looped = [a["adverse_event"] for tool, a in calls if tool == "FAERS_calculate_disproportionality"]
    assert looped == ["DEAFNESS", "NAUSEA", "FALL"], "the mapped term leads; the word never reaches FAERS"
    (mapping_question,) = [q for q in asked if "requested_meddra" in q["wants"]]
    assert "term" in mapping_question["notes"] and "reason" in mapping_question["notes"]
    (row,) = state["facts"]["requested_meddra"]
    assert (row["of"], row["term"], row["placing"]) == ("ototoxicity", "DEAFNESS", "placed")
    assert row["reason"] and row["under"]
    assert state["facts"]["signal_aes"] == ["DEAFNESS", "NAUSEA", "FALL"]


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
    assert queries == ["lutetium Lu 177 dotatate AND MYELODYSPLASTIC SYNDROME",
                       "lutetium Lu 177 dotatate AND RENAL IMPAIRMENT"]
    # One row for each paper, carrying its reaction and its own links: a paper without a
    # DOI cannot shift the DOI of the next one.
    assert state["facts"]["literature_rows"] == [
        {"reaction": reaction, "pmid": "1", "title": "t", "year": 2024, "doi": "d"}
        for reaction in ("MYELODYSPLASTIC SYNDROME", "RENAL IMPAIRMENT")]


def test_no_flagged_reaction_means_no_literature_search():
    state, calls, _ = _drive(prr={t: 1.0 for t in TERMS})
    assert [tool for tool, _ in calls if tool == "PubMed_search_articles"] == []
    assert state["facts"]["flagged_aes"] == []


# --- the two compute ops ---------------------------------------------------------

def test_flag_sorts_the_rows_by_the_field_and_flags_at_the_threshold():
    rows = [{"term": "a", "prr": 1.1}, {"term": "b", "prr": 7.5}, {"term": "c", "prr": 2.0}]
    out = _COMPUTE_OPS["flag"]({"rows": "r", "field": "prr", "threshold": 2}, {"r": rows})
    assert out == [{"term": "b", "prr": 7.5, "flagged": True},
                   {"term": "c", "prr": 2.0, "flagged": True},
                   {"term": "a", "prr": 1.1, "flagged": False}]


def test_flag_is_unresolved_when_the_rows_never_arrived():
    assert _COMPUTE_OPS["flag"]({"rows": "r", "field": "prr", "threshold": 2}, {}) is None


def test_pluck_takes_one_field_from_the_rows_that_pass():
    rows = [{"term": "b", "flagged": True}, {"term": "a", "flagged": False}, {"term": "c", "flagged": True}]
    assert _COMPUTE_OPS["pluck"]({"rows": "r", "field": "term", "where": "flagged"}, {"r": rows}) == ["b", "c"]
    assert _COMPUTE_OPS["pluck"]({"rows": "r", "field": "term"}, {"r": rows}) == ["b", "a", "c"]
    assert _COMPUTE_OPS["pluck"]({"rows": "r", "field": "term"}, {}) is None


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
    """The store hands the rules back alphabetically, so a rule can be reached before
    the fact it reads exists."""
    from tooluniverse.skill_runner import absorb
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
    assert state["facts"]["flagged_aes"] == ["MYELODYSPLASTIC SYNDROME", "RENAL IMPAIRMENT"]
    assert len([1 for tool, _ in calls if tool == "PubMed_search_articles"]) == 2


def test_the_literature_search_uses_the_inn_from_the_label_even_when_the_agent_bound_the_brand():
    """Untagged, a brand name maps to the element and the wrong papers come back, so
    the query uses the INN the label title carries."""
    _, calls, _ = _drive(drug_name="Lutathera")
    queries = [a["query"] for tool, a in calls if tool == "PubMed_search_articles"]
    assert queries == ["lutetium Lu 177 dotatate AND MYELODYSPLASTIC SYNDROME",
                       "lutetium Lu 177 dotatate AND RENAL IMPAIRMENT"]


# --- reported disease is not searched as an adverse event -------------------------

def test_pluck_sets_aside_the_rows_whose_field_matches_the_exclude_pattern():
    rows = [{"term": "NEUROENDOCRINE TUMOUR", "flagged": True}, {"term": "MDS", "flagged": True},
            {"term": "METASTASES TO LIVER", "flagged": True}, {"term": "NAUSEA", "flagged": False}]
    rule = {"rows": "r", "field": "term", "where": "flagged", "exclude_pattern": "TUMOU?R|METASTA"}
    assert _COMPUTE_OPS["pluck"](rule, {"r": rows}) == ["MDS"]


def test_the_literature_loop_skips_indication_terms_and_the_bundle_says_which():
    """Neuroendocrine tumour and liver metastases top Lutathera's PRR table: they are the
    disease treated, not adverse events. They stay in the table, flagged; the loop does
    not spend a search on them, and `excluded` names them."""
    terms = ["NEUROENDOCRINE TUMOUR", "METASTASES TO LIVER", "MYELODYSPLASTIC SYNDROME", "NAUSEA"]
    prr = {"NEUROENDOCRINE TUMOUR": 393.4, "METASTASES TO LIVER": 21.4, "MYELODYSPLASTIC SYNDROME": 7.5, "NAUSEA": 1.1}
    state, calls, _ = _drive(prr=prr, terms=terms,
                             indication=["NEUROENDOCRINE TUMOUR", "METASTASES TO LIVER"])
    facts = state["facts"]
    assert [r["term"] for r in facts["prr_table"] if r["flagged"]] == terms[:3]
    assert facts["flagged_aes"] == ["MYELODYSPLASTIC SYNDROME"]
    assert [a["query"] for tool, a in calls if tool == "PubMed_search_articles"] == [
        "lutetium Lu 177 dotatate AND MYELODYSPLASTIC SYNDROME"]
    assert facts["excluded_aes"] == ["NEUROENDOCRINE TUMOUR", "METASTASES TO LIVER"]


# --- the indication is the drug's own, judged from its label, not a fixed cancer pattern ---

def test_a_flagged_cancer_term_of_a_non_cancer_drug_stays_a_signal_and_its_indication_is_set_aside():
    """A fixed cancer pattern calls every drug's tumour terms reported disease, so a
    drug for another disease keeps its own indication as a signal."""
    terms = ["BLOOD GLUCOSE INCREASED", "NAUSEA", "PANCREATIC CARCINOMA", "DIABETES MELLITUS INADEQUATE CONTROL"]
    prr = {"BLOOD GLUCOSE INCREASED": 3.1, "NAUSEA": 1.1, "PANCREATIC CARCINOMA": 2.4,
           "DIABETES MELLITUS INADEQUATE CONTROL": 4.0}
    state, calls, asked = _drive(prr=prr, terms=terms, drug_name="metformin",
                                 indication=["BLOOD GLUCOSE INCREASED", "DIABETES MELLITUS INADEQUATE CONTROL"])
    facts = state["facts"]

    assert facts["flagged_aes"] == ["PANCREATIC CARCINOMA"]
    assert facts["excluded_aes"] == ["DIABETES MELLITUS INADEQUATE CONTROL", "BLOOD GLUCOSE INCREASED"]
    assert [(r["term"], "placing" in r) for r in facts["indication_meddra"]] == [
        ("BLOOD GLUCOSE INCREASED", True), ("DIABETES MELLITUS INADEQUATE CONTROL", True)]
    assert "glycemic control" in facts["indication_text"]
    (question,) = [q for q in asked if "indication_meddra" in q["wants"]]
    assert set(question["choices"]["indication_meddra"]) == set(terms)
    assert [a["query"] for tool, a in calls if tool == "PubMed_search_articles"] == [
        "lutetium Lu 177 dotatate AND PANCREATIC CARCINOMA"]


def test_the_process_carries_no_fixed_disease_pattern_and_no_cancer_wording():
    from tooluniverse.skill_graph import GRAPHS_DIR
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
    """The agent writes one query per subject, so the query is not fixed text in the
    process; with no input named, the subjects are the signals."""
    import tempfile
    state, _, asked = _drive(records=tempfile.mkdtemp(prefix="working-records-"))

    (queries,) = [q for q in asked if "web_queries" in q["wants"]]
    assert queries["context"]["web_subjects"] == ["MYELODYSPLASTIC SYNDROME", "RENAL IMPAIRMENT"]
    written = state["facts"]["web_queries"]
    assert written == ["MYELODYSPLASTIC SYNDROME published risk estimate",
                       "RENAL IMPAIRMENT published risk estimate"]
    (search,) = [q for q in asked if "web_rows" in q["wants"]]
    assert search["kind"] == "delegate"
    assert [c["arguments"]["query"] for c in search["calls"]] == written
    assert {c["tool"] for c in search["calls"]} == {"exa_web_search"}


def test_a_requested_word_gets_its_own_query_beside_the_signals():
    import tempfile
    state, _, _ = _drive(terms=["NAUSEA", "DEAFNESS", "FALL"],
                         prr={"NAUSEA": 1.1, "DEAFNESS": 17.7, "FALL": 2.5},
                         requested_aes=["ototoxicity"], records=tempfile.mkdtemp(prefix="working-records-"))

    assert state["facts"]["web_subjects"] == ["ototoxicity", "DEAFNESS", "FALL"]


def test_each_page_of_a_recorded_search_result_is_one_row_of_the_web_evidence_table():
    import tempfile
    from tooluniverse.skill_working_record import WorkingRecord
    records = tempfile.mkdtemp(prefix="working-records-")
    state, _, _ = _drive(records=records)

    (described,) = [t for t in state["handover"]["tables"] if t["table"] == "web_rows"]
    assert described["rows"] == 6, "two queries, three recorded pages each"
    assert set(described["columns"]) >= {"query", "title", "url", "source", "date", "content"}
    assert "web_rows" not in state["handover"]["facts"], "evidence is fetched, not handed whole"
    fetched = WorkingRecord(records, state["run_id"]).fetch("web_rows", limit=2, rank_by="otoprotection strategies")
    assert fetched["rows"][0]["url"].startswith("https://")


def test_an_empty_search_result_is_a_table_with_no_rows_not_a_failure():
    import tempfile
    state, _, _ = _drive(web_pages=[], records=tempfile.mkdtemp(prefix="working-records-"))

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


def test_the_declared_paths_find_the_totals_in_the_recorded_payloads(tmp_path):
    """A path that matches an invented payload proves nothing about the real one."""
    from tooluniverse.skill_runner import source_total

    process = load_graph("clinical-data-integration")
    literature = next(s for s in process["steps"] if s["id"] == "literature")
    trials = next(s for s in process["steps"] if s["id"] == "trials")
    pubmed = {"status": "success", "data": [], "source_url": "u",
              "metadata": {"count": 200, "total": 4120, "query": "q", "source": "PubMed"}}
    ctgov = {"status": "success", "data": {"studies": [], "total_count": 866, "next_page_token": None},
             "metadata": {"source": "ClinicalTrials.gov API v2", "operation": "search"}}

    assert source_total(literature, [pubmed], ["DEAFNESS"]) == {"DEAFNESS": 4120}
    assert source_total(trials, [ctgov], None) == 866
