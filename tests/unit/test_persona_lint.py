"""Unit tests for the prod-persona static linter (DSR-544).

Pure-function tests in the deep-module style — no squirro import, no network. They live
beside ``persona_lint.py`` (DSR-657) so every static guard sits on one CI surface.
"""

import re
import sys
from pathlib import Path

import pytest

DEPLOY = Path(__file__).resolve().parents[2] / "deploy"
sys.path.insert(0, str(DEPLOY))

import persona_lint

LONG_NAME = "OpenTargets_get_associated_targets_by_disease_efoId"
PLATFORM = set(persona_lint.PLATFORM_TOOLS)


def _served_bodies():
    """(name, text) for every served skill body on disk."""
    for name in sorted(persona_lint.served_skill_names(DEPLOY)):
        body = DEPLOY / f"persona-{name}.md"
        if body.is_file():
            yield name, body.read_text()


# --- the header is documentation, not body ---


def test_body_text_strips_leading_html_comment():
    assert persona_lint.body_text("<!--\nheader docs\n-->\n# Role\nbody").strip() == (
        "# Role\nbody"
    )


def test_body_len_excludes_header():
    body = "# Role\n" + "x" * 100
    header = "<!-- a long documentation header that must not count -->\n"
    assert persona_lint.body_len(header + body) == len(body)


@pytest.mark.parametrize(
    "text,expected",
    [
        ("See [the source](https://example.com) and ref[^1].\n\n[^1]: https://ok.example",
         ["[the source](https://example.com)"]),
        # A [x](y) inside backticks renders literally — documenting the rule, not a link.
        ("never write an inline `[text](url)` link; use footnotes", []),
    ],
)
def test_inline_links_are_flagged_but_footnotes_and_code_spans_are_not(text, expected):
    assert persona_lint.inline_links(text) == expected


def test_get_skill_names_extracted():
    text = 'route to get_skill("disease-research") then get_skill("toxicology")'
    assert persona_lint.get_skill_names(text) == ["disease-research", "toxicology"]


# --- the cap, the floor, and the routing table ---


def test_over_cap_is_an_error(tmp_path):
    text = "# Role\n" + "x" * (persona_lint.PROD_CHAR_CAP + 1)
    errors, _ = persona_lint.check_body(text, tmp_path)
    assert any("over the" in e for e in errors)


def test_short_body_warns_not_errors(tmp_path):
    errors, warnings = persona_lint.check_body("# Role\ntiny", tmp_path)
    assert errors == []
    assert any("under-using" in w for w in warnings)


def test_unknown_skill_name_is_an_error(tmp_path):
    (tmp_path / "persona-disease-research.md").write_text("served body")
    text = 'get_skill("disease-research") is fine; get_skill("drug-mechanism") is a typo'
    errors, _ = persona_lint.check_body(text, tmp_path)
    assert any('get_skill("drug-mechanism")' in e for e in errors)
    assert not any('get_skill("disease-research")' in e for e in errors)


def test_served_skill_names_excludes_dispatchers(tmp_path):
    for name in ("disease-research", "router", "prod-base", "prod", "smcp-only"):
        (tmp_path / f"persona-{name}.md").write_text("x")
    served = persona_lint.served_skill_names(tmp_path)
    assert "disease-research" in served
    assert {"router", "prod-base", "prod", "smcp-only"}.isdisjoint(served)


def test_prod_persona_assembles_and_lints_clean():
    import assemble_prod_personas
    for path, text in assemble_prod_personas.assemble():
        errors, _ = persona_lint.check_body(text, DEPLOY)
        assert errors == [], f"{path.name}: {errors}"
        assert "<!--MODE3-->" not in text, "stale MODE3 slot left in body"
        assert 'get_skill("disease-research")' in text, "Mode 3 routing table missing"


# --- a skill body must not send the agent to a tool the image does not serve ---
# DSR-644: 9 of the 20 routed skills named excluded tools. Each such call answers
# "Tool 'X' not found even after loading tools", which reads as a registry bug.

