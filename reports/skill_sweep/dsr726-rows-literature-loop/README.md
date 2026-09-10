# DSR-726 — clinical-data-integration: rows to the writer, literature per flagged reaction

One live Lutathera run on sr-dev (agent `Kkp_3Cu0TDyIcUOdXCNZsQ`, gpt-5.2), modelled arm,
process hash `e921199177f6`, fork `0fc663dd`. Driven with `skill_audit.three_arms`; the
bundle sidecar was fetched from Temporal (`skill-clinical-data-integration-914a7255`).

## What changed in the process

The FAERS signal table reaches the writer as `facts.prr_table`: one row per reaction with
`term`, `prr`, `flagged` (PRR >= 2) and the `url` of the disproportionality call that
produced it. The rows are built by the server from the calls (`collect` with `$item` and
`source_url`), then ordered and flagged by two compute ops, `flag` and `pluck`. The three
lists (`signal_aes`, `prrs`, `prr_urls`) stay in the bundle for this rung, for comparison.

Literature is a loop over `facts.flagged_aes`: one field-tagged PubMed query per flagged
reaction, collected as `facts.literature_rows`, one row per reaction.

## What the live run shows

| check | result |
|---|---|
| steps done / blocked / unresolved | 12 / 0 / 0 |
| `prr_table` rows, each `url` naming its own term | 14 / 14 |
| flagged reactions → PubMed calls → literature rows | 6 → 6 → 6 |
| PRR citations in the report pointing at their own reaction's query | 33 of 33 |
| PRR values stated / traceable / invented | 14 / 14 / 0 |
| wall time | 194 s, 130 s inside Temporal |

The report names each reaction that returned no papers and says so under Limitations.

## Two findings, one fixed and one recorded

**Fixed.** The first live run (`61df8645`) left `flagged_aes` unresolved and blocked the
literature loop although the table was flagged. GraphDB hands a step's compute rules back
in alphabetical order; the round-trip test `from_bbo(to_bbo(p)) == p` cannot see it because
dict equality ignores order. `pluck` ran before `flag`. The runner now resolves compute rules
in passes (`0fc663dd`); the second run (`914a7255`) is the one reported above.

**Recorded, not fixed.** Five of six flagged reactions found no papers. Probing PubMed with
the same shapes shows the drug term is the limit, not the reaction term:

| query | count |
|---|---|
| `Lutathera[tiab] AND myelodysplastic syndrome[tiab]` (the run's shape) | 0 |
| `(Lutathera[tiab] OR 177Lu-DOTATATE[tiab] OR lutetium Lu 177 dotatate[tiab]) AND myelodysplastic syndrome[tiab]` | 7 |
| `(Lutathera[tiab] OR 177Lu-DOTATATE[tiab]) AND renal impairment[tiab]` | 0 |
| `(Lutathera[tiab] OR 177Lu-DOTATATE[tiab]) AND (renal impairment[tiab] OR nephrotoxicity[tiab])` | 24 |
| `Lutathera[tiab] AND NEUROENDOCRINE TUMOUR` (reaction untagged) | 73 |

Papers write the drug as 177Lu-DOTATATE far more often than as Lutathera or its INN, and
the MedDRA reaction term is not the clinical word (renal impairment vs nephrotoxicity). A
notation set for the drug and an untagged or synonym-expanded reaction term would lift
recall; both are surface-form gaps of the same kind as the atlas isotope notation, and
belong to the next rung.

**Follow-up, same day:** both fixed — see `../dsr726-rows-literature-loop-untagged/README.md`.
