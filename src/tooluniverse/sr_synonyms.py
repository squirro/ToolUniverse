"""Synonym expansion for biomedical search queries.

Combines multiple sources for comprehensive drug/intervention synonym coverage:
1. PubChem compound synonyms — alternate drug names, trade names
2. PubChem periodic table — element name ↔ symbol (terbium ↔ Tb)
3. Isotope variant generation — terbium-161 → 161Tb, Tb-161, Tb161, etc.
4. OLS ontology lookup — NCI Thesaurus, MeSH, EFO synonyms
5. NCI EVS — oncology-specific synonyms with children concepts

All sources use requests + stdlib only (no cross-module imports).
"""
from __future__ import annotations
import json, logging, re, threading

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# PubChem periodic table (element name ↔ symbol)
# ---------------------------------------------------------------------------

_elem_name_to_sym: dict[str, str] = {}
_elem_sym_to_name: dict[str, str] = {}
_table_lock = threading.Lock()
_table_loaded = False


def _load_periodic_table(timeout=10):
    """Fetch PubChem periodic table, populate element caches."""
    global _table_loaded
    import requests as _rq
    try:
        r = _rq.get("https://pubchem.ncbi.nlm.nih.gov/rest/pug/periodictable/JSON",
                     timeout=timeout)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        log.warning("periodic table load failed: %s", e)
        _table_loaded = True
        return
    for row in data.get("Table", {}).get("Row", []):
        cells = row.get("Cell", [])
        if isinstance(cells, list) and len(cells) >= 3:
            symbol = str(cells[1]).strip()
            name = str(cells[2]).strip()
            _elem_name_to_sym[name.lower()] = symbol
            _elem_sym_to_name[symbol.lower()] = name.lower()
    _table_loaded = True
    log.info("periodic table: %d elements", len(_elem_name_to_sym))


def _ensure_table():
    with _table_lock:
        if not _table_loaded:
            _load_periodic_table()


def element_symbol(name):
    """Return element symbol for a name, or None. E.g. 'terbium' → 'Tb'."""
    _ensure_table()
    return _elem_name_to_sym.get(name.lower())


def element_name(symbol):
    """Return element name for a symbol, or None. E.g. 'Tb' → 'terbium'."""
    _ensure_table()
    return _elem_sym_to_name.get(symbol.lower())


# ---------------------------------------------------------------------------
# Isotope variant generation
# ---------------------------------------------------------------------------

_ISOTOPE_RE = re.compile(
    r"(?P<name>[A-Za-z]+)[- ]?(?P<mass>\d{1,3})$|"
    r"(?P<mass2>\d{1,3})[- ]?(?P<name2>[A-Za-z]+)$"
)


def generate_isotope_variants(term):
    """Generate all common notations for an isotope term.

    'terbium-161' → ['terbium-161', 'terbium 161', '161Tb', 'Tb-161',
                      'Tb161', '161-Tb', 'terbium161', '161terbium']
    '161Tb'       → ['161Tb', 'Tb-161', 'terbium-161', 'terbium 161', ...]
    """
    term = term.strip()
    m = _ISOTOPE_RE.match(term)
    if not m:
        return []

    name = (m.group("name") or m.group("name2") or "").strip()
    mass = (m.group("mass") or m.group("mass2") or "").strip()
    if not name or not mass:
        return []

    # Resolve element name ↔ symbol
    sym = element_symbol(name)
    full_name = element_name(name) if not sym else None
    if sym:
        full_name = name.lower()
        short = sym
    elif full_name:
        short = name  # input was the symbol
        # But capitalize properly
        short = name[0].upper() + name[1:].lower() if len(name) > 1 else name.upper()
    else:
        # Not a recognized element — still generate notation variants
        short = name
        full_name = name.lower()

    if sym:
        short = sym  # proper capitalization from periodic table

    variants = set()
    # Element name variants
    variants.add(f"{full_name}-{mass}")
    variants.add(f"{full_name} {mass}")
    variants.add(f"{mass}{full_name}")
    variants.add(f"{mass}-{full_name}")
    # Symbol variants
    variants.add(f"{short}-{mass}")
    variants.add(f"{short}{mass}")
    variants.add(f"{mass}{short}")
    variants.add(f"{mass}-{short}")
    # Capitalized full name
    cap_name = full_name.capitalize()
    variants.add(f"{cap_name}-{mass}")
    variants.add(f"{cap_name} {mass}")

    # Remove the original to avoid duplication when caller prepends it
    variants.discard(term)
    return sorted(variants)


def detect_isotope(term):
    """Check if a term looks like an isotope reference.

    Returns (element_or_symbol, mass_number) or None.
    """
    m = _ISOTOPE_RE.match(term.strip())
    if not m:
        return None
    name = (m.group("name") or m.group("name2") or "").strip()
    mass = (m.group("mass") or m.group("mass2") or "").strip()
    if not name or not mass:
        return None
    # Validate: mass number should be reasonable for isotopes (3-300)
    # Below 3 catches false positives like SSTR2, BRCA1
    try:
        mn = int(mass)
        if mn < 3 or mn > 300:
            return None
    except ValueError:
        return None
    return (name, mass)


