# faers_analytics_tool.py

import os
import requests
import math
from typing import Dict, Any, List, Tuple
from .base_tool import BaseTool
from .tool_registry import register_tool

FDA_BASE_URL = "https://api.fda.gov/drug/event.json"

# openFDA caps a count request at 1000 terms and rejects more with HTTP 400. It
# also refuses limit>100 outright (403 API_KEY_MISSING) unless the caller is
# authenticated, so the limit and the key have to travel together.
COUNT_PAGE_MAX = 1000


@register_tool("FAERSAnalyticsTool")
class FAERSAnalyticsTool(BaseTool):
    """
    FAERS Analytics Tool for statistical signal detection in adverse event data.

    Provides:
    - Disproportionality analysis (ROR, PRR, IC, EBGM)
    - Demographic stratification
    - Serious event filtering
    - Drug comparison
    - Temporal trend analysis
    - MedDRA hierarchy rollups
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to analytics operation."""
        # Normalize aliases
        if not arguments.get("adverse_event") and arguments.get("reaction"):
            arguments = dict(arguments, adverse_event=arguments["reaction"])
        if not arguments.get("stratify_by") and arguments.get("demographic"):
            arguments = dict(arguments, stratify_by=arguments["demographic"])
        # Normalize drug_name aliases: 'drug' → 'drug_name'
        if not arguments.get("drug_name") and arguments.get("drug"):
            arguments = dict(arguments, drug_name=arguments["drug"])
        # Normalize seriousness_type alias: 'event_type' → 'seriousness_type'
        if not arguments.get("seriousness_type") and arguments.get("event_type"):
            arguments = dict(arguments, seriousness_type=arguments["event_type"])
        # Normalize compare_drugs alias: 'drugs' list → 'drug1', 'drug2'
        if arguments.get("drugs") and not arguments.get("drug1"):
            drugs_list = arguments["drugs"]
            if isinstance(drugs_list, list) and len(drugs_list) >= 2:
                arguments = dict(arguments, drug1=drugs_list[0], drug2=drugs_list[1])
        # Normalize stratify_by: 'age_group' → 'age'
        if arguments.get("stratify_by") == "age_group":
            arguments = dict(arguments, stratify_by="age")
        operation = arguments.get("operation")
        # Auto-fill operation from tool config const if not provided by user
        if not operation:
            operation = self.get_schema_const_operation()

        if not operation:
            return {"status": "error", "error": "Missing required parameter: operation"}

        if operation == "calculate_disproportionality":
            operation_result = self._calculate_disproportionality(arguments)
        elif operation == "stratify_by_demographics":
            operation_result = self._stratify_by_demographics(arguments)
        elif operation == "filter_serious_events":
            operation_result = self._filter_serious_events(arguments)
        elif operation == "compare_drugs":
            operation_result = self._compare_drugs(arguments)
        elif operation == "analyze_temporal_trends":
            operation_result = self._analyze_temporal_trends(arguments)
        elif operation == "rollup_meddra_hierarchy":
            operation_result = self._rollup_meddra_hierarchy(arguments)
        else:
            return {"status": "error", "error": f"Unknown operation: {operation}"}

        return self._with_data_payload(operation_result)

    def _with_data_payload(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure successful operation responses include a standardized data wrapper."""
        if not isinstance(result, dict):
            return {"status": "success", "data": {"value": result}, "value": result}

        if result.get("status") != "success":
            return result

        if "data" in result:
            return result

        # Feature-81A-004: move non-status keys into data to avoid duplicating
        # every field at both the top level and inside data.
        data = {k: v for k, v in result.items() if k != "status"}
        return {"status": "success", "data": data}

    def _calculate_disproportionality(
        self, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculate disproportionality measures (ROR, PRR, IC) with 95% confidence intervals.

        Uses 2x2 contingency table:
                    Event+    Event-
        Drug+         a         b
        Drug-         c         d
        """
        try:
            drug_name = arguments.get("drug_name")
            adverse_event = arguments.get("adverse_event")

            if not drug_name or not adverse_event:
                return {
                    "status": "error",
                    "error": "Must provide drug_name and adverse_event",
                }

            # Resolve the drug ONCE, and remember which field knew it, so every
            # count below describes the same population and the envelope can say
            # which one. Searching only generic_name reported a brand name as no
            # data at all.
            resolved_field, drug_total = self._resolve_drug_field(drug_name)

            # Every drug query below carries the field EXPLICITLY. Passing it via
            # self would share it with concurrent calls on the same cached tool
            # instance, which is what made b come back as exactly -a (DSR-693).
            # a = drug + event
            a = self._get_faers_count(drug_name, adverse_event, field=resolved_field)

            # b = drug + no event (all drug reports - drug+event)
            drug_reports = self._get_faers_count(
                drug_name, None, field=resolved_field
            )
            b = drug_reports - a

            # c = no drug + event (all event reports - drug+event)
            event_reports = self._get_faers_count(None, adverse_event)
            c = event_reports - a

            # d = no drug + no event (total - a - b - c)
            total = self._get_faers_total_count()
            d = total - a - b - c

            # A drug cannot have fewer reports than one of its own reactions. If
            # that happens the two queries disagreed — say so, rather than
            # reporting a negative cell as "insufficient data".
            if drug_reports < a or event_reports < a:
                return {
                    "status": "error",
                    "error": (
                        "Inconsistent counts from openFDA: the joint count "
                        f"({a}) exceeds a marginal total (drug {drug_reports}, "
                        f"event {event_reports}). The queries disagreed; no "
                        "disproportionality was computed."
                    ),
                    "counts": {
                        "drug_and_event": a,
                        "drug_total": drug_reports,
                        "event_total": event_reports,
                        "field": resolved_field,
                    },
                }

            # Check for valid counts
            if a <= 0 or b <= 0 or c <= 0 or d <= 0:
                return {
                    "status": "error",
                    "error": f"Insufficient data: a={a}, b={b}, c={c}, d={d}. Need all counts > 0 for analysis.",
                    "contingency_table": {"a": a, "b": b, "c": c, "d": d},
                }

            # Calculate ROR (Reporting Odds Ratio)
            ror = (a / b) / (c / d) if b > 0 and d > 0 else None

            # Same analysis over the UNION of every spelling openFDA knows. This
            # is a different cohort, not a better one -- reporting both is what
            # stops a quoted ROR being ambiguous about which population it
            # describes. Costs two extra calls: c and d derive from a.
            sensitivity = self._population_sensitivity(
                drug_name, adverse_event, resolved_field, ror, a, total
            )
            ror_ci = self._calculate_ror_ci(a, b, c, d) if ror else None

            # Calculate PRR (Proportional Reporting Ratio)
            prr = (a / (a + b)) / (c / (c + d)) if (a + b) > 0 and (c + d) > 0 else None
            prr_ci = self._calculate_prr_ci(a, b, c, d) if prr else None

            # Calculate IC (Information Component)
            ic = self._calculate_ic(a, b, c, d)
            ic_ci = self._calculate_ic_ci(a, b, c, d) if ic is not None else None

            # Determine signal strength
            signal_detected = False
            signal_strength = "No signal"

            if ror and ror_ci:
                if ror_ci["lower"] > 1.0 and a >= 3:  # Standard threshold
                    signal_detected = True
                    if ror >= 4.0:
                        signal_strength = "Strong signal"
                    elif ror >= 2.0:
                        signal_strength = "Moderate signal"
                    else:
                        signal_strength = "Weak signal"

            return {
                "status": "success",
                "drug_name": drug_name,
                "adverse_event": adverse_event,
                # Which population this statistic actually describes. Without it
                # a reader cannot tell a brand-only cohort from the union of every
                # reported spelling -- and for this drug that is the difference
                # between ROR 7.2 and 12.0.
                "case_definition": {
                    "query_term": drug_name,
                    "resolved_field": resolved_field,
                    "drug_report_total": drug_total,
                    "note": (
                        "PRIMARY analysis: reports matched on this single openFDA "
                        "field (the narrow population). See population_sensitivity "
                        "for the same analysis over the union of every spelling."
                    ),
                },
                "population_sensitivity": sensitivity,
                "contingency_table": {
                    "a_drug_and_event": a,
                    "b_drug_no_event": b,
                    "c_no_drug_event": c,
                    "d_no_drug_no_event": d,
                },
                "metrics": {
                    "ROR": {
                        "value": round(ror, 3) if ror else None,
                        "ci_95_lower": round(ror_ci["lower"], 3) if ror_ci else None,
                        "ci_95_upper": round(ror_ci["upper"], 3) if ror_ci else None,
                        "interpretation": "Reporting odds ratio - measures association strength",
                    },
                    "PRR": {
                        "value": round(prr, 3) if prr else None,
                        "ci_95_lower": round(prr_ci["lower"], 3) if prr_ci else None,
                        "ci_95_upper": round(prr_ci["upper"], 3) if prr_ci else None,
                        "interpretation": "Proportional reporting ratio - probability ratio",
                    },
                    "IC": {
                        "value": round(ic, 3) if ic is not None else None,
                        "ci_95_lower": round(ic_ci["lower"], 3) if ic_ci else None,
                        "ci_95_upper": round(ic_ci["upper"], 3) if ic_ci else None,
                        "interpretation": "Information component - Bayesian measure",
                    },
                },
                "signal_detection": {
                    "signal_detected": signal_detected,
                    "signal_strength": signal_strength,
                    "criteria": "ROR lower CI > 1.0 and case count >= 3",
                },
                "note": "Disproportionality analysis indicates potential safety signal. Does NOT prove causation. Requires clinical evaluation.",
            }

        except Exception as e:
            return {
                "status": "error",
                "error": f"Disproportionality calculation failed: {str(e)}",
            }

    def _stratify_by_demographics(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Stratify adverse event data by demographics (age, sex, country)."""
        try:
            drug_name = arguments.get("drug_name")
            adverse_event = arguments.get("adverse_event")
            stratify_by = arguments.get("stratify_by", "sex")  # sex, age, country

            if not drug_name:
                return {
                    "status": "error",
                    "error": "Must provide drug_name",
                }

            if stratify_by not in ["sex", "age", "country"]:
                return {
                    "status": "error",
                    "error": "stratify_by must be 'sex', 'age', or 'country'",
                }

            # Map stratification to FAERS fields
            field_map = {
                "sex": "patient.patientsex",
                "age": "patient.patientagegroup",
                "country": "occurcountry",
            }

            count_field = field_map[stratify_by]

            # Feature-121A-003: adverse_event is optional — filter by drug alone if omitted
            if adverse_event:
                base_query = f'patient.drug.openfda.generic_name:"{drug_name}"+AND+patient.reaction.reactionmeddrapt:"{adverse_event}"'
            else:
                base_query = f'patient.drug.openfda.generic_name:"{drug_name}"'

            url = self._count_url(base_query, count_field)

            response = requests.get(url, timeout=30)
            response.raise_for_status()

            data = response.json()
            results = data.get("results", [])
            truncated = self._truncation_note(results)

            # Format stratified data
            stratified_data = []
            total_count = sum(r.get("count", 0) for r in results)

            for result in results:
                term = result.get("term", "Unknown")
                count = result.get("count", 0)
                percentage = (count / total_count * 100) if total_count > 0 else 0

                # Interpret codes (API returns integers; normalize to str for dict lookup)
                term_key = str(term)
                if stratify_by == "sex":
                    term = {"0": "Unknown", "1": "Male", "2": "Female"}.get(
                        term_key, term
                    )
                elif stratify_by == "age":
                    age_map = {
                        "1": "Neonate",
                        "2": "Infant",
                        "3": "Child",
                        "4": "Adolescent",
                        "5": "Adult",
                        "6": "Elderly",
                    }
                    term = age_map.get(term_key, term)

                stratified_data.append(
                    {"group": term, "count": count, "percentage": round(percentage, 2)}
                )

            payload: Dict[str, Any] = {
                "status": "success",
                "drug_name": drug_name,
                "adverse_event": adverse_event,
                "stratified_by": stratify_by,
                "total_reports": total_count,
                "stratification": sorted(
                    stratified_data, key=lambda x: x["count"], reverse=True
                ),
            }
            if truncated:
                payload["truncation_warning"] = truncated
            return payload

        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"API request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Stratification failed: {str(e)}"}

    def _filter_serious_events(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Filter for serious adverse events (death, hospitalization, disability, life-threatening)."""
        try:
            drug_name = arguments.get("drug_name")
            adverse_event = arguments.get("adverse_event")
            seriousness_type = arguments.get(
                "seriousness_type", "all"
            )  # all, death, hospitalization, disability, life_threatening

            if not drug_name:
                return {"status": "error", "error": "Must provide drug_name"}

            # Build query for serious events
            base_query = f'patient.drug.openfda.generic_name:"{drug_name}"'

            # Add specific reaction filter if provided
            if adverse_event:
                base_query += (
                    f'+AND+patient.reaction.reactionmeddrapt:"{adverse_event}"'
                )

            # Add seriousness filter
            seriousness_map = {
                "all": "+AND+serious:1",
                "death": "+AND+seriousnessdeath:1",
                "hospitalization": "+AND+seriousnesshospitalization:1",
                "disability": "+AND+seriousnessdisabling:1",
                "life_threatening": "+AND+seriousnesslifethreatening:1",
            }

            if seriousness_type not in seriousness_map:
                return {
                    "status": "error",
                    "error": f"Invalid seriousness_type. Must be one of: {list(seriousness_map.keys())}",
                }

            search_query = base_query + seriousness_map[seriousness_type]

            # Get top reactions for serious events
            url = self._count_url(
                search_query, "patient.reaction.reactionmeddrapt.exact"
            )

            response = requests.get(url, timeout=30)
            response.raise_for_status()

            data = response.json()
            results = data.get("results", [])
            truncated = self._truncation_note(results)

            # Get total serious event count
            total_url = f"{FDA_BASE_URL}?search={search_query}&limit=1"
            total_response = requests.get(total_url, timeout=30)
            total_data = total_response.json()
            total_serious = (
                total_data.get("meta", {}).get("results", {}).get("total", 0)
            )

            # Format results
            serious_reactions = []
            for result in results[:20]:  # Top 20
                serious_reactions.append(
                    {"reaction": result.get("term"), "count": result.get("count")}
                )

            result: Dict[str, Any] = {
                "drug_name": drug_name,
                "seriousness_type": seriousness_type,
                "total_serious_events": total_serious,
                "top_serious_reactions": serious_reactions,
                "note": f"Serious events: {'All' if seriousness_type == 'all' else seriousness_type.replace('_', ' ')}",
            }
            if adverse_event:
                result["adverse_event_filter"] = adverse_event.upper()
            if truncated:
                result["truncation_warning"] = truncated
            return {"status": "success", "data": result}

        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"API request failed: {str(e)}"}
        except Exception as e:
            return {
                "status": "error",
                "error": f"Serious event filtering failed: {str(e)}",
            }

    def _compare_drugs(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Compare safety profiles of two drugs for the same adverse event."""
        try:
            drug1 = arguments.get("drug1")
            drug2 = arguments.get("drug2")
            adverse_event = arguments.get("adverse_event")

            if not drug1 or not drug2 or not adverse_event:
                return {
                    "status": "error",
                    "error": "Must provide drug1, drug2, and adverse_event",
                }

            # Calculate disproportionality for both drugs
            result1 = self._calculate_disproportionality(
                {
                    "operation": "calculate_disproportionality",
                    "drug_name": drug1,
                    "adverse_event": adverse_event,
                }
            )

            result2 = self._calculate_disproportionality(
                {
                    "operation": "calculate_disproportionality",
                    "drug_name": drug2,
                    "adverse_event": adverse_event,
                }
            )

            if result1.get("status") != "success" or result2.get("status") != "success":
                return {
                    "status": "error",
                    "error": "Failed to calculate metrics for one or both drugs",
                    "drug1_result": result1,
                    "drug2_result": result2,
                }

            # Extract ROR values
            ror1 = result1.get("metrics", {}).get("ROR", {}).get("value")
            ror2 = result2.get("metrics", {}).get("ROR", {}).get("value")

            # Determine which drug has stronger signal
            comparison = "Inconclusive"
            if ror1 and ror2:
                if ror1 > ror2 * 1.5:
                    comparison = f"{drug1} shows stronger signal than {drug2}"
                elif ror2 > ror1 * 1.5:
                    comparison = f"{drug2} shows stronger signal than {drug1}"
                else:
                    comparison = f"{drug1} and {drug2} show similar signals"

            return {
                "status": "success",
                "adverse_event": adverse_event,
                "drug1": {
                    "name": drug1,
                    "metrics": result1.get("metrics"),
                    "signal_detection": result1.get("signal_detection"),
                },
                "drug2": {
                    "name": drug2,
                    "metrics": result2.get("metrics"),
                    "signal_detection": result2.get("signal_detection"),
                },
                "comparison": comparison,
                "note": "Direct comparison of safety signals. Both drugs may show signals due to different baseline risks.",
            }

        except Exception as e:
            return {"status": "error", "error": f"Drug comparison failed: {str(e)}"}

    def _analyze_temporal_trends(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze temporal trends in adverse event reporting."""
        try:
            drug_name = arguments.get("drug_name")
            adverse_event = arguments.get("adverse_event")

            if not drug_name:
                return {"status": "error", "error": "Must provide drug_name"}

            # Build base query
            if adverse_event:
                search_query = f'patient.drug.openfda.generic_name:"{drug_name}"+AND+patient.reaction.reactionmeddrapt:"{adverse_event}"'
            else:
                search_query = f'patient.drug.openfda.generic_name:"{drug_name}"'

            # Get counts by receive date (year)
            url = self._count_url(search_query, "receivedate")

            response = requests.get(url, timeout=30)
            response.raise_for_status()

            data = response.json()
            results = data.get("results", [])
            truncated = self._truncation_note(results)

            # Parse and aggregate by year
            yearly_counts = {}
            for result in results:
                # OpenFDA count=receivedate returns "time" key, not "term"
                date_str = result.get("time") or result.get("term", "")
                if len(date_str) >= 4:
                    year = date_str[:4]
                    count = result.get("count", 0)
                    yearly_counts[year] = yearly_counts.get(year, 0) + count

            # Format temporal data
            temporal_data = [
                {"year": year, "count": count}
                for year, count in sorted(yearly_counts.items())
            ]

            # Calculate trend
            if len(temporal_data) >= 2:
                first_year_count = temporal_data[0]["count"]
                last_year_count = temporal_data[-1]["count"]
                percent_change = (
                    ((last_year_count - first_year_count) / first_year_count * 100)
                    if first_year_count > 0
                    else 0
                )
                trend = (
                    "Increasing"
                    if percent_change > 10
                    else ("Decreasing" if percent_change < -10 else "Stable")
                )
            else:
                percent_change = 0
                trend = "Insufficient data"

            return {
                "status": "success",
                "drug_name": drug_name,
                "adverse_event": adverse_event or "All events",
                "temporal_data": temporal_data,
                "trend_analysis": {
                    "trend": trend,
                    "percent_change": round(percent_change, 1),
                    "years_analyzed": len(temporal_data),
                },
                **({"truncation_warning": truncated} if truncated else {}),
                "note": "Temporal trends may reflect increased awareness, reporting, or actual incidence changes",
            }

        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"API request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Temporal analysis failed: {str(e)}"}

    def _rollup_meddra_hierarchy(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Aggregate adverse events by MedDRA hierarchy levels (PT → HLT → SOC)."""
        try:
            drug_name = arguments.get("drug_name")

            if not drug_name:
                return {"status": "error", "error": "Must provide drug_name"}

            # Get preferred term (PT) level reactions
            search_query = f'patient.drug.openfda.generic_name:"{drug_name}"'
            url = self._count_url(
                search_query, "patient.reaction.reactionmeddrapt.exact"
            )

            response = requests.get(url, timeout=30)
            response.raise_for_status()

            data = response.json()
            pt_results = data.get("results", [])
            truncated = self._truncation_note(pt_results)

            # Format PT level
            pt_level = [
                {"preferred_term": r.get("term"), "count": r.get("count")}
                for r in pt_results[:50]  # Top 50 PTs
            ]

            # Note: Full MedDRA hierarchy requires MedDRA license
            # FAERS API doesn't provide HLT/SOC directly

            return {
                "status": "success",
                "data": {
                    "drug_name": drug_name,
                    "meddra_hierarchy": {
                        "PT_level": pt_level,
                        # len(pt_level) here counted the 50-item display slice, so
                        # this always read 50 for any drug with 50+ PTs.
                        "total_unique_PTs": len(pt_results),
                    },
                    "note": "Full MedDRA hierarchy (HLT, SOC) requires MedDRA license. Showing Preferred Term (PT) level only.",
                    "recommendation": "Use MedDRA dictionary to map PTs to higher-level terms for system organ class analysis",
                    "pt_display_cap": (
                        f"showing top {len(pt_level)} of {len(pt_results)} "
                        "preferred terms returned"
                    ),
                    **({"truncation_warning": truncated} if truncated else {}),
                },
            }

        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"API request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"MedDRA rollup failed: {str(e)}"}

    # Helper methods for statistical calculations

    # Fields tried, in order, when turning a drug name into a query. `generic_name`
    # stays first so existing numbers do not move; the rest exist because a BRAND
    # name matched none of them before. Measured 2026-08-03:
    #   generic_name:"Lutathera"           -> 404, no match
    #   brand_name:"Lutathera"             -> 5,551
    #   medicinalproduct.exact:"LUTATHERA" -> 5,550
    DRUG_NAME_FIELDS = (
        "patient.drug.openfda.generic_name",
        "patient.drug.openfda.brand_name",
        "patient.drug.openfda.substance_name",
        "patient.drug.medicinalproduct.exact",
    )

    # openFDA's own name set for one drug entry, NDC-derived.
    _OPENFDA_NAME_KEYS = ("brand_name", "generic_name", "substance_name")

    @staticmethod
    def synonyms_from_openfda(openfda_block) -> List[str]:
        """Other names for the SAME product, taken from openFDA itself.

        Counting names across a whole report conflates synonyms with
        co-medications -- LUTATHERA's reports name LUTETIUM LU 177 DOTATATE 5,683
        times (the same product) and OCTREOTIDE 314 times (a drug the patient also
        took). Separating those by a co-occurrence threshold is a clinical
        judgement. The ``openfda`` block on the matched DRUG ENTRY avoids the
        question: it is the NDC-derived name set for that one product, so a
        co-medication cannot appear in it at all.

        Caveat worth knowing: only NDC-matched reports carry this block, so
        as-reported spellings that never mapped are NOT reachable this way.
        """
        if not openfda_block:
            return []
        seen = {}
        for key in FAERSAnalyticsTool._OPENFDA_NAME_KEYS:
            for name in openfda_block.get(key) or []:
                if name and name.upper() not in seen:
                    seen[name.upper()] = name.upper()
        return sorted(seen.values())

    @staticmethod
    def expand_terms(drug_name: str, openfda_block) -> List[str]:
        """The caller's term first, then the product's other names.

        The caller's own spelling anchors the list because it defines the narrow
        cohort that stays PRIMARY. Everything after it widens the union.
        """
        terms = [drug_name]
        for name in FAERSAnalyticsTool.synonyms_from_openfda(openfda_block):
            if name.upper() != drug_name.upper():
                terms.append(name)
        return terms

    @staticmethod
    def candidate_terms(field: str, drug_name: str) -> List[str]:
        """Spellings worth probing for one field.

        ``.exact`` fields are case-STRICT and FAERS stores product names
        uppercase, so `medicinalproduct.exact:"Lutathera"` is a 404 while
        `"LUTATHERA"` returns 5,682 reports. Every other field matches either
        casing, where a second probe would only cost a call.
        """
        terms = [drug_name]
        if field.endswith(".exact") and drug_name.upper() != drug_name:
            terms.append(drug_name.upper())
        return terms

    @staticmethod
    def population_queries(matches: List[Tuple[str, str]]) -> Dict[str, str]:
        """The two defensible cohorts, from ``(field, matched_term)`` pairs.

        The term travels with the field because they disagree: `brand_name`
        matches "Lutathera" while `medicinalproduct.exact` needs "LUTATHERA".

        NARROW is the first field that knew the drug -- historically the only one
        counted, and kept as the primary so published numbers do not move. UNION
        is every spelling openFDA recognises, OR'd together. They are different
        populations, and on LUTATHERA/myelodysplastic syndrome they disagree by
        29 vs 50 cases (ROR 7.2 vs 12.0), so the choice cannot be silent.

        With one matching field the two are identical, and callers must not imply
        a comparison that does not exist.
        """
        narrow = f'{matches[0][0]}:"{matches[0][1]}"'
        union = "+OR+".join(f'{f}:"{t}"' for f, t in matches)
        return {"narrow": narrow, "union": union}

    @staticmethod
    def divergence_note(primary: Dict[str, Any], sensitivity: Dict[str, Any]):
        """Flag a population choice that changes the conclusion, else None.

        Two things are material: the signal crossing ROR 1.0 (present under one
        cohort, absent under the other), and a ratio shift large enough to change
        how the number reads. A stable estimate is NOT flagged -- noise here would
        train the reader to ignore the field.
        """
        p, s = primary.get("ROR"), sensitivity.get("ROR")
        if p is None or s is None or p <= 0 or s <= 0:
            return None
        pc, sc = primary.get("cases") or 0, sensitivity.get("cases") or 0
        crosses = (p >= 1.0) != (s >= 1.0)
        ratio = max(p, s) / min(p, s)
        # Case count is judged alongside the ROR, not instead of it. Measured on
        # LUTATHERA/myelodysplastic syndrome, the union holds 48% more cases while
        # the ROR ratio is only 1.44 -- under a ROR-only gate that read as
        # agreement, which is the opposite of what a reader needs to know.
        case_shift = (max(pc, sc) / min(pc, sc)) if min(pc, sc) > 0 else 0
        if not crosses and ratio < 1.5 and case_shift < 1.2:
            return None
        if crosses:
            lead = "The signal changes DIRECTION across the two populations"
        elif ratio >= 1.5:
            lead = "The two populations disagree materially"
        else:
            lead = "The two populations rest on materially different case counts"
        return (
            f"{lead}: ROR {p} ({pc} cases) under the narrow definition vs "
            f"{s} ({sc} cases) under the union. Report which population any quoted "
            "number describes; the ROR 1.0 line is the no-signal boundary."
        )

    def _count_url(self, search_query: str, count_field: str) -> str:
        """A count URL asking for as many terms as this caller is allowed.

        Without ``FDA_API_KEY`` openFDA answers 403 to any ``limit`` above 100, so
        an unauthenticated caller must not send one at all: it would turn a
        working-but-truncated call into a failed one. Authenticated, the ceiling
        is 1000, which on a busy drug is ~29% more of the reaction distribution
        than the unasked-for default of 100.
        """
        url = f"{FDA_BASE_URL}?search={search_query}&count={count_field}"
        api_key = os.getenv("FDA_API_KEY")
        if api_key:
            url += f"&limit={COUNT_PAGE_MAX}&api_key={api_key}"
        return url

    def _truncation_note(self, results: List[Dict[str, Any]]):
        """Say so when the distribution was cut off, else None.

        A full page is evidence of truncation, not of completeness -- measured on
        LUTATHERA, the 1000th term still has count == 1, so terms remain beyond the
        cap. Reporting a capped distribution as the whole one is the same defect
        class as reporting a transport failure as a zero.
        """
        if len(results) < COUNT_PAGE_MAX:
            return None
        return (
            f"TRUNCATED: openFDA returned the maximum {COUNT_PAGE_MAX} terms, so "
            "rarer events beyond the cap are missing. Counts shown are a lower "
            "bound and the distribution is incomplete."
        )

    def _field_total(self, field: str, term: str):
        """Report total for one field, or None when that field does not match.

        None means "this field has nothing", which is different from a transport
        failure -- that is allowed to raise, so it cannot be mistaken for a zero.
        """
        url = f'{FDA_BASE_URL}?search={field}:"{term}"&limit=1'
        response = requests.get(url, timeout=30)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        total = response.json().get("meta", {}).get("results", {}).get("total", 0)
        return total or None

    def _population_sensitivity(
        self, drug_name, adverse_event, resolved_field, primary_ror, primary_a, total
    ):
        """Re-run the estimate over the union cohort, and say if it disagrees.

        Never raises into the primary result: a failure here degrades to a stated
        "not computed", because a sensitivity arm that breaks the main answer is
        worse than no sensitivity arm.
        """
        try:
            fields = self._resolve_all_drug_fields(drug_name)
            if len(fields) <= 1:
                return {
                    "computed": False,
                    "reason": (
                        "Only one openFDA field knows this drug, so the narrow and "
                        "union populations are identical. No sensitivity to report."
                    ),
                }
            queries = self.population_queries(fields)
            ua = self._count_for_population(queries["union"], adverse_event)
            u_drug_total = self._count_for_population(queries["union"], None)
            ub = u_drug_total - ua
            uc = self._count_for_population(None, adverse_event) - ua
            ud = total - ua - ub - uc
            if min(ua, ub, uc, ud) <= 0:
                return {
                    "computed": False,
                    "reason": f"Insufficient counts in the union cohort (a={ua}, b={ub}).",
                    "fields_unioned": [f"{f}:\"{t}\"" for f, t in fields],
                }
            union_ror = (ua / ub) / (uc / ud)
            note = self.divergence_note(
                {"ROR": round(primary_ror, 3) if primary_ror else None, "cases": primary_a},
                {"ROR": round(union_ror, 3), "cases": ua},
            )
            return {
                "computed": True,
                "definition": (
                    "union over every openFDA field AND every other name openFDA "
                    "gives this product (its NDC-derived brand/generic/substance "
                    "set). Known limit: only NDC-matched reports carry that name "
                    "set, so an as-reported spelling that never mapped stays out "
                    "of this cohort."
                ),
                "fields_unioned": [f"{f}:\"{t}\"" for f, t in fields],
                "narrow_field": resolved_field,
                "cases": ua,
                "drug_report_total": u_drug_total,
                "ROR": round(union_ror, 3),
                "ci_95": {
                    k: round(v, 3)
                    for k, v in self._calculate_ror_ci(ua, ub, uc, ud).items()
                },
                "agrees_with_primary": note is None,
                "divergence": note,
            }
        except Exception as exc:  # noqa: BLE001 - must not break the primary result
            log_msg = f"sensitivity arm failed: {exc}"
            return {"computed": False, "reason": log_msg}

    def _resolve_all_drug_fields(self, drug_name: str) -> List[Tuple[str, str]]:
        """Every ``(field, term)`` that knows this drug, not just the first.

        The first is the narrow population; all of them together are the union.
        Reporting both is what lets a reader see that the population choice moved
        the estimate (LUTATHERA/MDS: ROR 7.2 vs 12.0). The matched TERM is kept
        because `.exact` fields need a different casing than the rest.
        """
        matches = []
        for term in self.expand_terms(drug_name, self._openfda_block(drug_name)):
            for field in self.DRUG_NAME_FIELDS:
                for probe in self.candidate_terms(field, term):
                    if (field, probe) in matches:
                        continue
                    if self._field_total(field, probe):
                        matches.append((field, probe))
                        break
        return matches

    def _openfda_block(self, drug_name: str):
        """openFDA's NDC-derived name set for the entry matching this drug.

        Returns None when nothing matches or the report carries no block -- both
        are ordinary, not errors, and simply mean no expansion is available.
        """
        try:
            field, _ = self._resolve_drug_field(drug_name)
            if not field:
                return None
            term = self.candidate_terms(field, drug_name)[-1]
            url = f'{FDA_BASE_URL}?search={field}:"{term}"&limit=1'
            api_key = os.getenv("FDA_API_KEY")
            if api_key:
                url += f"&api_key={api_key}"
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            results = response.json().get("results") or []
            wanted = drug_name.upper()
            for drug in (results[0].get("patient", {}) if results else {}).get("drug", []):
                block = drug.get("openfda") or {}
                names = self.synonyms_from_openfda(block)
                if any(wanted in n or n in wanted for n in names):
                    return block
            return None
        except Exception:
            # Expansion is an enhancement; never let it break the analysis.
            return None

    def _count_for_population(self, population_query: str, adverse_event: str = None) -> int:
        """Report count for an explicit population query, 404 meaning a true zero."""
        parts = []
        if population_query:
            parts.append(f"({population_query})")
        if adverse_event:
            parts.append(f'patient.reaction.reactionmeddrapt:"{adverse_event}"')
        url = FDA_BASE_URL + ("?search=" + "+AND+".join(parts) + "&limit=1" if parts else "?limit=1")
        api_key = os.getenv("FDA_API_KEY")
        if api_key:
            url += f"&api_key={api_key}"
        response = requests.get(url, timeout=30)
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            # 404 is openFDA's answer to a search matching nothing -- a real zero.
            # Anything else is us failing to ask, and must not look like absence.
            if exc.response is not None and exc.response.status_code == 404:
                return 0
            raise
        return response.json().get("meta", {}).get("results", {}).get("total", 0)

    def _resolve_drug_field(self, drug_name: str):
        """Find the first field that knows this drug. Returns (field, total).

        Returning the field is the point: the caller reports it, so an agent can
        state which population its statistic describes instead of implying that
        every spelling of the drug was counted.
        """
        for field in self.DRUG_NAME_FIELDS:
            total = self._field_total(field, drug_name)
            if total:
                return field, total
        return None, None

    def _get_faers_count(
        self,
        drug_name: str = None,
        adverse_event: str = None,
        field: str = None,
    ) -> int:
        """Get count of FAERS reports matching criteria.

        ``field`` is an argument, never instance state: ToolUniverse caches ONE
        instance per tool name, so a field stashed on ``self`` is shared with every
        concurrent call. Reading it back mid-calculation counted one drug under
        another drug's field and produced a negative contingency cell (DSR-693).
        """
        try:
            query_parts = []
            if drug_name:
                field = field or "patient.drug.openfda.generic_name"
                query_parts.append(f'{field}:"{drug_name}"')
            if adverse_event:
                query_parts.append(
                    f'patient.reaction.reactionmeddrapt:"{adverse_event}"'
                )

            if not query_parts:
                # Get total count
                url = f"{FDA_BASE_URL}?limit=1"
            else:
                search_query = "+AND+".join(query_parts)
                url = f"{FDA_BASE_URL}?search={search_query}&limit=1"

            response = requests.get(url, timeout=30)
            response.raise_for_status()

            data = response.json()
            return data.get("meta", {}).get("results", {}).get("total", 0)

        except requests.HTTPError as exc:
            # openFDA answers 404 to a search that matches nothing. That IS a
            # zero. Anything else -- timeout, connection reset, 5xx -- is us
            # failing to ask, and must not be reported as an absent drug: a bare
            # `except: return 0` here made a dead network indistinguishable from
            # "Insufficient data".
            if exc.response is not None and exc.response.status_code == 404:
                return 0
            raise

    def _get_faers_total_count(self) -> int:
        """Get total number of reports in FAERS database."""
        return self._get_faers_count(None, None)

    def _calculate_ror_ci(self, a: int, b: int, c: int, d: int) -> Dict[str, float]:
        """Calculate 95% confidence interval for ROR."""
        ror = (a / b) / (c / d)
        se_log_ror = math.sqrt((1 / a) + (1 / b) + (1 / c) + (1 / d))
        log_ror = math.log(ror)

        # 95% CI (z = 1.96)
        lower = math.exp(log_ror - 1.96 * se_log_ror)
        upper = math.exp(log_ror + 1.96 * se_log_ror)

        return {"lower": lower, "upper": upper}

    def _calculate_prr_ci(self, a: int, b: int, c: int, d: int) -> Dict[str, float]:
        """Calculate 95% confidence interval for PRR."""
        prr = (a / (a + b)) / (c / (c + d))
        se_log_prr = math.sqrt((b / (a * (a + b))) + (d / (c * (c + d))))
        log_prr = math.log(prr)

        lower = math.exp(log_prr - 1.96 * se_log_prr)
        upper = math.exp(log_prr + 1.96 * se_log_prr)

        return {"lower": lower, "upper": upper}

    def _calculate_ic(self, a: int, b: int, c: int, d: int) -> float:
        """Calculate Information Component (IC)."""
        n = a + b + c + d
        expected = ((a + b) * (a + c)) / n

        if expected <= 0 or a <= 0:
            return 0.0

        ic = math.log2((a + 0.5) / (expected + 0.5))
        return ic

    def _calculate_ic_ci(self, a: int, b: int, c: int, d: int) -> Dict[str, float]:
        """Calculate 95% confidence interval for IC."""
        n = a + b + c + d
        expected = ((a + b) * (a + c)) / n

        if expected <= 0 or a <= 0:
            return {"lower": 0.0, "upper": 0.0}

        # Approximate variance
        variance = (
            (1 / (a + 0.5))
            - (1 / ((a + b) + 0.5))
            - (1 / ((a + c) + 0.5))
            + (1 / (n + 0.5))
        )
        se = math.sqrt(variance) / math.log(2)

        ic = self._calculate_ic(a, b, c, d)
        lower = ic - 1.96 * se
        upper = ic + 1.96 * se

        return {"lower": lower, "upper": upper}