DOCKERFILE_SNIPPET = (
    'CMD ["tooluniverse-smcp", \\\n'
    '     "--compact-mode", \\\n'
    '     "--max-workers", "15", \\\n'
    '     "--exclude-tools", "Tool_RAG", \\\n'
    '     "ADMETAI_predict_toxicity", "CTD_get_gene_diseases"]\n'
)


def test_excluded_tool_names_read_from_the_shipped_command():
    """Exact set: --max-workers precedes --exclude-tools, and its value "15" is not a tool."""
    assert persona_lint.excluded_tool_names(DOCKERFILE_SNIPPET) == {
        "Tool_RAG", "ADMETAI_predict_toxicity", "CTD_get_gene_diseases"
    }


@pytest.mark.parametrize(
    "text,expected",
    [
        ("# Phase 2\nCall ADMETAI_predict_toxicity for the safety profile, then "
         "ChEMBL_search_targets for the ligands.", ["ADMETAI_predict_toxicity"]),
        ("Call ChEMBL_search_targets then UniProt_get_entry_by_accession.", []),
        # The matcher keys on the excluded set, not on a general identifier shape.
        ("Use Open Targets and Europe PMC. See Phase_2 below.", []),
        # A body's code spans are instructions to the agent, not documentation.
        ("Run `ADMETAI_predict_toxicity` on the lead compound.", ["ADMETAI_predict_toxicity"]),
    ],
)
def test_unserved_tools_inventories_every_mention_of_an_excluded_tool(text, expected):
    assert persona_lint.unserved_tools(text, {"ADMETAI_predict_toxicity"}) == expected


# --- only a POSITIVE instruction breaks a run (DSR-644 ask 1) ---
# unserved_tools() counts every mention, which is the right inventory but the wrong
# enforcement: 10 of the 33 flagged bodies are flagged for their own DO-NOT-CALL warnings.
# live_unserved_tools() keeps only mentions that tell the agent to call the thing.

DEAD = {"ADMETAI_predict_toxicity", "OncoKB_annotate_variant", "CTD_get_gene_diseases"}


@pytest.mark.parametrize(
    "text,include_header,expected",
    [
        # persona-chemical-safety.md's shape: a directive header, then names beneath it.
        ("DO NOT CALL (deployed but non-functional / out of scope):\n"
         "- `ADMETAI_predict_toxicity` and all other `ADMETAI_*` tools — they error.\n",
         False, []),
        # persona-drug-target-validation.md's shape: an inline parenthetical negation.
        ("(ADMETAI_predict_toxicity NOT available; report logP from physchem instead.)",
         False, []),
        # Studio surface: the human pastes the body below the comment, so the header is
        # never applied to the agent.
        ("<!--\nconverted 2026-06-04; dropped CTD_get_gene_diseases from phase 2\n-->\n"
         "# Role\nCall ChEMBL_search_targets for the ligands.\n", False, []),
        # DSR-687: get_skill serves the RAW file, so a header inventory claiming a dead
        # tool "IS available" mis-instructs the agent exactly like body text would.
        ("<!--\nAVAILABLE (verified):\n"
         "civic_search_evidence_items, CTD_get_gene_diseases,\n"
         "gnomad_get_variant\n-->\n"
         "# Role\nCall civic_search_evidence_items for the evidence.\n",
         True, ["CTD_get_gene_diseases"]),
        # The 17 bodies whose headers correctly FORBID an excluded tool must still pass.
        ("<!--\nUNAVAILABLE on this cluster (do not call): CTD_get_gene_diseases\n-->\n"
         "# Role\nCall ChEMBL_search_targets for the ligands.\n", True, []),
        # Suppression is per-mention, not per-block — one caveat must not clear a phase.
        ("## 5. ADMET (REQUIRED, not optional)\n"
         "Run `ADMETAI_predict_toxicity` on the lead compound.\n"
         "(OncoKB_annotate_variant NOT available; skip the actionability call.)\n",
         False, ["ADMETAI_predict_toxicity"]),
        ("For each candidate target, call CTD_get_gene_diseases(gene=...).",
         False, ["CTD_get_gene_diseases"]),
    ],
)
def test_only_a_positive_instruction_counts_as_a_live_dead_call(text, include_header, expected):
    assert persona_lint.live_unserved_tools(
        text, DEAD, include_header=include_header
    ) == expected