# ---------------------------------------------------------------------------
# PubChem compound synonyms
# ---------------------------------------------------------------------------

def fetch_pubchem_synonyms(name, timeout=10, max_synonyms=20):
    """Fetch alternate names for a compound from PubChem.

    Filters out IUPAC names, CAS numbers, internal IDs.
    """
    import requests as _rq
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{name}/synonyms/JSON"
    try:
        r = _rq.get(url, timeout=timeout)
        if r.status_code == 404:
            return []  # compound not found
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        log.warning("pubchem synonyms(%s): %s", name, e)
        return []

    info_list = data.get("InformationList", {}).get("Information", [])
    if not info_list:
        return []

    raw = info_list[0].get("Synonym", [])
    result = []
    for syn in raw:
        syn = syn.strip()
        if not syn or len(syn) > 60:
            continue
        if re.fullmatch(r"[\d\-]+", syn):
            continue
        if re.match(r"(RefChem|DTXSID|SCHEMBL|CHEBI:|NSC-|UNII|BRN |InChI)", syn):
            continue
        result.append(syn)
        if len(result) >= max_synonyms:
            break
    return result


# ---------------------------------------------------------------------------
# OLS ontology lookup (NCI Thesaurus, MeSH, EFO)
# ---------------------------------------------------------------------------

def _text_relevant(query_term, text):
    """Check if text relates to query via token overlap or substring match."""
    if not query_term or not text or len(text.strip()) <= 2:
        return False
    ql = query_term.lower()
    tl = text.lower()
    qtoks = set(ql.split())
    ttoks = set(tl.split())
    overlap = len(qtoks & ttoks)
    token_match = overlap > len(qtoks) * 2 / 3

    ql_c = re.sub(r"[\s\-]+", "", ql)
    tl_c = re.sub(r"[\s\-]+", "", tl)
    substring_match = len(text.split()) >= 2 and (ql_c in tl_c or tl_c in ql_c)

    return token_match or substring_match


def _concept_relevant(query, texts):
    return any(_text_relevant(query, t) for t in texts if t)


def _noise_term(s):
    if re.search(r"(?i)-induced|-related|-associated", s):
        return True
    if re.search(r"(?i)toxicity|adverse|benefit", s):
        return True
    if re.search(r"(?i)itis$|osis$|emia$", s):
        return True
    return False


def fetch_ols_synonyms(term, timeout=20):
    """Search OLS (EMBL-EBI) for synonyms from NCI, MeSH, EFO ontologies."""
    import requests as _rq
    all_terms = []
    for exact in ("true", "false"):
        try:
            r = _rq.get("https://www.ebi.ac.uk/ols4/api/search", params={
                "q": term, "rows": "10", "exact": exact,
                "ontology": "ncit,mesh,efo",
            }, timeout=timeout)
            r.raise_for_status()
            docs = r.json().get("response", {}).get("docs", [])
        except Exception as e:
            log.warning("OLS(%s, exact=%s): %s", term, exact, e)
            continue

        for doc in docs:
            label = doc.get("label", "")
            syns = doc.get("synonym", []) or []
            if _concept_relevant(term, [label] + syns):
                if label:
                    all_terms.append(label)
                all_terms.extend(s for s in syns if s)

    return list(dict.fromkeys(all_terms))  # dedupe, preserve order


def fetch_ncit_synonyms(term, timeout=20):
    """Search NCI EVS for oncology-specific synonyms."""
    import requests as _rq
    try:
        r = _rq.get("https://api-evsrest.nci.nih.gov/api/v1/concept/ncit/search", params={
            "term": term, "pageSize": "5",
            "include": "synonyms,children",
        }, timeout=timeout)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        log.warning("NCI EVS(%s): %s", term, e)
        return []

    all_terms = []
    for concept in data.get("concepts", []):
        cname = concept.get("name", "")
        syns = [s.get("name", "") for s in (concept.get("synonyms") or [])]
        if _concept_relevant(term, [cname] + syns):
            if cname:
                all_terms.append(cname)
            all_terms.extend(s for s in syns if s and not _noise_term(s))
            for child in concept.get("children") or []:
                cn = child.get("name", "")
                if cn and not _noise_term(cn):
                    all_terms.append(cn)

    return list(dict.fromkeys(all_terms))


# ---------------------------------------------------------------------------
# Main expansion API
# ---------------------------------------------------------------------------

