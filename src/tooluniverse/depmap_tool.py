# depmap_tool.py
"""
DepMap (Dependency Map) API tool for ToolUniverse.

DepMap provides cancer cell line dependency data from CRISPR knockout screens,
drug sensitivity data, and multi-omics characterization of cancer cell lines.

Data includes:
- CRISPR gene effect scores (gene essentiality)
- Drug sensitivity data
- Cell line metadata (lineage, mutations)
- Gene expression data

API Documentation: https://depmap.sanger.ac.uk/documentation/api/
Base URL: https://api.cellmodelpassports.sanger.ac.uk
"""

import requests
from statistics import median
from typing import Dict, Any, List, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool

# Base URL for Sanger Cell Model Passports API
DEPMAP_BASE_URL = "https://api.cellmodelpassports.sanger.ac.uk"


@register_tool("DepMapTool")
class DepMapTool(BaseTool):
    """
    Tool for querying DepMap/Sanger Cell Model Passports API.

    Provides access to:
    - Cancer cell line dependency data (CRISPR screens)
    - Drug sensitivity profiles
    - Cell line metadata and annotations
    - Gene effect scores for target validation

    No authentication required for non-commercial use.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.operation = tool_config.get("fields", {}).get(
            "operation", "get_cell_lines"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the DepMap API call."""
        operation = self.operation

        if operation == "get_cell_lines":
            return self._get_cell_lines(arguments)
        elif operation == "get_cell_line":
            return self._get_cell_line(arguments)
        elif operation == "search_cell_lines":
            return self._search_cell_lines(arguments)
        elif operation == "get_gene_dependencies":
            return self._get_gene_dependencies(arguments)
        elif operation == "get_drug_response":
            return self._get_drug_response(arguments)
        elif operation == "search_genes":
            return self._search_genes(arguments)
        else:
            return {"status": "error", "error": f"Unknown operation: {operation}"}

    def _get_cell_lines(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get list of cancer cell lines with metadata.

        Filter by tissue type or cancer type.
        """
        tissue = arguments.get("tissue")
        cancer_type = arguments.get("cancer_type")
        page_size = arguments.get("page_size", 20)

        try:
            url = f"{DEPMAP_BASE_URL}/models"
            params = {"page[size]": min(page_size, 100)}

            # Add filters if provided
            filters = []
            if tissue:
                filters.append(f"tissue:{tissue}")
            if cancer_type:
                filters.append(f"cancer_type:{cancer_type}")

            if filters:
                params["filter[model]"] = ",".join(filters)

            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            # Parse cell line data
            cell_lines = []
            for item in data.get("data", []):
                attrs = item.get("attributes", {})
                cell_lines.append(
                    {
                        "model_id": item.get("id"),
                        "model_name": attrs.get("model_name"),
                        "tissue": attrs.get("tissue"),
                        "cancer_type": attrs.get("cancer_type"),
                        "sample_site": attrs.get("sample_site"),
                        "gender": attrs.get("gender"),
                        "ethnicity": attrs.get("ethnicity"),
                    }
                )

            return {
                "status": "success",
                "data": {
                    "cell_lines": cell_lines,
                    "count": len(cell_lines),
                    "total": data.get("meta", {}).get("total", len(cell_lines)),
                },
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"DepMap API timeout after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"DepMap API request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _get_cell_line(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get detailed information for a specific cell line.

        Returns metadata, mutations, and available data types.
        """
        model_id = arguments.get("model_id")
        model_name = arguments.get("model_name")

        if not model_id and not model_name:
            return {
                "status": "error",
                "error": "Either model_id or model_name is required",
            }

        try:
            if model_id:
                url = f"{DEPMAP_BASE_URL}/models/{model_id}"
            else:
                # Search by name first
                search_result = self._search_cell_lines({"query": model_name})
                if (
                    search_result["status"] != "success"
                    or not search_result["data"]["cell_lines"]
                ):
                    return {
                        "status": "success",
                        "data": None,
                        "message": f"Cell line '{model_name}' not found",
                    }
                model_id = search_result["data"]["cell_lines"][0]["model_id"]
                url = f"{DEPMAP_BASE_URL}/models/{model_id}"

            response = requests.get(url, timeout=self.timeout)

            if response.status_code == 404:
                return {
                    "status": "success",
                    "data": None,
                    "message": f"Cell line not found: {model_id or model_name}",
                }

            response.raise_for_status()
            data = response.json()

            item = data.get("data", {})
            attrs = item.get("attributes", {})

            return {
                "status": "success",
                "data": {
                    "model_id": item.get("id"),
                    "model_name": attrs.get("model_name"),
                    "tissue": attrs.get("tissue"),
                    "cancer_type": attrs.get("cancer_type"),
                    "tissue_status": attrs.get("tissue_status"),
                    "sample_site": attrs.get("sample_site"),
                    "gender": attrs.get("gender"),
                    "ethnicity": attrs.get("ethnicity"),
                    "age_at_sampling": attrs.get("age_at_sampling"),
                    "growth_properties": attrs.get("growth_properties"),
                    "msi_status": attrs.get("msi_status"),
                    "ploidy": attrs.get("ploidy"),
                    "mutational_burden": attrs.get("mutational_burden"),
                },
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"DepMap API timeout after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"DepMap API request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _search_cell_lines(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search cell lines by name or identifier.
        """
        query = arguments.get("query")

        if not query:
            return {"status": "error", "error": "query parameter is required"}

        try:
            url = f"{DEPMAP_BASE_URL}/models"
            params = {"filter[model]": f"model_name:{query}", "page[size]": 20}

            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            cell_lines = []
            for item in data.get("data", []):
                attrs = item.get("attributes", {})
                cell_lines.append(
                    {
                        "model_id": item.get("id"),
                        "model_name": attrs.get("model_name"),
                        "tissue": attrs.get("tissue"),
                        "cancer_type": attrs.get("cancer_type"),
                    }
                )

            return {
                "status": "success",
                "data": {
                    "query": query,
                    "cell_lines": cell_lines,
                    "count": len(cell_lines),
                },
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"DepMap API timeout after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"DepMap API request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    # One page holds every screen today (1269); more are paged.
    _CRISPR_PAGE_SIZE = 2000
    _MOST_DEPENDENT_SHOWN = 10

    def _get_gene_dependencies(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        CRISPR knockout scores for one gene across the screened cancer lines.

        Reads `/genes/{id}/datasets/crispr_ko` (one row per screen, Sanger and
        Broad) and `/genes/{id}/essentiality_profiles`. A gene with no rows is
        an error that says so, never a success without numbers.
        """
        gene_symbol = arguments.get("gene_symbol")
        model_id = arguments.get("model_id")

        if not gene_symbol:
            return {"status": "error", "error": "gene_symbol parameter is required"}

        try:
            search_result = self._search_genes({"query": gene_symbol})
            if search_result.get("status") != "success":
                return search_result

            genes = search_result.get("data", {}).get("genes", [])
            matched = next((g for g in genes if g.get("exact_match")), None)
            if matched is None:
                similar = [g.get("symbol") for g in genes[:5]]
                return {
                    "status": "error",
                    "error": (
                        f"'{gene_symbol}' is not in the DepMap gene catalogue, so "
                        "there are no CRISPR scores for it."
                        + (f" Similar symbols: {similar}." if similar else "")
                    ),
                    "candidates": genes[:5],
                    "candidates_total": len(genes),
                }

            gene_id = matched["gene_id"]
            source_url = f"{DEPMAP_BASE_URL}/genes/{gene_id}/datasets/crispr_ko"
            rows, screens_total = self._crispr_rows(source_url)
            profiles = self._essentiality_profiles(gene_id)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"DepMap API timeout after {self.timeout}s",
                "retryable": True,
            }
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "error": f"DepMap API request failed: {type(e).__name__}: {e}",
                "retryable": True,
            }
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

        if model_id:
            rows = [r for r in rows if r["model_id"] == model_id]
        if not rows:
            where = f" in model {model_id}" if model_id else ""
            return {
                "status": "error",
                "error": (
                    f"DepMap has no CRISPR knockout rows for {gene_symbol} "
                    f"({gene_id}){where}: the gene was not screened, so its "
                    "dependency is unknown, not absent."
                ),
                "source_url": source_url,
                "screens_total": screens_total,
            }
        return {
            "status": "success",
            "data": self._summarise_crispr(
                gene_symbol, matched, model_id, rows, screens_total,
                profiles, source_url,
            ),
        }

    def _crispr_rows(self, url: str):
        """Every crispr_ko row for a gene, and the total the API reports.

        Pages by number: the API's `next` link drops `page[size]`.
        """
        rows: List[Dict[str, Any]] = []
        total = None
        number = 1
        while True:
            resp = requests.get(
                url,
                params={"page[size]": self._CRISPR_PAGE_SIZE, "page[number]": number},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            body = resp.json()
            if total is None:
                total = (body.get("meta") or {}).get("count")
            page = body.get("data") or []
            for item in page:
                attrs = item.get("attributes") or {}
                model = (item.get("relationships") or {}).get("model") or {}
                rows.append({
                    "model_id": (model.get("data") or {}).get("id"),
                    "source": attrs.get("source"),
                    "bf_scaled": attrs.get("bf_scaled"),
                    "fc_clean_qn": attrs.get("fc_clean_qn"),
                    "qc_pass": attrs.get("qc_pass"),
                })
            if not page or total is None or len(rows) >= total:
                break
            number += 1
        return rows, total if total is not None else len(rows)

    def _essentiality_profiles(self, gene_id: str) -> List[Dict[str, Any]]:
        resp = requests.get(
            f"{DEPMAP_BASE_URL}/genes/{gene_id}/essentiality_profiles",
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return [i.get("attributes") or {} for i in resp.json().get("data") or []]

    def _summarise_crispr(self, gene_symbol, matched, model_id, rows,
                          screens_total, profiles, source_url):
        def _stats(subset):
            bf = [r["bf_scaled"] for r in subset if r["bf_scaled"] is not None]
            fc = [r["fc_clean_qn"] for r in subset if r["fc_clean_qn"] is not None]
            dependent = sum(1 for v in bf if v < 0)
            return {
                "screens": len(subset),
                "dependent_screens": dependent,
                "dependent_fraction": round(dependent / len(bf), 3) if bf else None,
                "median_bf_scaled": round(median(bf), 3) if bf else None,
                "median_fc_clean_qn": round(median(fc), 3) if fc else None,
            }

        passed = [r for r in rows if r["qc_pass"] is not False]
        overall = _stats(passed)
        sources = sorted({r["source"] for r in passed if r["source"]})
        ranked = sorted(
            (r for r in passed if r["bf_scaled"] is not None),
            key=lambda r: r["bf_scaled"],
        )
        shown = ranked[: self._MOST_DEPENDENT_SHOWN]

        # Two profiles (Sanger, merged) can disagree; any "true" counts.
        flags = [str(p.get("common_essential")).lower() for p in profiles]
        common_essential = (
            True if "true" in flags else False if "false" in flags else None
        )
        tissue_specific = sorted({
            k[len("adm_status_"):]
            for p in profiles for k, v in p.items()
            if k.startswith("adm_status_") and v
        })

        return {
            "gene_symbol": gene_symbol,
            "gene_id": matched.get("gene_id"),
            "hgnc_id": matched.get("hgnc_id"),
            "model_id": model_id,
            "source_url": source_url,
            "screens_total": screens_total,
            "screens_held": len(rows),
            "screens_failing_qc": len(rows) - len(passed),
            **overall,
            "by_source": [
                {"source": s, **_stats([r for r in passed if r["source"] == s])}
                for s in sources
            ],
            "common_essential": common_essential,
            "core_fitness_pancan": any(p.get("core_fitness_pancan") for p in profiles),
            "tissue_specific_fitness": tissue_specific,
            "most_dependent": [
                {
                    **{k: r[k] for k in ("model_id", "source", "bf_scaled", "fc_clean_qn")},
                    "model_url": (
                        "https://cellmodelpassports.sanger.ac.uk/passports/"
                        f"{r['model_id']}"
                    ),
                }
                for r in shown
            ],
            "most_dependent_truncated": len(ranked) > len(shown),
            "note": (
                "Sanger Cell Model Passports CRISPR knockout screens (Sanger and "
                "Broad). bf_scaled: scaled Bayes factor, negative = the line "
                "depends on the gene (a screen counts as dependent below 0). "
                "fc_clean_qn: corrected log fold change, negative = depletion. "
                "Medians are over screens passing QC; most_dependent lists the "
                f"{len(shown)} lowest bf_scaled of {len(ranked)} scored screens. "
                "tissue_specific_fitness names tissues where the gene is a "
                "cancer-type-specific fitness gene."
            ),
        }

    def _search_genes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search for genes in DepMap by symbol.

        The Sanger Cell Model Passports API gene filter is limited,
        so this method fetches sorted gene batches and filters client-side.
        """
        query = arguments.get("query")

        if not query:
            return {"status": "error", "error": "query parameter is required"}

        try:
            # The Sanger API's filter[gene] param doesn't work for
            # exact symbol matching. Use sorted pagination + client filter.
            url = f"{DEPMAP_BASE_URL}/genes"
            params = {
                "sort": "symbol",
                "page[size]": 100,
            }

            # BINARY SEARCH over the sorted page space, not a scan from page 1.
            # The catalogue is ~45,750 symbols in ~458 pages; scanning the first
            # five saw only as far as "ABCD3" and then declared everything else
            # absent. Sorting is reliable and total, so ~9 requests locate any
            # symbol's page.
            genes = []
            query_upper = query.upper()
            page_size = int(params["page[size]"])

            def _page(number):
                params["page[number]"] = number
                resp = requests.get(url, params=params, timeout=self.timeout)
                resp.raise_for_status()
                return resp.json()

            first = _page(1)
            total = (first.get("meta") or {}).get("count") or 0
            last_page = max(1, -(-int(total) // page_size)) if total else 1

            # Find the first page whose LAST symbol is >= the query; that page,
            # and the one after it, hold every possible match.
            lo, hi = 1, last_page
            target_page = 1
            while lo <= hi:
                mid = (lo + hi) // 2
                rows = (_page(mid).get("data") or []) if mid != 1 else (
                    first.get("data") or []
                )
                if not rows:
                    hi = mid - 1
                    continue
                last_sym = str(
                    rows[-1].get("attributes", {}).get("symbol", "")
                ).upper()
                if last_sym < query_upper:
                    lo = mid + 1
                else:
                    target_page, hi = mid, mid - 1

            # A prefix match can straddle a page boundary, so read the located
            # page and its neighbour.
            for page_num in (target_page, target_page + 1):
                if page_num > last_page:
                    break
                data = first if page_num == 1 else _page(page_num)

                for item in data.get("data", []):
                    attrs = item.get("attributes", {})
                    symbol = attrs.get("symbol", "")
                    # Check for exact or prefix match
                    if symbol.upper() == query_upper or symbol.upper().startswith(
                        query_upper
                    ):
                        genes.append(
                            {
                                "gene_id": item.get("id"),
                                "symbol": symbol,
                                "name": attrs.get("name"),
                                "hgnc_id": attrs.get("hgnc_id"),
                                "ensembl_id": attrs.get("ensembl_gene_id"),
                                "exact_match": (symbol.upper() == query_upper),
                            }
                        )

                # If we found exact match(es), no need for more pages
                if any(g["exact_match"] for g in genes):
                    break

                # Still correct alongside the binary search, and saves the second
                # request: if this page already runs past every possible prefix
                # match, the neighbour cannot hold one.
                page_data = data.get("data", [])
                if page_data:
                    last_sym = page_data[-1].get("attributes", {}).get("symbol", "")
                    if last_sym.upper() > query_upper + "Z":
                        break

            # Sort: exact matches first
            genes.sort(
                key=lambda g: (
                    not g["exact_match"],
                    g.get("symbol", ""),
                )
            )

            if not genes:
                return {
                    "status": "success",
                    "data": {
                        "query": query,
                        "genes": [],
                        "count": 0,
                        "note": (
                            f"Gene '{query}' not found in DepMap "
                            "gene catalog. The Sanger Cell Model "
                            "Passports API has limited gene search. "
                            "Try using an Ensembl ID or check "
                            "depmap.org directly."
                        ),
                    },
                }

            return {
                "status": "success",
                "data": {
                    "query": query,
                    "genes": genes[:20],
                    "count": len(genes),
                },
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"DepMap API timeout after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "error": f"DepMap API request failed: {str(e)}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error: {str(e)}",
            }

    def _get_drug_response(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get drug sensitivity data for cell lines.

        Returns IC50/AUC values for drug-cell line combinations.
        """
        drug_name = arguments.get("drug_name")
        model_id = arguments.get("model_id")

        if not drug_name and not model_id:
            return {
                "status": "error",
                "error": "Either drug_name or model_id is required",
            }

        try:
            # Query drugs endpoint
            url = f"{DEPMAP_BASE_URL}/drugs"
            params = {"page[size]": 20}

            if drug_name:
                params["filter[drug]"] = f"drug_name:{drug_name}"

            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            drugs = []
            for item in data.get("data", []):
                attrs = item.get("attributes", {})
                drugs.append(
                    {
                        "drug_id": item.get("id"),
                        "drug_name": attrs.get("drug_name"),
                        "synonyms": attrs.get("synonyms"),
                        "targets": attrs.get("targets"),
                        "target_pathway": attrs.get("target_pathway"),
                    }
                )

            return {
                "status": "success",
                "data": {
                    "query": drug_name or model_id,
                    "drugs": drugs,
                    "count": len(drugs),
                    "note": "Drug sensitivity data (IC50, AUC) available through DepMap portal.",
                },
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"DepMap API timeout after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"DepMap API request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}
