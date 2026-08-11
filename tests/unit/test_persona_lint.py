"""Unit tests for the prod-persona static linter (DSR-544).

Pure-function tests in the deep-module style — no squirro import, no network. Mirrors the
other registry-wide guards in this directory.

These tests live beside ``persona_lint.py`` rather than in the parent delivery repo
(DSR-657). They used to sit in the parent's ``tests/unit/`` and reach in here by path
arithmetic, which could never run in CI: the parent tracks no ``libs/`` entry on any
branch and does not register this checkout as a submodule, so a clean parent clone has no
``deploy/persona_lint.py`` to import. Co-locating them puts every static guard on one CI
surface — the ``swiss-rockets`` test workflow — and removes the cross-repo path hop.
"""

import sys
from pathlib import Path

DEPLOY = Path(__file__).resolve().parents[2] / "deploy"
sys.path.insert(0, str(DEPLOY))

import persona_lint


def test_body_text_strips_leading_html_comment():
    text = "<!--\nheader docs\n-->\n# Role\nbody"
    assert persona_lint.body_text(text).strip() == "# Role\nbody"


def test_body_len_excludes_header():
    body = "# Role\n" + "x" * 100
    with_header = "<!-- a long documentation header that must not count -->\n" + body
    assert persona_lint.body_len(with_header) == len(body)


def test_inline_links_flagged_but_footnotes_ignored():
    text = "See [the source](https://example.com) and ref[^1].\n\n[^1]: https://ok.example"
    links = persona_lint.inline_links(text)
    assert links == ["[the source](https://example.com)"]


def test_inline_link_inside_code_span_is_not_flagged():
    # A [x](y) inside backticks renders literally — documenting the rule, not a link.
    text = "never write an inline `[text](url)` link; use footnotes"
    assert persona_lint.inline_links(text) == []


def test_get_skill_names_extracted():
    text = 'route to get_skill("disease-research") then get_skill("toxicology")'
    assert persona_lint.get_skill_names(text) == ["disease-research", "toxicology"]


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
# DSR-644: 9 of the 20 routed skills named excluded tools; drug-target-validation
# named 10. Each such call answers "Tool 'X' not found even after loading tools",
# which reads as a registry bug and burns an iteration against a cap of 10.

DOCKERFILE_SNIPPET = (
    'CMD ["tooluniverse-smcp", \\\n'
    '     "--compact-mode", \\\n'
    '     "--max-workers", "15", \\\n'
    '     "--exclude-tools", "Tool_RAG", \\\n'
    '     "ADMETAI_predict_toxicity", "CTD_get_gene_diseases"]\n'
)


def test_excluded_tool_names_read_from_the_shipped_command():
    names = persona_lint.excluded_tool_names(DOCKERFILE_SNIPPET)

    assert names == {"Tool_RAG", "ADMETAI_predict_toxicity", "CTD_get_gene_diseases"}


def test_a_flag_value_is_not_mistaken_for_a_tool():
    """--max-workers precedes --exclude-tools; its value must not be collected."""
    names = persona_lint.excluded_tool_names(DOCKERFILE_SNIPPET)

    assert "15" not in names and "--max-workers" not in names


def test_a_body_naming_an_excluded_tool_is_flagged():
    text = (
        "# Phase 2\n"
        "Call ADMETAI_predict_toxicity for the safety profile, then "
        "ChEMBL_search_targets for the ligands."
    )

    dead = persona_lint.unserved_tools(text, {"ADMETAI_predict_toxicity"})

    assert dead == ["ADMETAI_predict_toxicity"], dead


def test_a_body_naming_only_served_tools_is_clean():
    text = "Call ChEMBL_search_targets then UniProt_get_entry_by_accession."

    assert persona_lint.unserved_tools(text, {"ADMETAI_predict_toxicity"}) == []


