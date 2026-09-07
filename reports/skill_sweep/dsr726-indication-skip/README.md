# DSR-726 — the literature loop skips reported disease

Fork `189fc639`, process hash `7b834e6af569`. Two live Lutathera runs on sr-dev; the
traces here are the second, the bundle fetched from Temporal.

## The change

`flagged_aes`, the list the literature loop iterates, is the flagged PRR rows minus the
terms that name the treated disease or its course: `pluck` takes an `exclude_pattern`
(`TUMOU?R|NEOPLASM|CARCINOMA|CANCER|METASTA|PROGRESSION`), the terms it sets aside are
recorded under `excluded.compute.flagged_aes` — the same place the FAERS count step
records coding noise — and the report block tells the writer to say so. The terms stay
in `prr_table`, flagged: they are still the strongest reporting signals, they are just
not adverse events to read papers about.

## Two runs, one lesson

**Run `54e00a94`** ran on the new definition (hash `7b834e6af569`, read from GraphDB) but
in the container built from `0fc663dd`, whose `pluck` does not know `exclude_pattern`. Six
searches, six rows, nothing in `excluded`. A YAML change reaches the run through GraphDB
without a rebuild; a runner change does not.

**Run `65eb0728`**, after the rebuild:

| check | result |
|---|---|
| steps done / blocked / unresolved | 12 / 0 / 0 |
| flagged in the table | 6 (neuroendocrine tumour, liver metastases, platelet count, MDS, thrombocytopenia, renal) |
| `flagged_aes` searched | 4 |
| `excluded.compute.flagged_aes` | neuroendocrine tumour, metastases to liver |
| literature rows (papers) | platelet count 1, MDS 10, thrombocytopenia 10, renal 10 |
| titles mentioning PSMA or prostate | 0 of 31 |
| PRR citations on their own reaction | 32 of 32 |
| PRR values stated / traceable / invented | 13 / 13 / 0 |
| wall time | 192 s |

The report opens the signal section with "terms that are reported disease, not drug AEs",
lists the two with their PRRs, and says they were set aside and not literature-searched.
