# A/B prod personas — apply & verify (DSR-543)

Two prod personas for the main General Research Agent on `swiss-rockets.squirro.com`, differing
by **one** factor — how much weight they put on the TU skill layer. The customer hand-picks.

| Arm | File | Emphasis |
|-----|------|----------|
| **A — Neutral-tools** | `persona-prod-neutral.md` | TU skill/tool surface present as peer tools, no routing preference |
| **B — Weighted-skills** | `persona-prod-weighted.md` | Mode 3 routes biomedical-entity/workflow queries to the skill path first (DSR-545) |

## Source of truth

Both bodies are **generated** — never hand-edit `persona-prod-neutral.md` / `persona-prod-weighted.md`.
Edit `persona-prod-base.md` (shared base) or `persona-prod-weighted-addendum.md` (Mode 3) and re-run:

```bash
cd libs/tooluniverse/deploy && python3 assemble_prod_personas.py   # assemble + lint
```

The script exits nonzero on any hard failure (body over the 10 000 cap, an inline `[text](url)`
link, or a `get_skill("name")` that names no served `persona-<name>.md`). A short body only warns.

## Apply (manual)

1. Open the generated file. Copy **only the body** — everything *below* the `<!-- ... -->` header
   (the header documents the arm and does not count toward the 10 000-char Studio cap).
2. Studio → the agent's config → Persona → paste → Save, on `swiss-rockets.squirro.com`.
3. One arm per agent config (A and B are separate configs so they can be compared side by side).

## Verify by hand (no automated harness)

### Agent A — Neutral-tools
The question this arm answers: **does mere availability get the skills used?**
- [ ] Ask a biomedical question (e.g. "What is known about prostate cancer?"). Confirm the agent
      *spontaneously* reaches `find_skill` / `get_skill` / `find_tools` rather than answering from
      web alone — telemetry shows a TU tool call.
- [ ] Ask a plain public fact ("Who is the CEO of Pfizer?"). Confirm it stays in Transactional Mode
      (web, concise, footnoted) — the TU surface does not distort routine lookups.
- [ ] Confirm citations render as footnotes (`[^1]`), not inline links.

### Agent B — Weighted-skills (DSR-545)
- [ ] Fast-path rows route to the right `get_skill(name)` (disease → `disease-research`, mechanism →
      `drug-mechanism-research`, target → `drug-target-validation`, variant → `variant-interpretation`).
- [ ] A tail query with no fast-path row triggers `find_skill` first (no guessed skill name).
- [ ] An aggregate/landscape trial question ("how many Phase 2 trials target SSTR2?") does **not**
      route to `clinical-trial-matching` (which is per-patient).
- [ ] Web narrative still runs in parallel alongside a loaded skill body.
