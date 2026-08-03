"""FAERS resolved every drug through one field, and reported a brand name as no data.

Three defects, all in how `FAERSAnalyticsTool` turns a drug name into a query.

**1. A brand name resolves to nothing.** The only field searched was
`patient.drug.openfda.generic_name`. Measured against openFDA 2026-08-03:

    generic_name:"Lutathera"                  -> HTTP 404 (no match)
    brand_name:"Lutathera"                    -> 5,551 reports
    medicinalproduct.exact:"LUTATHERA"        -> 5,550
    generic_name:"LUTETIUM LU 177 DOTATATE"   -> 5,551

So `FAERS_calculate_disproportionality(drug_name="Lutathera", ...)` answered
`"Insufficient data: a=0, b=0"` for a drug with 5,551 reports — a confident false
negative on the most natural way to name the product.

**2. The case definition was never stated.** `generic_name` lands on the NARROW
definition (5,551, essentially LUTATHERA alone). The union of all reported
spellings is 5,783 and moves myelodysplastic syndrome from 29 cases to 50, and
the ROR from 7.2 to 12.0 — while renal impairment is stable at 2.22 either way,
so the sensitivity is signal-specific and cannot be assumed away. A reader
comparing our ROR against a published one had no way to know which population
either number described.

**3. A transport failure was indistinguishable from a real zero.**
`_get_faers_count` ended in `except Exception: return 0`, so a timeout or HTTP
error produced a count of 0, which then tripped the `a <= 0` guard and surfaced
as "Insufficient data" — the same message a genuinely absent drug produces.

The fix resolves through a documented field chain, reports which field and how
many reports it matched, and lets a transport failure raise instead of becoming
a number.
"""

import json
import pathlib

import pytest

import tooluniverse.faers_analytics_tool as mod
from tooluniverse.faers_analytics_tool import FAERSAnalyticsTool

def _shipped_config():
    """Use the config that actually ships: `operation` is a schema const."""
    import glob
    for path in glob.glob(
        str(pathlib.Path(__file__).resolve().parents[2]
            / "src" / "tooluniverse" / "data" / "**" / "*.json"),
        recursive=True,
    ):
        try:
            entries = json.loads(open(path).read())
        except Exception:
            continue
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if (isinstance(entry, dict)
                    and entry.get("name") == "FAERS_calculate_disproportionality"):
                return entry
    raise AssertionError("FAERS_calculate_disproportionality not found in data/")


CONFIG = _shipped_config()

# What openFDA really answers, keyed by the field a query uses.
REAL = {
    "patient.drug.openfda.generic_name:\"Lutathera\"": None,      # 404, no match
    "patient.drug.openfda.brand_name:\"Lutathera\"": 5551,
}


def _tool():
    return FAERSAnalyticsTool(CONFIG)


@pytest.mark.unit
def test_a_brand_name_resolves_through_the_field_chain(monkeypatch):
    """`generic_name` alone reported 5,551 reports as no data at all."""
    seen = []

    def _fake_total(self, field, term):
        seen.append(field)
        return REAL.get(f'{field}:"{term}"')

    monkeypatch.setattr(FAERSAnalyticsTool, "_field_total", _fake_total, raising=False)

    field, total = _tool()._resolve_drug_field("Lutathera")

    assert field == "patient.drug.openfda.brand_name", (field, seen)
    assert total == 5551, total
    # generic_name must still be tried FIRST, so existing numbers do not move.
    assert seen[0] == "patient.drug.openfda.generic_name", seen


@pytest.mark.unit
def test_a_generic_name_still_resolves_on_the_first_field(monkeypatch):
    """The common path must not change: no extra requests, same field."""
    seen = []

    def _fake_total(self, field, term):
        seen.append(field)
        return 5551 if "generic_name" in field else None

    monkeypatch.setattr(FAERSAnalyticsTool, "_field_total", _fake_total, raising=False)

    field, total = _tool()._resolve_drug_field("LUTETIUM LU 177 DOTATATE")

    assert field == "patient.drug.openfda.generic_name", field
    assert total == 5551
    assert seen == ["patient.drug.openfda.generic_name"], (
        f"resolved on the first field but made {len(seen)} calls: {seen}"
    )


@pytest.mark.unit
def test_a_drug_that_is_really_absent_still_resolves_to_nothing(monkeypatch):
    """The fallback chain must not invent a match."""
    monkeypatch.setattr(FAERSAnalyticsTool, "_field_total",
                        lambda self, field, term: None, raising=False)

    field, total = _tool()._resolve_drug_field("notadrug")

    assert field is None and total is None, (field, total)


@pytest.mark.unit
def test_the_envelope_states_which_field_and_how_many_reports(monkeypatch):
    """The ask: the agent must be able to state its case definition."""
    monkeypatch.setattr(
        FAERSAnalyticsTool, "_field_total",
        lambda self, field, term: 5551 if "brand_name" in field else None,
        raising=False,
    )
    monkeypatch.setattr(FAERSAnalyticsTool, "_get_faers_count",
                        lambda self, drug=None, event=None: 29 if (drug and event)
                        else (5551 if drug else 14805), raising=False)
    monkeypatch.setattr(FAERSAnalyticsTool, "_get_faers_total_count",
                        lambda self: 20328575, raising=False)

    result = _tool().run({"drug_name": "Lutathera",
                          "adverse_event": "Myelodysplastic syndrome"})

    assert result["status"] == "success", result
    # run() wraps the operation's dict under `data`.
    cd = result["data"].get("case_definition")
    assert cd, f"no case_definition in the envelope: {list(result['data'])}"
    assert cd["resolved_field"] == "patient.drug.openfda.brand_name", cd
    assert cd["drug_report_total"] == 5551, cd
    assert cd["query_term"] == "Lutathera", cd


@pytest.mark.unit
def test_a_transport_failure_is_not_a_count_of_zero(monkeypatch):
    """`except Exception: return 0` made a dead network look like an absent drug."""
    import requests as _rq

    def _boom(*a, **k):
        raise _rq.RequestException("connection reset")

    monkeypatch.setattr(mod.requests, "get", _boom)

    with pytest.raises(Exception):
        _tool()._get_faers_count("aspirin", "nausea")


@pytest.mark.network
def test_the_real_brand_name_now_produces_a_signal():
    """The claim the unit tests cannot make: Lutathera + MDS is a real signal."""
    result = _tool().run({"drug_name": "Lutathera",
                          "adverse_event": "Myelodysplastic syndrome"})

    assert result["status"] == "success", result
    payload = result["data"]
    assert payload["case_definition"]["drug_report_total"] > 5000, payload["case_definition"]
    assert payload["contingency_table"]["a_drug_and_event"] > 0, payload["contingency_table"]