def test_prose_that_merely_resembles_a_tool_name_is_not_flagged():
    """The matcher keys on the excluded set, not on a general identifier shape."""
    text = "Use Open Targets and Europe PMC. See Phase_2 below."

    assert persona_lint.unserved_tools(text, {"ADMETAI_predict_toxicity"}) == []


def test_an_excluded_tool_inside_a_code_span_still_counts():
    """A skill body's code spans are instructions to the agent, not documentation."""
    text = "Run `ADMETAI_predict_toxicity` on the lead compound."

    assert persona_lint.unserved_tools(text, {"ADMETAI_predict_toxicity"}) == [
        "ADMETAI_predict_toxicity"
    ]


# --- only a POSITIVE instruction breaks a run (DSR-644 ask 1) ---
# unserved_tools() counts every mention, which is the right inventory but the wrong
# enforcement: 10 of the 33 flagged bodies are flagged for their own DO-NOT-CALL
# warnings, and 3 for a documentation header the agent never sees. Those bodies are
# already correct. live_unserved_tools() keeps only mentions that tell the agent to
# call the thing, so the rule can be promoted to an error without punishing them.

DEAD = {"ADMETAI_predict_toxicity", "OncoKB_annotate_variant", "CTD_get_gene_diseases"}


def test_a_tool_under_a_do_not_call_directive_is_not_a_live_instruction():
    """persona-chemical-safety.md's shape: a directive header, then names beneath it."""
    text = (
        "DO NOT CALL (deployed but non-functional / out of scope):\n"
        "- `ADMETAI_predict_toxicity` and all other `ADMETAI_*` tools — they error.\n"
    )

    assert persona_lint.live_unserved_tools(text, DEAD) == []


def test_a_tool_marked_not_available_on_its_own_line_is_not_a_live_instruction():
    """persona-drug-target-validation.md's shape: an inline parenthetical negation."""
    text = "(ADMETAI_predict_toxicity NOT available; report logP from physchem instead.)"

    assert persona_lint.live_unserved_tools(text, DEAD) == []


def test_a_tool_named_only_in_the_documentation_header_is_not_a_live_instruction():
    """The agent is served the body; a leading HTML comment is for humans."""
    text = (
        "<!--\nconverted 2026-06-04; dropped CTD_get_gene_diseases from phase 2\n-->\n"
        "# Role\nCall ChEMBL_search_targets for the ligands.\n"
    )

    assert persona_lint.live_unserved_tools(text, DEAD) == []


def test_a_positive_instruction_beside_a_prohibition_is_still_live():
    """Suppression is per-mention, not per-block — one caveat must not clear a phase.

    persona-drug-target-validation.md §5 names live tools two lines above a
    parenthetical about a different one. Missing those is the failure that matters.
    """
    text = (
        "## 5. ADMET (REQUIRED, not optional)\n"
        "Run `ADMETAI_predict_toxicity` on the lead compound.\n"
        "(OncoKB_annotate_variant NOT available; skip the actionability call.)\n"
    )

    assert persona_lint.live_unserved_tools(text, DEAD) == ["ADMETAI_predict_toxicity"]


def test_a_plain_instruction_is_still_reported():
    text = "For each candidate target, call CTD_get_gene_diseases(gene=...)."

    assert persona_lint.live_unserved_tools(text, DEAD) == ["CTD_get_gene_diseases"]


# --- the rule is an ERROR now that all 76 bodies are reconciled (DSR-644) ---
# It shipped as a warning because 33 bodies tripped it on arrival and a linter that
# is red on arrival gets switched off. Zero bodies trip it now, so it can hold the line.


def _deploy_dir_excluding(tmp_path, *names):
    quoted = ", ".join(f'"{n}"' for n in names)
    (tmp_path / "Dockerfile").write_text(
        f'CMD ["tooluniverse-smcp", "--compact-mode", "--exclude-tools", {quoted}]\n'
    )
    return tmp_path


