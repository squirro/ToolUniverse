# Connectivity flow — Squirro ↔ ToolUniverse SMCP

**Ticket**: [DSR-443](https://squirro.atlassian.net/browse/DSR-443) ·
**Scope**: sempart-demo + sr-dev, this commit · **Audience**: Squirro IT.
Companion to `README.md` (ops).

> **Two hosts, one image, one flow.** SMCP is deployed on both
> `sempart-demo` and `sr-dev`. The container, egress surface (§3,
> Appendix A), trust properties, *and the way Squirro reaches the
> server* are identical — same `smcp:local` image, same loopback bind,
> same client→server hop over host loopback. Squirro→SMCP has been
> tested working on **both** hosts.


## 1. Topology

On both hosts the SMCP container's listener is bound to **host loopback
only** (`127.0.0.1:8765`): only the host's network namespace can reach
it. No nginx between Squirro and SMCP. Squirro's MCP client reaches the
server over host loopback the same way on both hosts — there is no
host-specific difference in the client→server hop.

### 1.1 Topology — same on both hosts

On both hosts `sqgenaid` (the Squirro GenAI service) runs directly on the
host as a **host process**, so it and the published SMCP port share the
same loopback; the client→server hop is a plain loopback call. The
diagram below applies unchanged to `sempart-demo` and `sr-dev`.

```
   sempart-demo / sr-dev (single Linux VM — same flow on both)
   +-------------------------------------------------------------+
   |                                                             |
   |  +----------------+  loopback HTTP  +----------------+      |
   |  |   sqgenaid     | --------------> |     smcp       |      |
   |  |  (Squirro      |   POST /mcp     |  (docker,      |      |
   |  |   GenAI host   | <-------------- |   image        |      |
   |  |   process)     | JSON-RPC + SSE  |   smcp:local)  |      |
   |  | 127.0.0.1:8000 |                 | 127.0.0.1:8765 |      |
   |  +--------+-------+                 +--------+-------+      |
   |           | HTTPS                            | HTTPS        |
   +-----------|----------------------------------|--------------+
               v                                  v
        +---------------+     also from     +-------------------+
        |  api.openai   | <---- smcp ------ |  External biomed  |
        |    .com       |   (find_tools     |   APIs (§3)       |
        +---------------+    ranking)       +-------------------+
```

| Address | Listener | Reachable from | Auth |
|---|---|---|---|
| `127.0.0.1:8765/mcp` | `smcp` container (via `0.0.0.0:8000` inside) | Same host only | **None** (see §4) |
| `127.0.0.1:8000` | `sqgenaid` host process | Same host only | (Squirro internal) |

### 1.2 sr-dev — identical to sempart

`sr-dev` reaches SMCP exactly as sempart does (§1.1): `sqgenaid` runs as
a host process and calls `http://127.0.0.1:8765/mcp` over host loopback —
no nginx, no auth. Squirro→SMCP has been tested working on this host.
There is no container boundary, and no special docker-network /
bridge-gateway / host-networking wiring is required.


## 2. On-the-wire sequence

Squirro's MCP client (Studio-UI-configured at deploy time with URL
`http://127.0.0.1:8765/mcp`, no auth) speaks standard MCP
streamable-HTTP. One init handshake per session, then `tools/call` per
LLM tool invocation. The sequence below is identical on both hosts.

```
sqgenaid                            smcp                       OpenAI /
(MCP client)                  (FastMCP, compact mode)         biomed API
   |                                  |                            |
   |--- POST /mcp  initialize ------->|                            |
   |<-- 200 + mcp-session-id: <uuid>--|                            |
   |                                  |                            |
   |--- POST /mcp  notifications/     |                            |
   |    initialized (+session hdr) -->|                            |
   |<-- 202 ---------------------------|                            |
   |                                  |                            |
   |--- POST /mcp  tools/list ------->|                            |
   |<-- 200 + 5 meta-tools  -----------|  // compact mode returns:  |
   |                                  |  // find_tools, list_tools,|
   |                                  |  // grep_tools,            |
   |                                  |  // get_tool_info,          |
   |                                  |  // execute_tool            |
   |                                  |                            |
   | (5 schemas forwarded into agent's OpenAI tools[])             |
   |                                  |                            |
   |--- POST /mcp  tools/call ------->|                            |
   |    name=find_tools               | ToolFinderLLM ranks tools  |
   |    args={query, limit}           |--- HTTPS chat/completions->|
   |                                  |<---------------------------|
   |<-- 200 + ranked tool descriptors-|                            |
   |                                  |                            |
   |--- POST /mcp  tools/call ------->|                            |
   |    name=execute_tool             | resolve, dispatch to TU    |
   |    args={tool_name, arguments}   |--- HTTPS to external API ->|
   |                                  |<---------------------------|
   |<-- 200 + tool output JSON -------|                            |
```

