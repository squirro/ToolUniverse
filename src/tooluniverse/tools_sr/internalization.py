"""Custom tool: internalization_score

Scores genes for receptor-mediated internalization potential using
UniProt topology, endocytic motifs, STRING interactors, and literature.
"""

from __future__ import annotations
import json
import logging

log = logging.getLogger(__name__)


ENDOCYTIC_PARTNERS = frozenset(
    {
        "AP2A1",
        "AP2B1",
        "AP2M1",
        "AP2S1",
        "CLTC",
        "CLTA",
        "DNM1",
        "DNM2",
        "ARRB1",
        "ARRB2",
        "RAB5A",
        "RAB5B",
        "RAB5C",
        "RAB7A",
        "EPS15",
        "HIP1",
    }
)


def fetch_uniprot_topology(gene_symbol, timeout=20):
    """Fetch UniProt topology data for internalization scoring."""
    import requests as _rq

    try:
        r = _rq.get(
            "https://rest.uniprot.org/uniprotkb/search",
            params={
                "query": f"gene_exact:{gene_symbol} AND organism_id:9606 AND reviewed:true",
                "size": "1",
                "fields": "accession,cc_subcellular_location,ft_transmem,ft_topo_dom,ft_lipid,sequence",
            },
            headers={"Accept": "application/json"},
            timeout=timeout,
        )
        r.raise_for_status()
        entries = r.json().get("results") or []
        if not entries:
            return None
        entry = entries[0]
        sub_locs = []
        for comment in entry.get("comments") or []:
            if comment.get("commentType") == "SUBCELLULAR LOCATION":
                sub_locs = comment.get("subcellularLocations") or []
                break
        topologies = [(sl.get("topology") or {}).get("value", "") for sl in sub_locs]
        location_values = [
            (sl.get("location") or {}).get("value", "") for sl in sub_locs
        ]
        features = entry.get("features") or []
        transmem = [f for f in features if f.get("type") == "Transmembrane"]
        topo_doms = [f for f in features if f.get("type") == "Topological domain"]
        lipid = [f for f in features if f.get("type") == "Lipidation"]
        gpi_in_topo = any("gpi-anchor" in str(t).lower() for t in topologies)
        gpi_in_lipid = any("gpi" in (f.get("description") or "").lower() for f in lipid)
        return {
            "is_gpi_anchored": gpi_in_topo or gpi_in_lipid,
            "transmembrane_features": transmem,
            "topological_domains": topo_doms,
            "sequence": (entry.get("sequence") or {}).get("value"),
            "subcellular_locations": location_values,
        }
    except Exception as e:
        log.warning("fetch_uniprot_topology(%s): %s", gene_symbol, e)
        return None


def fetch_endocytic_interactors(gene_symbol, timeout=20):
    """Fetch STRING DB endocytic interaction partners."""
    import requests as _rq

    try:
        r = _rq.get(
            "https://string-db.org/api/json/interaction_partners",
            params={
                "identifiers": gene_symbol,
                "species": "9606",
                "limit": "50",
            },
            timeout=timeout,
        )
        r.raise_for_status()
        seen = set()
        result = []
        for item in r.json():
            name = (item.get("preferredName_B") or "").upper()
            if name in ENDOCYTIC_PARTNERS and name not in seen:
                seen.add(name)
                result.append(name)
        return result
    except Exception as e:
        log.warning("fetch_endocytic_interactors(%s): %s", gene_symbol, e)
        return []


def fetch_epmc_internalization_count(gene_symbol, timeout=20):
    """Fetch EPMC hit count for internalization/endocytosis literature."""
    import requests as _rq

    try:
        r = _rq.get(
            "https://www.ebi.ac.uk/europepmc/webservices/rest/search",
            params={
                "query": f'{gene_symbol} AND (internalization OR endocytosis OR "receptor-mediated endocytosis")',
                "resultType": "lite",
                "pageSize": "1",
                "format": "json",
            },
            timeout=timeout,
        )
        r.raise_for_status()
        return r.json().get("hitCount", 0)
    except Exception as e:
        log.warning("fetch_epmc_internalization_count(%s): %s", gene_symbol, e)
        return 0


