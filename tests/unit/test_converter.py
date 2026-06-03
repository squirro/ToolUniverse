"""Unit tests for the conversion orchestrator (DSR-508)."""
import pytest

from tooluniverse.skill_conversion.converter import ConvertedSkill, Converter
from tooluniverse.skill_conversion.registry_adapter import RegistryAdapter

pytestmark = pytest.mark.unit

# Real router phrasing: the analysis set lives in the STEP-2 "this exact list
# (never invent): … Use for …" clause (parse_router_analysis_skills scopes to it).
ROUTER = ('description: "Router. STEP 2 routing — pick a sub-skill name from this exact '
          'list (never invent): tooluniverse-crispr-screen-analysis (MAGeCK), '
          'tooluniverse-proteomics-analysis (mass spec). Use for CSV/VCF analysis."')

GOLDEN_SOURCE = "# disease SKILL source"
GOLDEN_PERSONA = "# disease persona converted"


def _converter(judge, available_names):
    def probe(name):
        return {"exists": name in available_names, "signature": None}
    adapter = RegistryAdapter(cluster="sr-dev", probe=probe, cache={})
    return Converter(adapter=adapter, judge=judge,
                     golden_source=GOLDEN_SOURCE, golden_persona=GOLDEN_PERSONA)


def _write_skill(tmp_path, name, skill_md):
    d = tmp_path / name
    d.mkdir()
    (d / "SKILL.md").write_text(skill_md)
    return d


def test_analysis_skill_is_excluded_and_judge_not_called(tmp_path):
    calls = []
    conv = _converter(lambda p: calls.append(p) or "BODY", available_names=set())
    skill_dir = _write_skill(tmp_path, "tooluniverse-crispr-screen-analysis", "# anything")
    result = conv.convert(skill_dir, router_md=ROUTER, prompt_out=tmp_path / "p.md")
    assert isinstance(result, ConvertedSkill)
    assert result.servable is False
    assert result.body is None
    assert calls == []  # judge never called for an excluded skill


def test_servable_skill_assembles_saved_prompt_and_calls_judge(tmp_path):
    seen = {}
    def judge(prompt):
        seen["prompt"] = prompt
        return "# CONVERTED BODY"
    conv = _converter(judge, available_names={"OpenTargets_get_asso_targ_by_dise_efoI"})
    skill_md = "# Target Research\nCall `OpenTargets_get_asso_targ_by_dise_efoI`(efoId)."
    skill_dir = _write_skill(tmp_path, "tooluniverse-target-research", skill_md)
    prompt_out = tmp_path / "prompts" / "target.prompt.md"

    result = conv.convert(skill_dir, router_md=ROUTER, prompt_out=prompt_out)

    assert result.servable is True
    assert result.body == "# CONVERTED BODY"
    assert prompt_out.exists()                       # prompt artifact saved
    assert "OpenTargets_get_asso_targ_by_dise_efoI" in seen["prompt"]
    assert GOLDEN_SOURCE in seen["prompt"]           # few-shot wired in
    assert result.escalations == ()


def test_unavailable_seeded_family_is_substituted_in_prompt(tmp_path):
    seen = {}
    conv = _converter(lambda p: seen.update(prompt=p) or "BODY",
                      available_names={"OpenTargets_get_asso_targ_by_dise_efoI"})
    skill_md = "Use `DisGeNET_search_gene`(gene) and `OpenTargets_get_asso_targ_by_dise_efoI`(efoId)."
    skill_dir = _write_skill(tmp_path, "tooluniverse-target-research", skill_md)
    result = conv.convert(skill_dir, router_md=ROUTER, prompt_out=tmp_path / "p.md")
    assert "SUBSTITUTE" in seen["prompt"].upper()
    assert "DisGeNET_search_gene" in seen["prompt"]
    assert result.escalations == ()  # OpenTargets alt is available → no escalation


def test_dead_nonsubstitutable_tool_listed_do_not_call(tmp_path):
    seen = {}
    conv = _converter(lambda p: seen.update(prompt=p) or "BODY",
                      available_names={"UniProt_get_function_by_accession"})
    skill_md = ("Call `UniProt_get_function_by_accession`(accession) and "
                "`OpenTargets_get_target_safety_profile_by_ensemblID`(ensemblId).")
    skill_dir = _write_skill(tmp_path, "tooluniverse-target-research", skill_md)
    conv.convert(skill_dir, router_md=ROUTER, prompt_out=tmp_path / "p.md")
    assert "DO NOT CALL" in seen["prompt"].upper()
    assert "OpenTargets_get_target_safety_profile_by_ensemblID" in seen["prompt"]