def test_excluded_is_an_unavailability_marker():
    """"Excluded" is this deploy's canonical word for a removed tool (the Dockerfile's own
    --exclude-tools vocabulary), so a line using it is a warning, not a call."""
    text = "advanced_literature_search_agent is likewise excluded from the image."

    assert persona_lint.live_unserved_tools(
        text, {"advanced_literature_search_agent"}
    ) == []


# --- the rule is an ERROR now that all 76 bodies are reconciled (DSR-644) ---


@pytest.mark.parametrize(
    "text,flagged",
    [
        ("# Phase 2\nCall CTD_get_gene_diseases(gene=...) for each candidate.\n", True),
        # Naming a tool in order to forbid it is the correct behaviour, not a failure.
        ("DO NOT CALL (deployed but non-functional):\n"
         "- `CTD_get_gene_diseases` — the RENCI mirror has no backends.\n", False),
    ],
)
def test_a_live_dead_instruction_fails_the_body(tmp_path, text, flagged):
    (tmp_path / "Dockerfile").write_text(
        'CMD ["tooluniverse-smcp", "--compact-mode", "--exclude-tools",'
        ' "CTD_get_gene_diseases"]\n'
    )

    errors, warnings = persona_lint.check_body(text, tmp_path)

    assert any("CTD_get_gene_diseases" in e for e in errors) is flagged, errors
    assert not any("CTD_get_gene_diseases" in w for w in warnings), warnings


def test_no_served_skill_body_instructs_a_dead_call():
    """The DSR-644 line in the sand, swept over the real bodies.

    Applied directly rather than through check_body, which raises the 10,000-char Studio
    cap as a hard error while 44 served bodies go out through get_skill instead.
    include_header, because get_skill serves the raw file (DSR-687).
    """
    excluded = persona_lint.excluded_tool_names((DEPLOY / "Dockerfile").read_text())
    assert excluded, "parsed no --exclude-tools from the Dockerfile"

    offenders = {
        name: dead
        for name, text in _served_bodies()
        if (dead := persona_lint.live_unserved_tools(text, excluded, include_header=True))
    }

    assert offenders == {}, f"bodies instructing dead calls: {offenders}"


def test_no_served_body_prescribes_a_linkless_references_log():
    """DSR-631: the chat renderer promotes only LINK-bearing footnotes, so a body ordering
    the old file-report convention makes the agent emit references that render broken."""
    markers = ("| # | Tool | Parameters", "References section logging")
    offenders = {
        name: hits
        for name, text in _served_bodies()
        if (hits := [marker for marker in markers if marker in text])
    }
    assert offenders == {}, f"bodies prescribing link-less references: {offenders}"


# --- does the name exist at all? (DSR-661) ---
# The linter only ever asked "is this name excluded?", never "does this name exist?".
# Validation goes through the same resolver the server uses: SMCP runs with name
# shortening on, so a body may legitimately name either the original or shortened form.


def test_registry_names_are_read_from_the_data_files(tmp_path):
    """A file that is not valid JSON must not break the load."""
    (tmp_path / "a.json").write_text(
        '[{"name": "ChEMBL_search_targets"}, {"name": "UniProt_get_entry"}]'
    )
    (tmp_path / "broken.json").write_text("{ not json")

    assert persona_lint.registry_tool_names(tmp_path) == {
        "ChEMBL_search_targets", "UniProt_get_entry"
    }


def test_servable_names_include_both_the_original_and_its_shortened_form():
    """A body may name either; the server resolves both to the same tool."""
    servable = persona_lint.servable_names({LONG_NAME})

    assert LONG_NAME in servable
    assert any(len(n) <= 45 for n in servable), servable