def test_a_live_dead_instruction_fails_the_body(tmp_path):
    deploy = _deploy_dir_excluding(tmp_path, "CTD_get_gene_diseases")
    text = "# Phase 2\nCall CTD_get_gene_diseases(gene=...) for each candidate.\n"

    errors, warnings = persona_lint.check_body(text, deploy)

    assert any("CTD_get_gene_diseases" in e for e in errors), errors
    assert not any("CTD_get_gene_diseases" in w for w in warnings), warnings


def test_no_served_skill_body_instructs_a_dead_call():
    """The DSR-644 line in the sand, swept over the real bodies.

    check_body cannot do this sweep itself: it raises the 10,000-char Studio cap as a
    hard error, and 44 of the served bodies are legitimately over it because they go out
    through get_skill rather than a Studio persona field. So the rule is applied directly.
    """
    excluded = persona_lint.excluded_tool_names((DEPLOY / "Dockerfile").read_text())
    assert excluded, "parsed no --exclude-tools from the Dockerfile"

    offenders = {}
    for name in sorted(persona_lint.served_skill_names(DEPLOY)):
        body = DEPLOY / f"persona-{name}.md"
        if not body.is_file():
            continue
        dead = persona_lint.live_unserved_tools(body.read_text(), excluded)
        if dead:
            offenders[name] = dead

    assert offenders == {}, f"bodies instructing dead calls: {offenders}"


def test_a_body_that_forbids_the_dead_tool_passes(tmp_path):
    """Naming a tool in order to forbid it is the correct behaviour, not a failure."""
    deploy = _deploy_dir_excluding(tmp_path, "CTD_get_gene_diseases")
    text = (
        "DO NOT CALL (deployed but non-functional):\n"
        "- `CTD_get_gene_diseases` — the RENCI mirror has no backends.\n"
    )

    errors, warnings = persona_lint.check_body(text, deploy)

    assert not any("CTD_get_gene_diseases" in m for m in errors + warnings)


# --- does the name exist at all? (DSR-661) ---
# The linter only ever asked "is this name excluded?", never "does this name exist?" -- it
# performs no registry load. A name that exists nowhere answers "Tool 'X' not found even
# after loading tools", which reads to the agent as a registry bug and burns an iteration.
#
# Validation must go through the same resolver the server uses. SMCP runs with name
# shortening on (smcp.py sets enable_name_shortening=True, MAX_TOOL_NAME_LENGTH=45), so a
# body may legitimately name either the registry's original or the shortened form. Checking
# only originals would flag every shortened name; only shortened would flag every original.


def test_registry_names_are_read_from_the_data_files(tmp_path):
    (tmp_path / "a.json").write_text(
        '[{"name": "ChEMBL_search_targets"}, {"name": "UniProt_get_entry"}]'
    )

    names = persona_lint.registry_tool_names(tmp_path)

    assert names == {"ChEMBL_search_targets", "UniProt_get_entry"}


def test_a_file_that_is_not_valid_json_does_not_break_the_load(tmp_path):
    (tmp_path / "good.json").write_text('[{"name": "ChEMBL_search_targets"}]')
    (tmp_path / "broken.json").write_text("{ not json")

    assert persona_lint.registry_tool_names(tmp_path) == {"ChEMBL_search_targets"}


def test_servable_names_include_both_the_original_and_its_shortened_form():
    """A body may name either; the server resolves both to the same tool."""
    long_name = "OpenTargets_get_associated_targets_by_disease_efoId"

    servable = persona_lint.servable_names({long_name})

    assert long_name in servable
    assert any(len(n) <= 45 for n in servable), servable


def test_a_referenced_name_absent_from_the_registry_is_reported():
    text = "Call `ChEMBL_search_targets`, then `OpenTargets_get_invented_thing`."

    absent = persona_lint.absent_tools(text, {"ChEMBL_search_targets"})

    assert absent == ["OpenTargets_get_invented_thing"]