Key facts:

- `tools/list` returns **5 meta-tools, not ~2,278**. Compact mode loads
  the full TU catalog in the background; the agent reaches breadth via
  `tools/call name=execute_tool` (`smcp.py:1087`, `:1116`).
- `find_tools` causes a **second outbound HTTPS to OpenAI from `smcp`**
  (for ranking), independent of the agent's own OpenAI call.
- The custom JSON-RPC methods `tools/find` / `tools/search` are declared
  but **not enabled** (middleware commented at `smcp.py:558`); discovery
  flows through the `find_tools` MCP tool above.


## 3. Egress destinations

Two components make outbound HTTPS on each host — Squirro GenAI and the
`smcp` container. The table below names the hosts a typical session
hits; the **full inventory (~315 hosts) is in Appendix A** at the end of
this document. `.env.template` lists API key variables but not hostnames.

| Domain | Purpose | From | Auth |
|---|---|---|---|
| `api.openai.com` | LLM (agent + `Tool_Finder_LLM` ranking) | **sqgenaid AND smcp** | API key |
| `api.platform.opentargets.org` | Target ↔ disease ↔ drug graph | smcp | None |
| `api.fda.gov` | Drug labels, FAERS adverse events | smcp | Optional key |
| `clinicaltrials.gov` | Trial registry | smcp | None |
| `rest.uniprot.org` | Protein metadata | smcp | None |
| `www.ebi.ac.uk` | ChEMBL, EuropePMC, Reactome, AlphaFold | smcp | None |
| `eutils.ncbi.nlm.nih.gov` | PubMed, gene, taxonomy | smcp | Optional key |
| `www.proteinatlas.org` | HPA expression data | smcp | None |
| `ops.epo.org` | EPO patent search | smcp | OAuth2 |
| Other biomedical APIs | DisGeNET, OMIM, OncoKB, BRENDA, USPTO, ICD, … | smcp | Mixed; see `.env.template` |

**OpenAI is the only destination called by both containers** — a
firewall allow-list for `*.openai.com` is the single most critical
egress rule. No proxy, no TLS pinning, no outbound rate limiting from
our side.


## 4. Trust posture

- **No auth on the MCP endpoint.** Loopback bind (`docker-compose.yml:14`)
  is the sole access control on both hosts: reachability requires shell on
  the host (`htafer`, non-root, passwordless sudo, not in docker group).
  Changing to `0.0.0.0:8765` or fronting with unauthenticated nginx turns
  the server into an open relay (our OpenAI key + ~30 biomedical APIs).
- **Secrets** in `smcp/.env`: gitignored, on-host only, mounted via
  compose `env_file:` (not baked into the image). `.env.template` lists
  every variable; treat `.env` as the most sensitive file here.
- **Image** `smcp:local` is built on each host from the git checkout
  (`squirro/ToolUniverse` fork, branch `swiss-rockets`, anonymous HTTPS
  pull). No registry push; the two hosts build the same source
  independently.
- **Logs**: `json-file`, 50 MB × 3 (`docker-compose.yml:33-37`). Tool
  arguments and results are **unredacted**. No central forwarding.
- **Blast radius if compromised**: OpenAI spend on our key, rate-limit
  consumption on biomedical APIs, exfiltration via tool output (read-only
  public data — no upstream write paths from the TU tools here).
- No privilege boundary between `sqgenaid` and `smcp` beyond host process
  isolation; they share trust class.


## 5. Deployment status

This document covers **sempart-demo + sr-dev**. Status across the
clusters in scope for the broader DSR-394 work:

- **sempart-demo** (demo): SMCP **deployed**, container healthy, host-side
  `smoke.sh` green. Squirro→SMCP wired via host loopback (§1.1), tested
  working.