@pytest.mark.parametrize(
    "text,registry,allowlist,expected",
    [
        ("Call `ChEMBL_search_targets`, then `OpenTargets_get_invented_thing`.",
         {"ChEMBL_search_targets"}, set(), ["OpenTargets_get_invented_thing"]),
        # Bodies quote ontology ids constantly; a digits-after-prefix shape is never a tool.
        ("Map to `MONDO_0008315`, or `EFO_0001663` if MONDO has no term.",
         set(), set(), []),
        ("Report the `score` and the `id` from each row, sorted by `Grade`.",
         set(), set(), []),
        # Squirro-side tools are real but never appear in the ToolUniverse registry.
        ("Hand the table to `Code_Interpreter` for the arithmetic.",
         set(), {"Code_Interpreter"}, []),
        # find_tools is registered in smcp.py, declared nowhere in data/**/*.json.
        ("Scout with `find_tools` before assuming no tool exists.", set(), PLATFORM, []),
        # get_skill and find_skill likewise, served from the DSR-505 work onward.
        ("Call `find_skill` to discover the name, then `get_skill` to load it.",
         set(), PLATFORM, []),
        # The defect found in nine bodies on 2026-08-11: Squirro's Studio UI shows
        # `display_name`, so a body writing the label names nothing and fails silently.
        ("Use `Perplexity_Search_Llm` for recency.", set(), {"Perplexity_Web_Search_LLM"},
         ["Perplexity_Search_Llm"]),
        ("Use `Perplexity_Web_Search_LLM` for recency.", set(),
         {"Perplexity_Web_Search_LLM"}, []),
    ],
)
def test_absent_tools_reports_only_names_that_resolve_nowhere(
    text, registry, allowlist, expected
):
    assert persona_lint.absent_tools(text, registry, allowlist=allowlist) == expected


def test_a_shortened_name_resolves_against_a_long_registry_name():
    """The exemplar body names the shortened form; flagging it would be wrong."""
    text = f"Call `{persona_lint.shorten(LONG_NAME)}` for the associations."

    assert persona_lint.absent_tools(text, {LONG_NAME}) == []


def test_external_tool_names_reads_the_generated_manifest(tmp_path):
    manifest = tmp_path / "served_external_tools.json"
    manifest.write_text('{"tools": ["exa_web_search", "Clinical_Trials_Search"]}')

    assert persona_lint.external_tool_names(manifest) == {
        "exa_web_search", "Clinical_Trials_Search",
    }


def test_a_missing_manifest_over_reports_rather_than_under_reports(tmp_path):
    """The linter must still run inside the standalone fork, where there is no manifest.
    Noisy-and-visible beats silently allowing everything."""
    assert persona_lint.external_tool_names(tmp_path / "nope.json") == set()


def test_a_declared_return_field_is_not_read_as_a_tool_name(tmp_path):
    """2,373 of 2,428 definitions declare return_schema; without it every documented output
    field reads as an invented tool. Return schemas nest, so depth counts too."""
    (tmp_path / "a.json").write_text(
        '[{"name": "ESMFold_predict_structure", "return_schema": {"properties": '
        '{"mean_plddt": {}, "pdb_text": {}, "rows": {"type": "array", "items": '
        '{"properties": {"total_count": {}}}}}}}]'
    )

    fields = persona_lint.registry_return_field_names(tmp_path)

    assert {"mean_plddt", "pdb_text", "total_count"} <= fields