def test_an_identifier_in_backticks_is_not_read_as_a_tool_name():
    """Bodies quote ontology ids constantly; a digits-after-prefix shape is never a tool."""
    text = "Map to `MONDO_0008315`, or `EFO_0001663` if MONDO has no term."

    assert persona_lint.absent_tools(text, set()) == []


def test_a_plain_field_name_is_not_read_as_a_tool_name():
    text = "Report the `score` and the `id` from each row, sorted by `Grade`."

    assert persona_lint.absent_tools(text, set()) == []


def test_an_allowlisted_platform_tool_is_not_reported():
    """Squirro-side tools are real but will never appear in the ToolUniverse registry."""
    text = "Hand the table to `Code_Interpreter` for the arithmetic."

    absent = persona_lint.absent_tools(
        text, set(), allowlist={"Code_Interpreter"}
    )

    assert absent == []


def test_find_tools_is_allowlisted_because_it_is_registered_in_code():
    """Real and served, but declared nowhere in data/**/*.json.

    compact_mode_tools.json lists only list_tools, grep_tools, get_tool_info and
    execute_tool; smcp.py registers find_tools programmatically. Without the allowlist the
    registry check calls a working meta-tool a phantom -- which is how a linter earns its
    reputation for crying wolf.
    """
    text = "Scout with `find_tools` before assuming no tool exists."

    absent = persona_lint.absent_tools(
        text, set(), allowlist=set(persona_lint.PLATFORM_TOOLS)
    )

    assert absent == []


# --- does the call pass arguments the tool declares? (DSR-668) ---
# For the 241-tool REST family, query params are built from *declared* properties, so an
# undeclared keyword is silently DROPPED rather than rejected: organism="human" vanishes
# and the agent reports mouse+human data as human. A wrong answer, not a failed call.
#
# This is anchored on tools that exist, which is what makes it precise where the
# phantom-name rule is not: prose like "tally (Supporting=1)" has no callee in the
# registry and is discarded before any judgement is needed.

PROPS = {
    "OpenTargets_get_associated_targets_by_disease_efoId": {"efoId", "size"},
    "PubMed_search_articles": {"query", "limit"},
}


def test_a_call_passing_only_declared_keywords_is_clean():
    text = 'Call `PubMed_search_articles(query="FOXO3", limit=10)`.'

    assert persona_lint.undeclared_keywords(text, PROPS) == []


def test_an_undeclared_keyword_is_reported():
    text = 'Call `PubMed_search_articles(query="FOXO3", organism="human")`.'

    problems = persona_lint.undeclared_keywords(text, PROPS)

    assert len(problems) == 1
    assert problems[0].tool == "PubMed_search_articles"
    assert problems[0].keyword == "organism"


def test_the_report_names_the_declared_alternatives():
    """Fixing a body must not require opening the registry by hand."""
    text = 'Call `PubMed_search_articles(terms="FOXO3")`.'

    message = persona_lint.undeclared_keywords(text, PROPS)[0].message

    assert "terms" in message
    assert "query" in message and "limit" in message


def test_prose_that_looks_like_a_call_is_ignored():
    """'tally (Supporting=1, Moderate=2)' appears verbatim in a body and is not a call."""
    text = "Sum the tally (Supporting=1, Moderate=2, Strong=4)."

    assert persona_lint.undeclared_keywords(text, PROPS) == []


def test_a_call_to_a_tool_outside_the_registry_is_not_judged_here():
    """That is the phantom-name rule's job; this one only checks known tools."""
    text = 'Call `Some_unknown_tool(whatever="x")`.'

    assert persona_lint.undeclared_keywords(text, PROPS) == []


def test_a_call_site_is_reported_with_its_line_number():
    text = "intro\n\nCall `PubMed_search_articles(bogus=1)` here.\n"

    assert persona_lint.undeclared_keywords(text, PROPS)[0].line == 3