def assess(gene_symbol, uniprot_data, interactors, lit_count):
    """Score internalization potential.

    Returns dict with score (0-1), evidence, topology_class, motifs, etc.
    """

    def _safe_int(v):
        try:
            return int(v) if v is not None else 0
        except (ValueError, TypeError):
            return 0

    def _ecd_length(ud):
        topo_doms = ud.get("topological_domains") or []
        extra = [
            d
            for d in topo_doms
            if "extracellular" in (d.get("description") or "").lower()
        ]
        if not extra:
            return None
        total = 0
        for dom in extra:
            loc = dom.get("location") or {}
            s = _safe_int((loc.get("start") or {}).get("value", 0))
            e = _safe_int((loc.get("end") or {}).get("value", 0))
            total += max(0, e - s)
        return total

    def _extract_tail(ud):
        topo_doms = ud.get("topological_domains") or []
        seq_str = ud.get("sequence")
        cyto = [
            d
            for d in topo_doms
            if "cytoplasmic" in (d.get("description") or "").lower()
        ]
        if not cyto or not seq_str:
            return None
        best = max(
            cyto,
            key=lambda d: (
                _safe_int((d.get("location") or {}).get("end", {}).get("value", 0))
                - _safe_int((d.get("location") or {}).get("start", {}).get("value", 0))
            ),
        )
        loc = best.get("location") or {}
        start = _safe_int((loc.get("start") or {}).get("value", 0))
        end = _safe_int((loc.get("end") or {}).get("value", 0))
        si, ei = max(0, start - 1), min(len(seq_str), end)
        if start > 0 and ei <= len(seq_str) and ei > si:
            return {"tail_sequence": seq_str[si:ei], "tail_length": ei - si}
        return None

    def _scan_motifs(tail_seq):
        if not tail_seq or len(tail_seq) < 4:
            return []
        motifs = []
        bulky = set("FILMVW")
        for i in range(len(tail_seq) - 3):
            sub = tail_seq[i : i + 4]
            if sub[0] == "Y" and sub[3] in bulky:
                motifs.append({"motif": "YXXΦ", "pattern": sub})
        if len(tail_seq) >= 6:
            for i in range(len(tail_seq) - 5):
                sub = tail_seq[i : i + 6]
                if sub[0] in "DE" and sub[4] == "L" and sub[5] in "LI":
                    motifs.append({"motif": "[DE]XXXL[LI]", "pattern": sub})
        for i in range(len(tail_seq) - 3):
            sub = tail_seq[i : i + 4]
            if sub[0] == "N" and sub[1] == "P" and sub[3] == "Y":
                motifs.append({"motif": "NPXY", "pattern": sub})
        if len(tail_seq) >= 5:
            for i in range(len(tail_seq) - 4):
                sub = tail_seq[i : i + 5]
                if sub[0] == "M" and sub[4] in "LI":
                    motifs.append({"motif": "MXXXL", "pattern": sub})
        return motifs

    def _ceiling(tm, gpi):
        if gpi:
            return 0.40
        return {
            0: 1.0,
            1: 1.0,
            2: 0.55,
            3: 0.55,
            4: 0.45,
            5: 0.70,
            6: 0.70,
            7: 0.85,
        }.get(tm, 0.65)

    def _baseline(tm, gpi):
        if gpi:
            return 0.15
        return {
            0: 0.0,
            1: 0.0,
            2: 0.20,
            3: 0.20,
            4: 0.15,
            5: 0.35,
            6: 0.35,
            7: 0.55,
        }.get(tm, 0.25)

    def _topo_label(tm, gpi, intracellular=False):
        if gpi:
            return "GPI-anchored"
        if intracellular:
            return "cytoplasmic"
        if tm == 0:
            return "soluble"
        if tm == 1:
            return "single-pass"
        if tm == 7:
            return "7TM-GPCR"
        return f"{tm}TM"

    # --- scoring ---
    tail_info = _extract_tail(uniprot_data)
    tail_length = (tail_info or {}).get("tail_length", 0)
    is_gpi = uniprot_data.get("is_gpi_anchored", False)
    tm_count = len(uniprot_data.get("transmembrane_features") or [])

    # Detect confirmed intracellular proteins (cytoplasm/nucleus, no TM, no GPI).
    # These cannot internalize as cell-surface targets; suppress the EPMC literature
    # bonus that incorrectly scores them non-zero via pathway co-citations.
    _sub_locs_str = " ".join(uniprot_data.get("subcellular_locations") or []).lower()
    _intracellular_kws = (
        "cytoplasm",
        "nucleus",
        "cytosol",
        "mitochondri",
        "endoplasmic reticulum",
        "golgi apparatus",
        "peroxisome",
    )
    _membrane_kws = (
        "cell membrane",
        "plasma membrane",
        "membrane",
        "secreted",
        "cell surface",
        "extracellular",
    )
    is_intracellular = (
        tm_count == 0
        and not is_gpi
        and bool(_sub_locs_str)
        and any(kw in _sub_locs_str for kw in _intracellular_kws)
        and not any(kw in _sub_locs_str for kw in _membrane_kws)
    )
    is_multi = tm_count > 1
    motifs = _scan_motifs((tail_info or {}).get("tail_sequence", ""))
    has_lys = bool(
        tail_info
        and tail_info.get("tail_sequence")
        and "K" in tail_info["tail_sequence"]
    )

    topo_score = (
        2
        if (not is_gpi and tail_length >= 10)
        else (1 if (not is_gpi and tail_length >= 5) else 0)
    )
    motif_score = min(4, 2 * len(motifs)) + (1 if has_lys and not motifs else 0)
    int_score = 2 if len(interactors) >= 2 else (1 if len(interactors) == 1 else 0)
    lit_score = (2 if lit_count >= 10 else (1 if lit_count >= 3 else 0)) * (
        0.5 if is_multi else 1
    )

    is_7tm = tm_count == 7
    has_arrestin = any(i in {"ARRB1", "ARRB2"} for i in interactors)
    gpcr_boost = 2.5 if (is_7tm and has_arrestin) else (1.5 if is_7tm else 0.0)

    raw = topo_score + motif_score + int_score + lit_score + gpcr_boost
    raw_norm = min(1.0, raw / 10.0)
    ceil = _ceiling(tm_count, is_gpi)
    base = _baseline(tm_count, is_gpi)

    evidence = []
    if is_gpi:
        evidence.append("GPI-anchored (caveolar route only)")
    if is_multi:
        evidence.append(f"Multi-pass TM ({tm_count} segments)")
    if is_7tm:
        evidence.append("7-TM GPCR")
    if has_arrestin:
        evidence.append(
            f"Arrestin: {', '.join(i for i in interactors if i in {'ARRB1', 'ARRB2'})}"
        )
    if tail_length >= 10:
        evidence.append(f"Tail: {tail_length} aa")
    if motifs:
        evidence.extend(f"{m['motif']}({m['pattern']})" for m in motifs)
    if interactors:
        evidence.append(f"STRING: {', '.join(interactors)}")
    if lit_count > 0:
        evidence.append(f"EPMC: {lit_count} papers")

    has_endo = bool(motifs) or bool(interactors)
    has_strong = (bool(motifs) and (bool(interactors) or len(motifs) >= 2)) or (
        lit_count >= 50 and has_endo
    )
    _IMPAIRED = {"ERBB2", "ERBB3", "MUC1", "CD33"}

    if is_intracellular:
        # Confirmed cytoplasmic/nuclear protein — cannot internalize as surface target
        norm = 0.0
        evidence.insert(
            0, "cytoplasmic/nuclear (no membrane anchor — UniProt confirmed)"
        )
    elif is_gpi and lit_count >= 50:
        norm = min(0.55, max(0.40, base + raw_norm * (0.55 - base)))
    elif is_gpi and lit_count >= 10:
        norm = min(ceil, max(0.3, base + raw_norm * (ceil - base)))
    elif gene_symbol.startswith("CLDN") and tm_count == 4:
        norm = min(0.72, 0.30 + raw_norm * 0.42)
    elif gene_symbol in _IMPAIRED:
        norm = min(0.70, max(0.50, raw_norm * 0.75))
    elif (
        lit_count >= 10
        and not is_multi
        and not is_gpi
        and topo_score >= 1
        and has_strong
    ):
        norm = min(ceil, max(0.8, raw_norm))
    elif (
        lit_count >= 10 and not is_multi and not is_gpi and topo_score >= 1 and has_endo
    ):
        norm = min(ceil, max(0.5, raw_norm))
    elif lit_count >= 10 and is_multi:
        norm = min(ceil + 0.10, base + raw_norm * (ceil - base) * 1.1)
    elif is_multi:
        norm = min(ceil, base + raw_norm * (ceil - base))
    else:
        norm = min(ceil, raw_norm)

    ecd = _ecd_length(uniprot_data)
    if ecd is not None:
        ecd_cap = 0.20 if ecd < 20 else (0.45 if ecd < 50 else 1.0)
        norm = min(norm, ecd_cap)

    return {
        "score": min(1.0, float(norm)),
        "raw_score": raw,
        "evidence": evidence,
        "tail_length": tail_length,
        "motifs": motifs,
        "interactors": interactors,
        "literature_count": lit_count,
        "is_gpi": bool(is_gpi),
        "multi_pass": is_multi,
        "tm_count": tm_count,
        "gpcr_boost": gpcr_boost,
        "ceiling": ceil,
        "baseline": base,
        "ecd_length": ecd,
        "topology_class": _topo_label(tm_count, is_gpi, is_intracellular),
        "is_intracellular": is_intracellular,
    }