@pytest.mark.parametrize(
    "text,expected",
    [
        ('1. `ESMFold_predict_structure`(sequence="<F>") → `mean_plddt`, `pdb_text`.',
         ["ESMFold_predict_structure"]),
        # Bodies tabulate `tool | arguments | operation-value`; only the first cell names
        # a tool, the later columns hold argument names shaped exactly like tool names.
        ("| `IMGT_get_gene_info` | `gene_name` | `get_gene_info` |", ["IMGT_get_gene_info"]),
        # The wording that makes them values sits before the bracket, on the line above.
        ("Use the Ensembl species slugs (`homo_sapiens`, `mus_musculus`,\n"
         "`rattus_norvegicus`, `danio_rerio`) in tool calls.", []),
        ("Use `ChEMBL_search_targets`, NOT `ClinicalTrials_search`.",
         ["ChEMBL_search_targets"]),
        # A general "not ..." rule would silence real instructions; the bodies reserve
        # uppercase NOT for contrast.
        ("This is not optional: call `ChEMBL_search_targets` first.",
         ["ChEMBL_search_targets"]),
        # A bare prefix naming a family. No registry name ends in an underscore.
        ("Default to the RefSeq mRNA (`NM_`); predicted records use `XM_`/`XP_`.", []),
        ("Never pass `TAX_ID_HERE` or `ENSEMBL_ID` — a placeholder call returns empty.", []),
    ],
)
def test_referenced_tool_names_reads_only_real_call_sites(text, expected):
    assert persona_lint.referenced_tool_names(text) == expected


def test_a_body_naming_a_tool_in_order_to_forbid_it_is_not_reported():
    """A body that warns the agent off an unreachable tool is doing the right thing."""
    text = "NOTE: there is NO `WormBase_search` tool deployed — use `Monarch_search_gene`."

    assert "WormBase_search" not in persona_lint.referenced_tool_names(text)


def test_check_body_raises_an_unresolvable_tool_name_as_an_error(tmp_path):
    """The rule ships as an error, not a warning: the corpus was cleaned first, and what
    the structural rules cannot classify is named in PHANTOM_ALLOWLIST."""
    text = "# Role\n" + "x" * 6100 + "\nCall `OpenTargets_get_invented_thing` for this."

    errors, _ = persona_lint.check_body(text, tmp_path)

    assert any("OpenTargets_get_invented_thing" in e and "resolves to no served tool" in e
               for e in errors), errors


def test_every_served_body_names_only_reachable_tools():
    """The ratchet: the next wrong name fails a test rather than a demo."""
    unresolvable = {}
    for body in sorted(DEPLOY.glob("persona-*.md")):
        errors, _ = persona_lint.check_body(body.read_text(), DEPLOY)
        if hits := [e for e in errors if "resolves to no served tool" in e]:
            unresolvable[body.name] = hits

    assert unresolvable == {}, unresolvable


# --- does the call pass arguments the tool declares? (DSR-668) ---
# For the 241-tool REST family, query params are built from *declared* properties, so an
# undeclared keyword is silently DROPPED rather than rejected: organism="human" vanishes and
# the agent reports mouse+human data as human. A wrong answer, not a failed call.

PROPS = {
    LONG_NAME: {"efoId", "size"},
    "PubMed_search_articles": {"query", "limit"},
}


@pytest.mark.parametrize(
    "text,expected",
    [
        ('Call `PubMed_search_articles(query="FOXO3", limit=10)`.', []),
        ('Call `PubMed_search_articles(query="FOXO3", organism="human")`.',
         [("PubMed_search_articles", "organism")]),
        # 'tally (Supporting=1, Moderate=2)' appears verbatim in a body and is not a call.
        ("Sum the tally (Supporting=1, Moderate=2, Strong=4).", []),
        # An unknown callee is the phantom-name rule's job, not this one's.
        ('Call `Some_unknown_tool(whatever="x")`.', []),
        # Most bodies close the code mark before the bracket: `Tool`(arg=...).
        ('Call `PubMed_search_articles`(query="FOXO3", organism="human").',
         [("PubMed_search_articles", "organism")]),
        ('Call `PubMed_search_articles(query="x", 10)`.', []),
        # `limit=10` is a keyword; `score >= 0.5` inside a value is not.
        ('Call `PubMed_search_articles(query="score >= 0.5", limit=5)`.', []),
    ],
)
def test_undeclared_keywords_are_anchored_on_tools_that_exist(text, expected):
    problems = persona_lint.undeclared_keywords(text, PROPS)

    assert [(p.tool, p.keyword) for p in problems] == expected