def test_a_shortened_call_name_resolves_to_the_registry_tool():
    """Bodies name tools in shortened form; the arguments still belong to the long one."""
    long_name = "OpenTargets_get_associated_targets_by_disease_efoId"
    short = persona_lint.shorten(long_name)
    text = f'Call `{short}(efoId="EFO_0004847", nope=1)`.'

    problems = persona_lint.undeclared_keywords(text, PROPS)

    assert [p.keyword for p in problems] == ["nope"], problems


def test_a_positional_argument_is_not_read_as_a_keyword():
    text = 'Call `PubMed_search_articles(query="x", 10)`.'

    assert persona_lint.undeclared_keywords(text, PROPS) == []


def test_a_comparison_inside_an_argument_is_not_read_as_a_keyword():
    """`limit=10` is a keyword; `score >= 0.5` inside a value is not."""
    text = 'Call `PubMed_search_articles(query="score >= 0.5", limit=5)`.'

    assert persona_lint.undeclared_keywords(text, PROPS) == []


def test_a_comment_inside_an_argument_block_contributes_no_keyword():
    """persona-protein-structural-annotation-pdb's shape: a JSON block with // comments.

    The body passes a multi-line JSON object to execute_tool and annotates the fields with
    `//` comments. One reads "RSA below this = buried/core", which a naive scan turns into
    a keyword named `this`. It was the single false positive in the first corpus run.
    """
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


# --- the rule holds the line now the corpus is clean (DSR-673) ---
# It shipped as a report-only helper because 18 call-sites tripped it on arrival, and a
# linter that is red on arrival gets switched off. All 18 are corrected, so it is an error.


def test_no_served_skill_body_passes_an_undeclared_keyword():
    """The DSR-673 line in the sand, swept over the real bodies.

    Applied directly rather than through check_body, for the same reason the dead-call
    sweep is: check_body raises the 10,000-char Studio cap as a hard error and 44 served
    bodies are legitimately over it, because they go out through get_skill rather than a
    Studio persona field.
    """
    properties = persona_lint.registry_properties(persona_lint.REGISTRY_DATA)
    assert properties, "read no tool properties from the registry"

    offenders = {}
    for name in sorted(persona_lint.served_skill_names(DEPLOY)):
        body = DEPLOY / f"persona-{name}.md"
        if not body.is_file():
            continue
        problems = persona_lint.undeclared_keywords(body.read_text(), properties)
        if problems:
            offenders[name] = [p.message for p in problems]

    assert offenders == {}, f"bodies passing undeclared keywords: {offenders}"


def test_an_undeclared_keyword_fails_the_body(tmp_path):
    """Injecting one into a body must fail the guard."""
    (tmp_path / "Dockerfile").write_text('CMD ["tooluniverse-smcp"]\n')
    text = '# Phase 1\nCall `NCBIGene_search(query="TP53")` for the symbol.\n'

    errors, _ = persona_lint.check_body(text, tmp_path)

    assert any("NCBIGene_search" in e and "query" in e for e in errors), errors


def test_a_declared_keyword_passes_check_body(tmp_path):
    (tmp_path / "Dockerfile").write_text('CMD ["tooluniverse-smcp"]\n')
    text = '# Phase 1\nCall `NCBIGene_search(term="TP53")` for the symbol.\n'

    errors, _ = persona_lint.check_body(text, tmp_path)

    assert not any("NCBIGene_search" in e for e in errors), errors


def test_registry_properties_are_read_from_the_data_files(tmp_path):
    (tmp_path / "a.json").write_text(
        '[{"name": "T_get", "parameter": {"properties": {"a": {}, "b": {}}}}]'
    )

    props = persona_lint.registry_properties(tmp_path)

    assert props["T_get"] == {"a", "b"}


def test_a_shortened_name_is_an_alias_for_the_same_properties(tmp_path):
    long_name = "OpenTargets_get_associated_targets_by_disease_efoId"
    (tmp_path / "a.json").write_text(
        '[{"name": "%s", "parameter": {"properties": {"efoId": {}}}}]' % long_name
    )

    props = persona_lint.registry_properties(tmp_path)

    assert props[persona_lint.shorten(long_name)] == {"efoId"}