def expand_synonyms(term, timeout=15, max_terms=15):
    """Expand a drug/intervention/target term into search synonyms.

    Combines: PubChem compound synonyms, periodic table element ↔ symbol,
    isotope variant generation, OLS ontology, NCI EVS.

    Returns deduplicated list (original term first), max 15 terms.
    """
    from concurrent.futures import ThreadPoolExecutor as _TPE, as_completed

    log.info("expand_synonyms: '%s'", term)
    results = {"pubchem": [], "ols": [], "ncit": [], "isotope": []}

    # Isotope variants (instant, no API)
    iso = detect_isotope(term)
    if iso:
        results["isotope"] = generate_isotope_variants(term)
        # Also expand the element full name (but NOT bare short symbols like
        # "Tb" — too ambiguous, matches "TB" = targeted biopsy, tuberculosis)
        name_part = iso[0]
        sym = element_symbol(name_part)
        full = element_name(name_part)
        if full:
            results["isotope"].append(full)
        # Only add bare symbol if ≥3 chars (e.g. "Lut" would be ok, "Tb" is not)
        if sym and len(sym) >= 3:
            results["isotope"].append(sym)
    else:
        # Check if term itself is a bare element name/symbol (no mass number)
        sym = element_symbol(term)
        full = element_name(term)
        if sym or full:
            resolved_name = full or term.lower()
            # Don't add bare short symbols — too ambiguous
            results["isotope"] = []

    # Parallel API calls
    with _TPE(max_workers=3) as pool:
        futures = {
            pool.submit(fetch_pubchem_synonyms, term, timeout): "pubchem",
            pool.submit(fetch_ols_synonyms, term, timeout): "ols",
            pool.submit(fetch_ncit_synonyms, term, timeout): "ncit",
        }
        for future in as_completed(futures):
            source = futures[future]
            try:
                results[source] = future.result()
            except Exception as e:
                log.warning("expand_synonyms %s failed: %s", source, e)

    # Isotope discovery: scan ALL collected synonyms for isotope patterns.
    # If we find any (e.g. PubChem returns "Terbium-159" for "terbium"),
    # query PubChem for other isotopes of the same element to discover
    # medical isotopes (e.g. "terbium-161" → "161Tb", "Tb-161").
    all_collected = results["isotope"] + results["ncit"] + results["ols"] + results["pubchem"]
    discovered_elements = set()
    for syn in all_collected:
        iso_check = detect_isotope(syn)
        if iso_check:
            elem = iso_check[0].lower()
            full_elem = element_name(elem) or element_symbol(elem)
            if full_elem:
                discovered_elements.add(element_name(elem) or elem)
            else:
                discovered_elements.add(elem)

    # For each discovered element, fetch PubChem synonyms for known isotope
    # compounds. PubChem has separate compound entries per isotope
    # (e.g. "terbium-161" is CID 12501904 with synonyms "161Tb", "Tb-161").
    isotope_enriched = list(results["isotope"])
    for elem in discovered_elements:
        # Get the list of synonyms from the original element PubChem result
        # and find all mass numbers mentioned
        found_masses = set()
        for syn in all_collected:
            iso_check = detect_isotope(syn)
            if iso_check and iso_check[0].lower() == elem:
                found_masses.add(iso_check[1])
        # Query PubChem for each isotope compound — they return the notations
        for mass in found_masses:
            isotope_term = f"{elem}-{mass}"
            if isotope_term.lower() == term.lower():
                continue  # already the original query
            iso_syns = fetch_pubchem_synonyms(isotope_term, timeout=min(timeout, 8))
            for s in iso_syns:
                iso_detected = detect_isotope(s)
                if iso_detected:
                    isotope_enriched.extend(generate_isotope_variants(s))
                elif len(s) < 30:
                    isotope_enriched.append(s)
        # Also try querying PubChem for nearby mass numbers
        # that weren't in the original synonyms. PubChem compound lookup
        # returns 404 if the isotope doesn't exist as a compound.
        sym = element_symbol(elem)
        if sym:
            checked_masses = set(found_masses)
            for known_mass in found_masses:
                # Prioritize heavier isotopes (radioactive/medical)
                for delta in [1, 2, 3, 4, 5, -1, -2]:
                    test_mass = str(int(known_mass) + delta)
                    if test_mass in checked_masses:
                        continue
                    checked_masses.add(test_mass)
                    test_term = f"{elem}-{test_mass}"
                    test_syns = fetch_pubchem_synonyms(test_term, timeout=min(timeout, 5))
                    if test_syns:
                        log.info("isotope discovery: found %s via PubChem", test_term)
                        # Only add the isotope notation variants, not all PubChem cruft
                        for s in test_syns:
                            iso_d = detect_isotope(s)
                            if iso_d:
                                isotope_enriched.extend(generate_isotope_variants(s))
                                break  # one isotope synonym is enough to generate all variants
    results["isotope"] = isotope_enriched

    # Merge: original first, isotope variants, NCI (most precise), OLS, PubChem
    all_terms = [term] + results["isotope"] + results["ncit"] + results["ols"] + results["pubchem"]

    # Deduplicate, filter noise
    seen = set()
    clean = []
    for t in all_terms:
        t = t.strip()
        if not t or len(t) < 2:
            continue
        key = t.lower()
        if key in seen:
            continue
        if t != term and _noise_term(t):
            continue
        if "/" in t and t != term:
            continue
        seen.add(key)
        clean.append(t)

    log.info("expand_synonyms: '%s' → %d terms", term, len(clean))
    return clean[:max_terms]