- **sr-dev** (acceptance): SMCP **deployed**, container healthy, host-side
  `smoke.sh` green. Squirro→SMCP wired via host loopback exactly as on
  sempart (§1.1), tested working.
- **sr-dev-com**: SMCP not deployed.
- **swiss-rockets.squirro.com** (production): SMCP not deployed. Any
  production rollout that exposes SMCP beyond loopback requires auth,
  TLS, and rate limiting before the §4 trust model holds — treat as a
  new connectivity review.


## 6. References

- `README.md` — operational deploy/smoke instructions.
- `docker-compose.yml`, `Dockerfile`, `.env.template` — runtime config.
- `smoke.sh` — minimal client showing the handshake on the wire.
- `libs/tooluniverse/src/tooluniverse/smcp.py:1087` — `_expose_core_discovery_tools` (the 4 dispatch meta-tools).
- `libs/tooluniverse/src/tooluniverse/smcp.py:1116` — `_add_search_tools` (registers `find_tools`).
- `libs/tooluniverse/src/tooluniverse/smcp.py:558` — `tools/find`/`tools/search` middleware (currently disabled).
- MCP protocol: https://modelcontextprotocol.io/


## 7. Appendix A — Full egress endpoint inventory

Generated by grepping every `url` / `endpoint` / `base_url` field in
`src/tooluniverse/data/**/*.json` and every URL constant or
`requests.{get,post,…}` call in `src/tooluniverse/**/*.py` of the
deployed commit. Plus a small set of **SDK-default endpoints** that
don't appear as string literals but are reached via the LLM client
libraries (`openai`, `google-generativeai`, `huggingface_hub`).

**~315 distinct hosts.** Any tool's invocation through `execute_tool`
may reach the corresponding host; compact-mode loads the full TU
catalog at startup, so every host below is *reachable* even though
the SR persona's queries typically hit only the §3 subset.

### A.0 Wildcard summary (for firewall allow-listing)

| Apex / wildcard | Host count | Purpose |
|---|---|---|
| `*.openai.com` | (SDK default) | LLM — agent + Tool_Finder_LLM ranking |
| `*.nlm.nih.gov` | 14 | NCBI / NIH services (PubMed, PubChem, RxNorm, UMLS, MedlinePlus, …) |
| `*.ebi.ac.uk` | 2 | EMBL-EBI hub (ChEMBL, Europe PMC, ENA, GxA, GWAS, Intact, InterPro, PRIDE, PDBe, Rhea, …) |
| `*.nih.gov` | 8 | Other NIH (NIA, NCI, NCATS, GDC, NCBO, …) |
| `*.who.int` | 4 | ICD-11, GHO |
| `*.opentargets.org` | 2 | Open Targets Platform + Genetics |
| `*.rcsb.org` | 3 | PDB structures, files, search |
| `*.open-meteo.com` | 5 | Weather/climate APIs (non-biomedical) |
| `*.nvidia.com` | 4 | NVIDIA NIM / BioNeMo inference |
| `*.hubmapconsortium.org` | 3 | HuBMAP single-cell |
| `*.clinicalgenome.org` | 4 | ClinGen / ERepo / Actionability |
| `*.nasa.gov` | 4 | NASA reference (non-biomedical) |
| `*.huggingface.co` | (SDK default) | HF model hub + inference |

If the firewall does **not** support wildcard rules, allow-list every
host listed in §A.1–A.9 explicitly.

### A.1 LLM and inference providers