def test_a_shortened_name_resolves_against_a_long_registry_name():
    """The exemplar body names the shortened form; flagging it would be wrong."""
    long_name = "OpenTargets_get_associated_targets_by_disease_efoId"
    shortened = persona_lint.shorten(long_name)
    text = f"Call `{shortened}` for the associations."

    assert persona_lint.absent_tools(text, {long_name}) == []


# --- does the referenced name exist ANYWHERE the agent can reach? (DSR-661) ---
# "Exists" spans three sources. Checking only the ToolUniverse registry is what let five
# wrong web-tool names sit unnoticed in nine bodies: the agent also reaches meta-tools that
# smcp.py registers in code, and the Squirro agent's own tools, neither of which is
# declared in data/**/*.json.


def test_the_skill_serving_meta_tools_are_not_phantoms():
    """get_skill and find_skill are registered in smcp.py, like find_tools before them.

    They were served from the DSR-505 work onward while the allowlist still named only
    find_tools, so every body routing through them read as naming two invented tools.
    """
    text = "Call `find_skill` to discover the name, then `get_skill` to load it."

    absent = persona_lint.absent_tools(
        text, set(), allowlist=set(persona_lint.PLATFORM_TOOLS)
    )

    assert absent == []


def test_external_tool_names_reads_the_generated_manifest(tmp_path):
    manifest = tmp_path / "served_external_tools.json"
    manifest.write_text('{"tools": ["exa_web_search", "Clinical_Trials_Search"]}')

    assert persona_lint.external_tool_names(manifest) == {
        "exa_web_search", "Clinical_Trials_Search",
    }


def test_a_missing_manifest_over_reports_rather_than_under_reports(tmp_path):
    """The linter must still run inside the standalone fork, where there is no manifest.

    Returning the empty set makes external tools look absent, which is noisy and visible.
    Raising would stop the linter; silently allowing everything would hide real mistakes.
    """
    assert persona_lint.external_tool_names(tmp_path / "nope.json") == set()


def test_a_studio_display_label_is_reported_but_the_callable_name_is_not():
    """The exact defect found in nine bodies on 2026-08-11.

    Squirro shows the model `custom_name` with spaces turned into underscores; the Studio
    UI shows `display_name`. "Perplexity Search Llm" is the label, so a body that writes
    `Perplexity_Search_Llm` names nothing and its web step fails silently.
    """
    served = {"Perplexity_Web_Search_LLM"}
    label = "Use `Perplexity_Search_Llm` for recency."
    callable_name = "Use `Perplexity_Web_Search_LLM` for recency."

    assert persona_lint.absent_tools(label, set(), allowlist=served) == [
        "Perplexity_Search_Llm"
    ]
    assert persona_lint.absent_tools(callable_name, set(), allowlist=served) == []


def test_a_declared_return_field_is_not_read_as_a_tool_name(tmp_path):
    """2,373 of 2,428 definitions declare return_schema; without it every documented
    output field reads as an invented tool. This was the largest single noise source."""
    (tmp_path / "a.json").write_text(
        '[{"name": "ESMFold_predict_structure", "return_schema": '
        '{"properties": {"mean_plddt": {}, "pdb_text": {}}}}]'
    )

    fields = persona_lint.registry_return_field_names(tmp_path)

    assert {"mean_plddt", "pdb_text"} <= fields


def test_return_fields_are_found_at_any_depth(tmp_path):
    """Return schemas nest: an array of rows, each an object with its own properties."""
    (tmp_path / "a.json").write_text(
        '[{"name": "T", "return_schema": {"properties": {"rows": '
        '{"type": "array", "items": {"properties": {"total_count": {}}}}}}}]'
    )

    assert "total_count" in persona_lint.registry_return_field_names(tmp_path)


