# DSR-726 follow-up — the literature loop finds the papers

Two more live Lutathera runs on sr-dev after the first pair (see
`../dsr726-rows-literature-loop/README.md`), each on a republished definition read from
GraphDB without a rebuild. The traces here are the second of the two; both bundles were
fetched from Temporal.

## Why the loop came back empty

The loop searched `<drug>[Title/Abstract] AND <reaction>[Title/Abstract]`. The tag switches
off PubMed's vocabulary mapping and asks for the exact words. Papers write the drug as
177Lu-DOTATATE (443 in title or abstract) far more than Lutathera (111) or the INN (21), and
they write "thrombocytopenia", not the MedDRA "PLATELET COUNT DECREASED". Five of six flagged
reactions found nothing.

## Two changes, each measured before it was made

**Untagged query** (`f01f9d88`, hash `d4fa242c82ec`). Untagged, PubMed maps the INN to its
Supplementary Concept "lutetium lu 177 dotatate" and the reaction to its MeSH heading.
Probed: myelodysplastic syndrome 0 → 12, renal impairment 0 → 11, thrombocytopenia 3 → 22.
Live (run `bb76f876`): six rows of ten papers each — but the agent had bound the drug as
"Lutathera", and untagged the brand maps to the element lutetium, so the 177Lu-PSMA
prostate papers came back: 5 of 10 platelet papers and 12 of 29 renal papers.

**INN from the label** (`cc6d959b`, hash `21408ee099c8`). DailyMed's title is
"LUTATHERA (lutetium Lu 177 dotatate)"; the identity step now extracts the INN beside the
brand and the loop searches with it, never with the name the agent typed. Live (run
`3bf3822d`, this folder):

| check | result |
|---|---|
| steps done / blocked / unresolved | 12 / 0 / 0 |
| literature rows (papers) | NET 10, liver mets 10, platelet count 1, MDS 10, thrombocytopenia 10, renal 10 |
| titles mentioning PSMA or prostate | 0 of 51 |
| PRR citations on their own reaction | 41 of 41 |
| PRR values stated / traceable / invented | 14 / 14 / 0 |
| wall time | 210 s |

The report carries a Literature Summary table with PMID footnotes per reaction.

## Left for the next rung

"Neuroendocrine tumour" and "metastases to liver" are the indication, not adverse events;
they top the PRR table and now cost two searches that return indication papers. The report
block already treats them as reported disease. The loop could skip a named list of
indication terms the way the FAERS count step skips coding noise.