Called from `smcp` for `Tool_Finder_LLM` (and from `sqgenaid` itself
for the agent's own reasoning). **High-traffic and billable.**

```
api.openai.com                  # OpenAI (SDK default; primary LLM)
*.openai.azure.com              # Azure OpenAI (host depends on AZURE_OPENAI_ENDPOINT)
generativelanguage.googleapis.com   # Google Gemini (SDK default)
openrouter.ai                   # OpenRouter fallback provider
huggingface.co                  # HF Hub: models + embeddings
api-inference.huggingface.co    # HF Inference API (SDK default)
api.nvcf.nvidia.com             # NVIDIA NIM cloud functions
build.nvidia.com                # NVIDIA build endpoints
integrate.api.nvidia.com        # NVIDIA inference
health.api.nvidia.com           # NVIDIA biomedical NIMs (BioNeMo)
assets.ngc.nvidia.com           # NVIDIA NGC model assets
azure-ai.hms.edu                # Harvard Medical School Azure helper (smolagent_tools)
```

### A.2 NCBI / NLM (US National Library of Medicine)

```
api.ncbi.nlm.nih.gov            # NCBI Datasets v2
eutils.ncbi.nlm.nih.gov         # E-utilities (PubMed, gene, taxonomy, sequence)
pubmed.ncbi.nlm.nih.gov         # PubMed UI fallback
pmc.ncbi.nlm.nih.gov            # PubMed Central
www.ncbi.nlm.nih.gov            # NCBI web (LitVar, PubTator3, IntAct mirror)
pubchem.ncbi.nlm.nih.gov        # PubChem (compounds, substances, bioassays)
trace.ncbi.nlm.nih.gov          # NCBI SRA Trace
clinicaltables.nlm.nih.gov      # NLM clinical lookup tables
dailymed.nlm.nih.gov            # DailyMed drug labels
id.nlm.nih.gov                  # NLM identifier service
rxnav.nlm.nih.gov               # RxNorm / drug nomenclature
uts.nlm.nih.gov                 # UMLS Terminology Services
uts-ws.nlm.nih.gov              # UMLS web service
wsearch.nlm.nih.gov             # NLM web search
```

### A.3 Other NIH and US-gov biomedical

```
api-evsrest.nci.nih.gov         # NCI EVS terminology
api.gdc.cancer.gov              # NCI Genomic Data Commons
api.nal.usda.gov                # USDA FoodData Central
cactus.nci.nih.gov              # NCI Chemical Identifier Resolver
data.cdc.gov                    # CDC open data
fdc.nal.usda.gov                # USDA FoodData Central (alt)
healthabc.nia.nih.gov           # NIA Health ABC study
icite.od.nih.gov                # NIH iCite (citation analysis)
ontology.api.hubmapconsortium.org
entity.api.hubmapconsortium.org
search.api.hubmapconsortium.org
odphp.health.gov                # HHS ODPHP guidelines
pdc.cancer.gov                  # NCI Proteomic Data Commons
pharos-api.ncats.io             # NCATS Pharos
pharos.nih.gov                  # NCATS Pharos web
run.opencravat.org              # NCATS OpenCRAVAT
services.cancerimagingarchive.net   # TCIA
webapis.cancer.gov              # NCI Drug Dictionary
www.atsdr.cdc.gov               # CDC ATSDR
www.cdc.gov / wwwn.cdc.gov      # CDC reference
www.nia.nih.gov                 # NIA
```

### A.4 EMBL-EBI and Europe PMC

`www.ebi.ac.uk` is a single host serving dozens of TU tools:
ArrayExpress, BioModels, BioStudies, ChEMBL, dbfetch, EBI Search, EFO,
EMDB, ENA browser, Europe PMC Citations, Europe PMC, eQTL, EVA,
Gene2Phenotype, GWAS Catalog, IntAct, InterPro, MetaboLights, MGnify,
OLS, PDBe (API + Graph), PRIDE, Proteins API.

```
www.ebi.ac.uk
alphafold.ebi.ac.uk             # AlphaFold protein structures
europepmc.org                   # Europe PMC literature
rfam.org / batch.rfam.org       # RNA family DB (EBI-hosted)
tess.elixir-europe.org          # ELIXIR Tess training portal
jaspar.elixir.no                # JASPAR TF binding profiles
```

### A.5 Major curated biomedical platforms

```
api.platform.opentargets.org    # Open Targets (target-disease-drug)
api.genetics.opentargets.org    # Open Targets Genetics
rest.uniprot.org                # UniProt
rest.ensembl.org                # Ensembl REST
rest.kegg.jp                    # KEGG pathways/compounds
data.rcsb.org                   # PDB metadata
files.rcsb.org                  # PDB structure files
search.rcsb.org                 # PDB search
reactome.org                    # Reactome pathways
plantreactome.gramene.org       # Plant Reactome
string-db.org                   # STRING protein interactions
stitch.embl.de                  # STITCH compound-protein
dgidb.org / www.dgidb.org       # DGIdb drug-gene interactions
www.proteinatlas.org            # HPA Human Protein Atlas
api.cellxgene.cziscience.com    # CZI cellxgene Census
api.brain-map.org               # Allen Brain Atlas
api.geneontology.org            # Gene Ontology
golr-aux.geneontology.io        # GO golr
api.monarchinitiative.org       # Monarch Initiative
pantherdb.org                   # PANTHER classification
public.ndexbio.org              # NDEx networks
clue.io / api.clue.io           # Broad CMap / Connectivity Map
```

### A.6 Genomic variants and clinical genetics

```
gnomad.broadinstitute.org       # gnomAD population variation
rest.variantvalidator.org       # VariantValidator HGVS
mutalyzer.nl                    # Mutalyzer HGVS
panelapp.genomicsengland.co.uk  # Genomics England PanelApp
api.disgenet.com                # DisGeNET (auth required)
www.disgenet.org                # DisGeNET web
beacon.progenetix.org           # GA4GH Beacon (Progenetix)
search.clinicalgenome.org
reg.clinicalgenome.org
erepo.clinicalgenome.org
actionability.clinicalgenome.org
search.thegencc.org
thegencc.org
wintervar.wglab.org             # InterVar
cancervar.wglab.org             # CancerVar
regulomedb.org                  # RegulomeDB
databases.lovd.nl               # LOVD locus-specific
api.mavedb.org                  # MaveDB
r12.finngen.fi                  # FinnGen
www.internationalgenome.org     # 1000 Genomes
www.deciphergenomics.org        # DECIPHER
www.phenoscanner.medschl.cam.ac.uk  # PhenoScanner
cadd.bihealth.org               # CADD scoring
cadd.zju.edu.cn                 # CADD (CN mirror)
pangolin-37-xwkwwwxdwq-uc.a.run.app # Pangolin splice predictor (GCR)
pangolin-38-xwkwwwxdwq-uc.a.run.app
spliceai-37-xwkwwwxdwq-uc.a.run.app # SpliceAI (GCR)
spliceai-38-xwkwwwxdwq-uc.a.run.app
alphamissense.hegelab.org       # AlphaMissense (hegelab mirror)
hocomoco14.autosome.org         # HOCOMOCO TF motifs
api.genome.ucsc.edu             # UCSC Genome
data.4dnucleome.org             # 4D Nucleome
data.orthodb.org                # OrthoDB
omabrowser.org                  # OMA orthologs
gtdb-api.ecogenomic.org         # GTDB taxonomy
gtexportal.org                  # GTEx eQTL
www.encodeproject.org           # ENCODE
chip-atlas.org                  # ChIP-Atlas
www.intogen.org                 # IntOGen cancer drivers
www.cbioportal.org              # cBioPortal
www.dfam.org                    # DFAM repeats
www.genomenexus.org             # Genome Nexus
```

### A.7 Chemistry, drugs, pharmacology, screening

```
www.bindingdb.org               # BindingDB
www.guidetopharmacology.org     # IUPHAR/BPS Guide to Pharmacology
www.swissadme.ch                # SwissADME
swissdock.ch / www.swissdock.ch # SwissDock
www.swisstargetprediction.ch    # SwissTargetPrediction
www.lipidmaps.org / lipidmaps.org   # LIPID MAPS
www.metabolomicsworkbench.org   # Metabolomics Workbench
metabolomics-usi.gnps2.org      # GNPS metabolomics
massbank.eu                     # MassBank mass spectra
massive.ucsd.edu                # UCSD MassIVE
proteomecentral.proteomexchange.org
proteins.plus                   # ProteinsPlus
klifs.net                       # KLIFS kinase structures
zinc15.docking.org              # ZINC15
mcule.com / doc.mcule.com       # Mcule virtual chemistry
enamine.net / new.enaminestore.com
api.emolecules.com / www.emolecules.com
www.t3db.ca                     # T3DB toxins
www.drugbank.ca                 # DrugBank XML
hmdb.ca / www.hmdb.ca           # HMDB Human Metabolome
www.rhea-db.org                 # Rhea reactions
enzyme.expasy.org               # ExPASy enzyme
prosite.expasy.org              # PROSITE
www.idtdna.com                  # IDT oligo design
www.crystallography.net         # COD crystal structures
tmapi.neb.com                   # NEB enzyme finder
mibig.secondarymetabolites.org  # MIBiG secondary metabolites
www.tcdb.org                    # TCDB transporter classification
www.gsea-msigdb.org             # MSigDB
elm.eu.org                      # ELM eukaryotic linear motifs
www.openml.org                  # OpenML ML datasets
biit.cs.ut.ee                   # g:Profiler
db.idrblab.net                  # IDRB drug-target
drugcentral.org                 # DrugCentral
hb.flatironinstitute.org        # Flatiron H-bond DB
db.indra.bio                    # INDRA pathway DB
```

### A.8 Pharmacogenomics and clinical guidelines

```
api.cpicpgx.org / cpicpgx.org   # CPIC pharmacogenomic guidelines
api.clinpgx.org                 # ClinPGx
api.pharmgkb.org / www.pharmgkb.org # PharmGKB
www.pharmvar.org                # PharmVar
www.nice.org.uk                 # NICE guidelines (UK)
www.nccn.org                    # NCCN guidelines (US)
www.sign.ac.uk                  # SIGN guidelines (Scotland)
canadiantaskforce.ca            # Canadian Task Force
guidelines.ebmportal.com
api.magicapp.org                # MAGICapp digital guidelines
www.tripdatabase.com            # TRIP evidence database
```

### A.9 Clinical trials, regulatory, drug safety

```
clinicaltrials.gov              # NIH ClinicalTrials.gov
api.fda.gov                     # openFDA (FAERS, drug labels)
open.fda.gov / www.fda.gov      # openFDA web
sideeffects.embl.de             # SIDER adverse effects
www.oncokb.org / api.oncokb.org # OncoKB
icd.who.int                     # WHO ICD-11
icdaccessmanagement.who.int
id.who.int / www.who.int        # WHO
ghoapi.azureedge.net            # WHO Global Health Observatory
disease.sh                      # disease.sh COVID-19
nextstrain.org                  # Nextstrain phylogenetics
www.disease-ontology.org        # Disease Ontology
ontology.jax.org                # JAX HPO
oncotree.mskcc.org              # MSKCC OncoTree
api.orphacode.org               # Orphanet codes
api.orphadata.com               # Orphadata rare disease
api.omim.org                    # OMIM (auth required)
```

### A.10 Patents and IP

```
ops.epo.org                     # EPO Open Patent Services (OAuth2)
api.uspto.gov                   # USPTO API
```

### A.11 Protein structure, function, interactions

```
alphafold.ebi.ac.uk             # AlphaFold (also in §A.4)
mobidb.org / mobidb.bio.unipd.it    # MobiDB disordered regions
www.disprot.org                 # DisProt
swissmodel.expasy.org           # SWISS-MODEL
www.cathdb.info                 # CATH structural classification
www.sasbdb.org                  # SASBDB SAXS
channelsdb.ncbr.muni.cz         # ChannelsDB
pdb-redo.eu                     # PDB-REDO refinement
scop.mrc-lmb.cam.ac.uk          # SCOP
www.imgt.org                    # IMGT immunoglobulins
www.fpbase.org                  # FPbase fluorescent proteins
www.proteomicsdb.org            # ProteomicsDB
www.pathwaycommons.org          # Pathway Commons
opig.stats.ox.ac.uk             # OPIG (SAbDab, etc.)
apprisws.bioinfo.cnio.es        # APPRIS principal isoforms
deepgo.cbrc.kaust.edu.sa        # DeepGO function prediction
research.bioinformatics.udel.edu    # ProteoCons
evemodel.org                    # EVEmodel
zitniklab.hms.harvard.edu       # Zitnik lab tools (Harvard)
```

### A.12 Expression, single-cell, cell atlases, omics

```
api.cellxgene.cziscience.com    # cellxgene Census (also §A.4)
service.azul.data.humancellatlas.org    # HCA
maayanlab.cloud                 # Maayan lab tools (ARCHS4, ChEA, …)
www.bgee.org                    # Bgee gene expression
www.pombase.org                 # PomBase yeast
www.yeastgenome.org             # SGD yeast
www.flymine.org / www.mousemine.org / www.humanmine.org   # InterMine
targetmine.mizuguchilab.org     # TargetMine
bigg.ucsd.edu                   # BiGG genome-scale models
api.cellmodelpassports.sanger.ac.uk
api.cellosaurus.org             # Cellosaurus cell lines
www.alliancegenome.org          # Alliance of Genome Resources
rest.genenames.org              # HGNC gene names
www.mousephenotype.org          # IMPC
rest.wormbase.org               # WormBase
rest.rgd.mcw.edu                # Rat Genome DB (in source, schema-only)
plantreactome.gramene.org       # Plant Reactome
synergxdb.ca                    # SynergxDB drug combos
veupathdb.org                   # VEuPathDB (EuPathDB)
neuromorpho.org                 # NeuroMorpho
neurovault.org                  # NeuroVault
modeldb.science                 # ModelDB neural models
idr.openmicroscopy.org          # IDR imaging
sabiork.h-its.org               # SABIO-RK kinetics
query-api.iedb.org              # IEDB immune epitopes
www.immport.org (schema)        # ImmPort
vdjdb.com                       # VDJdb TCR
omnipathdb.org                  # OmniPath signaling
gpcrdb.org                      # GPCRdb
mychem.info                     # MyChem.info
mydisease.info                  # MyDisease.info
mygene.info                     # MyGene.info
myvariant.info                  # MyVariant.info
bio-bigdata.hrbmu.edu.cn        # HRBMU multi-omics
biocyc.org / websvc.biocyc.org  # BioCyc / MetaCyc
ctdbase.org                     # CTD chemical-gene-disease
www.disprot.org                 # DisProt (also §A.11)
rnacentral.org                  # RNAcentral
```

### A.13 Ontologies, registries, ID resolvers

```
purl.obolibrary.org             # OBO Foundry ontologies
bioregistry.io                  # Bioregistry
registry.api.identifiers.org
resolver.api.identifiers.org
data.bioontology.org            # NCBO BioPortal data
bioportal.bioontology.org       # NCBO BioPortal
bio.tools                       # ELIXIR bio.tools registry
biotools_registry (alias)
api.catalogueoflife.org         # Catalogue of Life
api.ror.org / ror.org           # Research Organization Registry
api.crossref.org                # Crossref DOI
api.datacite.org                # DataCite DOI
doi.org                         # DOI resolver
pub.orcid.org                   # ORCID public API
www.re3data.org                 # re3data repository registry
identifiers.org (legacy)
www.itis.gov                    # ITIS taxonomy
```

### A.14 Literature, citations, scholarly identifiers

```
arxiv.org / export.arxiv.org    # arXiv
api.biorxiv.org                 # bioRxiv
api.archives-ouvertes.fr        # HAL
api.core.ac.uk / core.ac.uk     # CORE
api.openaire.eu                 # OpenAIRE
api.openalex.org / openalex.org # OpenAlex
api.opencitations.net           # OpenCitations
api.scite.ai                    # Scite
api.semanticscholar.org / www.semanticscholar.org  # Semantic Scholar
api.unpaywall.org               # Unpaywall
dblp.org                        # DBLP CS bibliography
doaj.org                        # DOAJ open-access journals
inspirehep.net                  # INSPIRE-HEP
scholar.archive.org             # Internet Archive Scholar
datadryad.org                   # Dryad data
dataverse.harvard.edu           # Harvard Dataverse
api.figshare.com                # Figshare
api.osf.io                      # Open Science Framework
zenodo.org                      # Zenodo
api.developers.addgene.org      # Addgene plasmids
ec.europa.eu                    # EC open data
```

### A.15 Ecology, biodiversity, taxonomy

```
api.gbif.org                    # GBIF biodiversity occurrences
api.inaturalist.org             # iNaturalist
api.obis.org                    # OBIS ocean biodiversity
api.ebird.org                   # eBird
api.opentreeoflife.org          # Open Tree of Life
api.census.gov                  # US Census (also non-bio reference)
eol.org                         # Encyclopedia of Life
paleobiodb.org                  # Paleobiology DB
search.idigbio.org              # iDigBio specimens
marineregions.org / www.marineregions.org
www.marinespecies.org           # WoRMS marine species
powo.science.kew.org            # Kew Plants of the World
nextstrain.org                  # phylogenetics (also §A.9)
synbiohub.org                   # SynBioHub
www.openml.org                  # OpenML (also §A.7)
```

### A.16 Earth, weather, space, non-biomedical reference

Loaded into TU but **never invoked by the SR biomedical persona** in
normal operation. Listed for completeness.

```
api.weather.gov                 # NWS US weather
api.open-meteo.com              # Open-Meteo
air-quality-api.open-meteo.com
archive-api.open-meteo.com
climate-api.open-meteo.com
flood-api.open-meteo.com
geocoding-api.open-meteo.com
marine-api.open-meteo.com
api.met.no                      # MET Norway
api.waqi.info                   # World Air Quality Index
api.opentopodata.org            # OpenTopoData elevation
api.sunrise-sunset.org
nominatim.openstreetmap.org     # OSM geocoding
earthquake.usgs.gov             # USGS earthquakes
waterservices.usgs.gov          # USGS water
cmr.earthdata.nasa.gov          # NASA Earthdata
eonet.gsfc.nasa.gov             # NASA EONET events
kauai.ccmc.gsfc.nasa.gov        # NASA CCMC space weather
ssd.jpl.nasa.gov / ssd-api.jpl.nasa.gov # JPL Solar System Dynamics
exoplanetarchive.ipac.caltech.edu
ned.ipac.caltech.edu            # NASA NED astronomy
simbad.cds.unistra.fr           # SIMBAD astronomy
skyserver.sdss.org              # SDSS skyserver
coastwatch.pfeg.noaa.gov        # NOAA ERDDAP
rest.isric.org                  # ISRIC SoilGrids
www.worldbank.org / api.worldbank.org   # World Bank
catalogue.ceda.ac.uk            # CEDA climate archive
world.openfoodfacts.org         # Open Food Facts
www.countyhealthrankings.org    # County Health Rankings
```

### A.17 Code, package registries, generic web

```
api.github.com                  # GitHub (some agentic tools)
api.anaconda.org                # Anaconda.org packages
bioc.r-universe.dev             # Bioconductor R-universe
crandb.r-pkg.org                # CRAN database
pypi.org / pypistats.org        # PyPI
en.wikipedia.org / www.wikipedia.org
www.wikidata.org / query.wikidata.org / dbpedia.org
ec.europa.eu                    # EC OpenData
httpbin.org                     # diagnostic (some test tools)
```

### A.18 Out-of-cluster TU helpers (worth flagging)

These are TU calling **third-party-hosted TU services**, not under SR control:

```
tooluniversemcpserver.onrender.com  # Render-hosted TU instance — `agentic_tools.json` references this as an external TU
                                    # if invoked, smcp makes an outbound HTTPS call to this third party
azure-ai.hms.edu                # Harvard Medical School Azure helper — used by `smolagent_tools`
```

`agentic_tools.json` declares ~30 "RemoteTool" definitions pointing at
`tooluniversemcpserver.onrender.com`. They are loaded into the registry
in compact mode. If the agent picks one of these via `find_tools`, our
server makes an outbound HTTPS call to Render-hosted infrastructure.
For a hardened deployment, consider excluding `agentic_tools` (add to
`--exclude-tools` in `Dockerfile`).

### A.19 Hosts grep'd but **not** treated as endpoints

The static analysis also surfaced ~200 documentation URLs (e.g.
`*.readthedocs.io`, `pytorch.org`, `numpy.org`, `scikit-learn.org`,
`matplotlib.org`, `flask.palletsprojects.com`, etc.) embedded in tool
description text. These are **not invoked**; they appear because tool
metadata cites the upstream library's docs. Not included above.

---

**Methodology notes**

- Inventory generated against `libs/tooluniverse/` at the deployed commit.
- The deployed container loads the full TU catalog via `--compact-mode`
  but excludes `Tool_RAG` (see `Dockerfile:54`). Excluding `Tool_RAG` does
  not change the egress surface — that tool is local-model based, not
  network-bound, so its absence has no effect on this list.
- The hostname list is what the deployed image **can** reach if the
  matching tool is invoked. The §3 table is what it **typically** reaches
  during normal sempart-demo use.
- For an ongoing watch, re-run:
  `grep -rhoE 'https?://[a-zA-Z0-9._-]+\.[a-zA-Z]{2,}' libs/tooluniverse/src/tooluniverse/ | sort -u`
  and diff against the list above after TU upstream merges.