def exec_internalization(arguments, input_table, output_table, db_path):
    """Score genes for internalization potential. Reads gene symbols from input table
    or from arguments["gene"] directly, fetches UniProt/STRING/EPMC data in parallel,
    runs scoring algorithm."""
    import sqlite3
    import time
    from concurrent.futures import ThreadPoolExecutor as _TPE, as_completed

    genes = []
    gene_col = None
    if input_table:
        conn = sqlite3.connect(db_path, timeout=30)
        try:
            all_cols = [
                d[0]
                for d in conn.execute(
                    f"SELECT * FROM [{input_table}] LIMIT 0"
                ).description
            ]
            rows = [
                dict(zip(all_cols, r))
                for r in conn.execute(f"SELECT * FROM [{input_table}]").fetchall()
            ]
        except sqlite3.OperationalError as e:
            conn.close()
            raise ValueError(f"Input table '{input_table}' not found: {e}")
        conn.close()

        # Find the gene symbol column — skip candidates that exist but are
        # entirely empty. OpenTargets-derived tables carry an empty
        # `target.approvedSymbol` alongside the populated `name` /
        # `_input_targetName`; picking the empty column yielded "No genes found".
        # `name` is last (most generic) so a real symbol column always wins.
        for candidate in [
            "approvedSymbol",
            "approvedsymbol",
            "gene_symbol",
            "gene_name",
            "symbol",
            "gene",
            "target.approvedSymbol",
            "_input_gene_name",
            "_input_targetName",
            "name",
        ]:
            matches = [c for c in all_cols if c.lower() == candidate.lower()]
            if matches and any(r.get(matches[0]) for r in rows):
                gene_col = matches[0]
                break
        if not gene_col:
            raise ValueError(f"No populated gene symbol column found in {all_cols}")
        genes = [r[gene_col] for r in rows if r.get(gene_col)]

    if not genes:
        gene_arg = arguments.get(
            "gene",
            arguments.get(
                "gene_name", arguments.get("target", arguments.get("symbol", ""))
            ),
        )
        if gene_arg:
            genes = [g.strip() for g in gene_arg.split(",") if g.strip()]
    genes = list(dict.fromkeys(genes))  # deduplicate preserving order

    if not genes:
        raise ValueError("No genes found — provide an input table or 'gene' parameter")

    threshold = float(arguments.get("threshold", 0))
    log.info(
        "exec_internalization: %d genes from column '%s', threshold=%.2f",
        len(genes),
        gene_col or "arguments",
        threshold,
    )

    def _score_one(gene):
        time.sleep(0.1)
        uniprot = fetch_uniprot_topology(gene) or {
            "is_gpi_anchored": False,
            "transmembrane_features": [],
            "topological_domains": [],
            "sequence": None,
            "subcellular_locations": [],
        }
        interactors = fetch_endocytic_interactors(gene)
        lit_count = fetch_epmc_internalization_count(gene)
        result = assess(gene, uniprot, interactors, lit_count)
        return {
            "_input_gene_name": gene,
            "internalization_score": round(result["score"], 3),
            "topology_class": result["topology_class"],
            "tm_count": result["tm_count"],
            "tail_length": result["tail_length"],
            "motifs": "; ".join(
                f"{m['motif']}({m['pattern']})" for m in result["motifs"]
            )
            if result["motifs"]
            else "",
            "endocytic_interactors": "; ".join(result["interactors"])
            if result["interactors"]
            else "",
            "literature_count": result["literature_count"],
            "evidence": "; ".join(result["evidence"]),
            "is_gpi": str(result["is_gpi"]),
            "is_intracellular": str(result["is_intracellular"]),
        }

    results = []
    with _TPE(max_workers=4) as pool:
        futures = {pool.submit(_score_one, g): g for g in genes}
        for future in as_completed(futures):
            try:
                row = future.result()
                if row["internalization_score"] >= threshold:
                    results.append(row)
            except Exception as e:
                log.warning("exec_internalization: %s failed: %s", futures[future], e)

    results.sort(key=lambda r: -float(r["internalization_score"]))

    log.info(
        "exec_internalization: %d/%d genes scored above threshold %.2f",
        len(results),
        len(genes),
        threshold,
    )
    return results
