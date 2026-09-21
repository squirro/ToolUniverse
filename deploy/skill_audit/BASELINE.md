# Skill coverage baseline — 2026-08-21, sr-dev

All 76 served skills probed once, one question each, on `sr-dev.squirro.cloud`
against agent `Kkp_3Cu0TDyIcUOdXCNZsQ` ("[DEV/TEST] General Research and TU"),
image built from `feat/tu-skill-quality-campaign`.

**A baseline is a reference measurement, not a target.** The gate rule is *no new
failures against this record*, not *zero failures* — requiring green first would be
circular, since every remediation ticket needs the baseline to prove it worked.

## Verdicts

| verdict | skills |
|---|---|
| fail | 61 |
| warn | 10 |
| retry (provider refusal) | 4 |
| pass | 1 (`pharmacovigilance`) |

## Findings

| code | count | what it means |
|---|---|---|
| `skill_after_web` | 30 | a genuine web search ran before `find_skill`/`get_skill` |
| `linkless_footnote` | 29 | footnote definitions the chat renderer will drop |
| `no_skill_loaded` | 26 | no `get_skill` anywhere in the turn |
| `schema_rejected` | 24 | the call did not satisfy the tool's schema |
| `tool_error` | 19 | the tool genuinely failed |
| `wrong_skill` | 14 | a skill loaded, but not the one the question was written for |
| `lookup_miss` | 12 | the database does not hold that entity or identifier |
| `skill_without_tools` | 7 | the skill loaded and then no `execute_tool` followed |
| `answer_declined` | 4 | the answer hedges on availability |
| `provider_refusal` | 4 | environment artefact, re-run |
| `tool_not_found` | 3 | a tool name that is not registered |
| `missing_primary_tools` | 1 | see limitation 1 |

## Routing

A skill loaded on 46 of 76 turns and it was the right one on 32, so the intended
playbook governed **42% of questions**. Of the 29 turns where the right skill loaded
and the provider did not refuse, 5 fired **none** of the tools their body names
(`cancer-variant-interpretation`, `clinical-trial-design`, `neuroscience`,
`proteomics-data-retrieval`, `systems-biology`) — the skill governs on paper and the
agent improvises. Median share of a body's named tools that fired: **0.33**. Median
number of tools called that the body never names: **0** — so when a skill does govern,
the agent stays inside its toolset rather than inventing.

## Hand-check

One finding per code, eleven in all, read against the saved transcript. **All eleven
verdicts matched what the trace shows.** Two were sharper than expected:

* `linkless_footnote` on `aging-senescence` caught `](clinicaltrials.gov)` and
  `](squirro_source#…)` — targets with no URL scheme. The Squirro chat renderer
  promotes only `http`/`https`/`mailto`/`xmpp`, so both render broken.
* `tool_error` on `acmg-variant-classification` caught gnomAD answering HTTP 500 with
  `"Unrecognized query"`, which supports DSR-694's reading that the query is malformed
  rather than the endpoint being down.

## Known limitations of this baseline

1. **`required_tools` is inert across the corpus.** It reads the `**Primary**`
   convention, and only 3 of 86 bodies use it — which is why `missing_primary_tools`
   fired once in 76 probes. `body_tool_coverage` reports coverage over *every* tool a
   body names instead, as data rather than a verdict, because bodies legitimately name
   gated alternatives ("pick the first applicable, then STOP").
2. **`no_skill_loaded` conflates two different failures.** "Never consulted the skill
   index" and "called `find_skill`, then loaded nothing" are both counted here;
   `aging-senescence` is the second kind. Worth splitting when DSR-691 investigates
   routing, since the two have different causes.
3. **One run per skill.** LLM turns are not deterministic — `pharmacovigilance` scored
   `pass` here and `tool_error` on a re-run an hour later. Treat single-skill deltas as
   weak evidence; treat class-level movement (29 link-less footnotes → N) as strong.
4. **Raw traces are local only.** `results.jsonl` and `report.md` are the record;
   `traces/` is 4.2 MB of API payload and stays out of the repo, so `rescore` works on
   the machine that ran the sweep, not from a fresh clone.

## Reproducing

```
cd deploy
python -m skill_audit.sweep run --agent-id <id> --target srdev --env-file <dotenv>
python -m skill_audit.sweep diff --old <baseline-run> --new <new-run>   # exit 1 on regression
```
