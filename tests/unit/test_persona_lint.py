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