def test_a_name_after_a_result_arrow_is_not_a_call():
    text = "1. `ESMFold_predict_structure`(sequence=\"<F>\") → `mean_plddt`, `pdb_text`."

    assert persona_lint.referenced_tool_names(text) == ["ESMFold_predict_structure"]


def test_only_the_first_cell_of_a_table_row_can_name_a_tool():
    """Bodies tabulate `tool | arguments | operation-value`. The later columns hold
    argument names and enum values shaped exactly like tool names."""
    text = "| `IMGT_get_gene_info` | `gene_name` | `get_gene_info` |"

    assert persona_lint.referenced_tool_names(text) == ["IMGT_get_gene_info"]


def test_a_value_list_wrapped_across_lines_is_still_a_value_list():
    """The wording that makes them values sits before the bracket, on the previous line."""
    text = (
        "Use the Ensembl species slugs (`homo_sapiens`, `mus_musculus`,\n"
        "`rattus_norvegicus`, `danio_rerio`) in tool calls."
    )

    assert persona_lint.referenced_tool_names(text) == []


def test_uppercase_not_marks_a_contrast_rather_than_an_instruction():
    text = "Use `ChEMBL_search_targets`, NOT `ClinicalTrials_search`."

    assert persona_lint.referenced_tool_names(text) == ["ChEMBL_search_targets"]


def test_lowercase_not_is_ordinary_prose_and_does_not_suppress():
    """A general "not ..." rule would silence real instructions; the bodies reserve
    uppercase NOT for contrast."""
    text = "This is not optional: call `ChEMBL_search_targets` first."

    assert persona_lint.referenced_tool_names(text) == ["ChEMBL_search_targets"]


def test_an_accession_prefix_is_not_a_tool_name():
    """`NM_`, `XM_`: a bare prefix naming a family. No registry name ends in an underscore."""
    text = "Default to the RefSeq mRNA (`NM_`); predicted records use `XM_`/`XP_`."

    assert persona_lint.referenced_tool_names(text) == []


def test_screaming_case_is_a_placeholder_not_a_tool_name():
    text = "Never pass `TAX_ID_HERE` or `ENSEMBL_ID` — a placeholder call returns empty."

    assert persona_lint.referenced_tool_names(text) == []


def test_a_body_naming_a_tool_in_order_to_forbid_it_is_not_reported():
    """Same per-mention suppression live_unserved_tools applies. A body that warns the
    agent off an unreachable tool is doing the right thing and must still pass."""
    text = "NOTE: there is NO `WormBase_search` tool deployed — use `Monarch_search_gene`."

    assert "WormBase_search" not in persona_lint.referenced_tool_names(text)


def test_check_body_raises_an_unresolvable_tool_name_as_an_error(tmp_path):
    """The rule ships as an error, not a warning.

    It can, because the corpus is already clean: it reported 145 mentions at the start of
    the 2026-08-11 session, the nine bodies naming unreachable web tools were corrected,
    and what the structural rules cannot classify is named in PHANTOM_ALLOWLIST.
    """
    text = "# Role\n" + "x" * 6100 + "\nCall `OpenTargets_get_invented_thing` for this."

    errors, _ = persona_lint.check_body(text, tmp_path)

    assert any("OpenTargets_get_invented_thing" in e and "resolves to no served tool" in e
               for e in errors), errors


def test_every_served_body_names_only_reachable_tools():
    """The ratchet. This is zero on arrival because the session that added the rule fixed
    the corpus first; it is here so the next wrong name fails a test rather than a demo."""
    unresolvable = {}
    for body in sorted(DEPLOY.glob("persona-*.md")):
        errors, _ = persona_lint.check_body(body.read_text(), DEPLOY)
        hits = [e for e in errors if "resolves to no served tool" in e]
        if hits:
            unresolvable[body.name] = hits

    assert unresolvable == {}, unresolvable