def test_the_report_names_the_declared_alternatives():
    """Fixing a body must not require opening the registry by hand."""
    text = 'Call `PubMed_search_articles(terms="FOXO3")`.'

    message = persona_lint.undeclared_keywords(text, PROPS)[0].message

    assert "terms" in message
    assert "query" in message and "limit" in message


def test_a_call_site_is_reported_with_its_line_number():
    text = "intro\n\nCall `PubMed_search_articles(bogus=1)` here.\n"

    assert persona_lint.undeclared_keywords(text, PROPS)[0].line == 3


def test_a_shortened_call_name_resolves_to_the_registry_tool():
    """Bodies name tools in shortened form; the arguments still belong to the long one."""
    text = f'Call `{persona_lint.shorten(LONG_NAME)}(efoId="EFO_0004847", nope=1)`.'

    problems = persona_lint.undeclared_keywords(text, PROPS)

    assert [p.keyword for p in problems] == ["nope"], problems


def test_a_comment_inside_an_argument_block_contributes_no_keyword():
    """persona-protein-structural-annotation-pdb's shape: a JSON block whose `//` comment
    reads "RSA below this = buried/core", which a naive scan turns into a keyword `this`."""
    text = (
        'execute_tool("Structure_annotate", {\n'
        '  "core_rsa_cutoff": 0.25,   // RSA below this = buried/core\n'
        '  "tool_name": "x"\n'
        "})"
    )

    problems = persona_lint.undeclared_keywords(
        text, {"execute_tool": {"arguments", "tool_name"}}
    )

    assert problems == [], problems


@pytest.mark.parametrize(
    "call,flagged",
    [('`NCBIGene_search(query="TP53")`', True), ('`NCBIGene_search(term="TP53")`', False)],
)
def test_an_undeclared_keyword_fails_the_body(tmp_path, call, flagged):
    (tmp_path / "Dockerfile").write_text('CMD ["tooluniverse-smcp"]\n')

    errors, _ = persona_lint.check_body(f"# Phase 1\nCall {call} for the symbol.\n", tmp_path)

    hits = [e for e in errors if "NCBIGene_search" in e]
    assert bool(hits) is flagged, errors
    assert not flagged or "query" in hits[0], hits


def test_registry_properties_are_read_from_the_data_files(tmp_path):
    """A shortened name is an alias for the same properties."""
    (tmp_path / "a.json").write_text(
        '[{"name": "T_get", "parameter": {"properties": {"a": {}, "b": {}}}},'
        ' {"name": "%s", "parameter": {"properties": {"efoId": {}}}}]' % LONG_NAME
    )

    props = persona_lint.registry_properties(tmp_path)

    assert props["T_get"] == {"a", "b"}
    assert props[persona_lint.shorten(LONG_NAME)] == {"efoId"}


def test_no_served_skill_body_passes_an_undeclared_keyword():
    """The DSR-673 line in the sand, applied directly for the same reason the dead-call
    sweep is: check_body raises the Studio cap that 44 served bodies legitimately exceed."""
    properties = persona_lint.registry_properties(persona_lint.REGISTRY_DATA)
    assert properties, "read no tool properties from the registry"

    offenders = {
        name: [p.message for p in problems]
        for name, text in _served_bodies()
        if (problems := persona_lint.undeclared_keywords(text, properties))
    }

    assert offenders == {}, f"bodies passing undeclared keywords: {offenders}"


def test_disease_research_stops_when_the_subject_is_not_an_ontology_disease():
    """A pathogen/strain subject resolves to nothing in OpenTargets; the body must say so
    and hand off, not spend its remaining dimensions on empty ids (2026-08-20)."""
    body = (DEPLOY / "persona-disease-research.md").read_text()

    assert "find_skill" in body, "no hand-off route named"
    assert re.search(r"no hit|no match|resolves to nothing", body, re.IGNORECASE), (
        "no wrong-instrument guard"
    )
