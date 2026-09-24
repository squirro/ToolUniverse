from graphql import build_schema
from graphql.language import parse
from graphql.validation import validate
from .base_tool import BaseTool
from .http_utils import DEFAULT_RETRY_STATUSES, error_from_exception, upstream_error
from .tool_registry import register_tool
import requests
import copy
import time

# Upper bound on how long DiseaseTargetScoreTool will paginate through
# OpenTargets associatedTargets before returning what it has so far. A
# disease can have >10,000 associated targets; without a bound the loop
# issues hundreds of sequential requests and can run for many minutes.
_DISEASE_TARGET_SCORE_TIME_BUDGET_S = 25.0


def validate_query(query_str, schema_str):
    try:
        # Build the GraphQL schema object from the provided schema string
        schema = build_schema(schema_str)

        # Parse the query string into an AST (Abstract Syntax Tree)
        query_ast = parse(query_str)

        # Validate the query AST against the schema
        validation_errors = validate(schema, query_ast)

        if not validation_errors:
            return True
        else:
            # Collect and return the validation errors
            error_messages = "\n".join(str(error) for error in validation_errors)
            return f"Query validation errors:\n{error_messages}"
    except Exception as e:
        return f"An error occurred during validation: {str(e)}"


def remove_none_and_empty_values(json_obj):
    """Remove all key-value pairs where the value is None or an empty list"""
    if isinstance(json_obj, dict):
        return {
            k: remove_none_and_empty_values(v)
            for k, v in json_obj.items()
            if v is not None and v != []
        }
    elif isinstance(json_obj, list):
        return [
            remove_none_and_empty_values(item)
            for item in json_obj
            if item is not None and item != []
        ]
    else:
        return json_obj


def execute_query(endpoint_url, query, variables=None):
    """The query's result, None when the source holds nothing, an error envelope when
    the source failed. A caller must tell the last two apart before reading the data."""
    try:
        response = requests.post(
            endpoint_url, json={"query": query, "variables": variables}, timeout=30
        )
    except requests.exceptions.RequestException as exc:
        return error_from_exception(exc, f"{endpoint_url} request")
    try:
        if not response.ok:
            return upstream_error(
                f"{endpoint_url} answered HTTP {response.status_code}: "
                f"{(response.text or '')[:120]}",
                response.status_code,
                retryable=response.status_code in DEFAULT_RETRY_STATUSES)
        result = response.json()
        result = remove_none_and_empty_values(result)
        # An error from the query itself: a real failure, not an empty answer.
        if "errors" in result:
            return upstream_error(f"{endpoint_url} answered an error: {result['errors']}",
                                  response.status_code, retryable=False)
        # A data key with empty values is a source that holds nothing, and is returned.
        elif "data" not in result:
            return None
        else:
            return result
    except requests.exceptions.JSONDecodeError:
        return upstream_error(
            f"{endpoint_url} answered HTTP {response.status_code} with a body that is not JSON",
            response.status_code, retryable=True)


def _failed(result) -> bool:
    """Did the source fail, as opposed to holding nothing?"""
    return isinstance(result, dict) and result.get("status") == "error"


def _source_failed(result) -> bool:
    """A source that failed, as against a source that answered with nothing.

    Only the second is a reason to ask again with different arguments; asking an outage
    a second question and reporting its rows under the caller's term is how a transport
    failure becomes a statement about the drug.
    """
    return (isinstance(result, dict)
            and (result.get("error_details") or {}).get("type") == "UpstreamServiceError")


class GraphQLTool(BaseTool):
    def __init__(self, tool_config, endpoint_url):
        super().__init__(tool_config)
        self.endpoint_url = endpoint_url
        self.query_schema = tool_config["query_schema"]
        self.parameters = tool_config["parameter"]["properties"]
        self.default_size = 5

    def run(self, arguments):
        arguments = copy.deepcopy(arguments)
        # A paging parameter the caller left out takes the schema's default.
        if "size" in self.parameters and "size" not in arguments:
            arguments["size"] = self.parameters["size"].get("default", self.default_size)
        if "index" in self.parameters and "index" not in arguments:
            arguments["index"] = self.parameters["index"].get("default", 0)
        result = execute_query(
            endpoint_url=self.endpoint_url, query=self.query_schema, variables=arguments
        )
        if _failed(result):
            return result
        if result is None:
            return {"status": "error", "error": "No data returned from API"}
        return {"status": "success", "data": result.get("data", result)}


_OT_SEARCH_QUERY = """
query otSearch($q: String!, $entity: [String!]!) {
  search(queryString: $q, entityNames: $entity, page: {index: 0, size: 1}) {
    hits { id name }
  }
}
"""


def _ot_resolve_id(endpoint_url: str, query_string: str, entity: str) -> str | None:
    """Resolve a gene symbol or disease name to an OpenTargets ID via search."""
    result = execute_query(
        endpoint_url,
        _OT_SEARCH_QUERY,
        {"q": query_string, "entity": [entity]},
    )
    if result and not _failed(result):
        hits = result.get("data", {}).get("search", {}).get("hits", [])
        if hits:
            return hits[0]["id"]
    return None


def _at(data: dict, path: str):
    for key in path.split("."):
        data = data.get(key) if isinstance(data, dict) else None
    return data


def _page_rows(result: dict, path: str, page: int, page_size: int) -> dict:
    """One page of a list the source answers whole, with the source's own total."""
    holder = _at(result.get("data") or {}, path)
    if not isinstance(holder, dict):
        return result
    rows = holder.get("rows") or []
    total = holder.get("count", len(rows))
    start = (page - 1) * page_size
    holder["rows"] = rows[start:start + page_size]
    returned = len(holder["rows"])
    has_more = start + returned < len(rows)
    first, last = (start + 1, start + returned) if returned else (0, 0)
    note = (f"Rows {first}-{last} of the {total} the source holds."
            if returned else f"Page {page} is past the end: the source holds {total}.")
    if has_more:
        note += f" Ask page {page + 1} for the next."
    result.setdefault("metadata", {}).update({
        "total": total, "page": page, "page_size": page_size, "returned": returned,
        "has_more": has_more, "next_page": page + 1 if has_more else None, "note": note})
    return result


@register_tool("OpenTarget")
class OpentargetTool(GraphQLTool):
    def __init__(self, tool_config):
        self.endpoint_url = "https://api.platform.opentargets.org/api/v4/graphql"
        super().__init__(tool_config, self.endpoint_url)

    def run(self, arguments):
        arguments = copy.deepcopy(arguments)
        paged = self.tool_config.get("page_rows")
        if paged:
            # The source answers the whole list; paging is the tool's, not a query variable.
            try:
                page = int(arguments.pop("page", 1))
                page_size = int(arguments.pop(
                    "page_size", self.parameters["page_size"].get("default", 25)))
            except (TypeError, ValueError):
                return {"status": "error", "error": "page and page_size must be integers"}
            if page < 1 or page_size < 1:
                return {"status": "error", "error": "page and page_size start at 1"}
            result = self._query(arguments)
            if result.get("status") == "success":
                result = _page_rows(result, paged, page, page_size)
            return result
        return self._query(arguments)

    def _query(self, arguments):

        # Normalize common aliases before resolution
        if "ensemblId" not in arguments and "gene_symbol" not in arguments:
            for alias in ("target", "gene", "gene_name"):
                if arguments.get(alias):
                    arguments["gene_symbol"] = arguments.pop(alias)
                    break
        if "efoId" not in arguments and "disease_name" not in arguments:
            for alias in ("disease", "disease_id", "trait"):
                if arguments.get(alias):
                    arguments["disease_name"] = arguments.pop(alias)
                    break

        # Resolve gene_symbol → ensemblId if ensemblId not provided
        if "ensemblId" not in arguments and "gene_symbol" in arguments:
            resolved = _ot_resolve_id(
                self.endpoint_url, arguments.pop("gene_symbol"), "target"
            )
            if resolved:
                arguments["ensemblId"] = resolved
            else:
                return {
                    "status": "error",
                    "error": f"Could not resolve gene symbol to Ensembl ID. "
                    "Try passing ensemblId directly (e.g. ENSG00000141510 for TP53).",
                }

        # Resolve disease_name → efoId (or diseaseIds) if not provided
        needs_disease_ids = "diseaseIds" in self.query_schema
        if (
            "efoId" not in arguments
            and "diseaseIds" not in arguments
            and "disease_name" in arguments
        ):
            resolved = _ot_resolve_id(
                self.endpoint_url, arguments.pop("disease_name"), "disease"
            )
            if resolved:
                if needs_disease_ids:
                    arguments["diseaseIds"] = [resolved]
                else:
                    arguments["efoId"] = resolved
            else:
                return {
                    "status": "error",
                    # The example must be a live id; EFO disease terms are obsolete in favour of MONDO.
                    "error": f"Could not resolve disease name to a disease ID. "
                    "Try passing efoId directly (e.g. MONDO_0005011 for Crohn "
                    "disease); OpenTargets indexes diseases under MONDO ids.",
                }

        result = super().run(arguments)

        # Add note when IntOGen evidence count is 0 (Feature-122B-002)
        if result.get("status") == "success":
            evidences = result.get("data", {}).get("disease", {}).get("evidences", {})
            if isinstance(evidences, dict) and evidences.get("count") == 0:
                result.setdefault("metadata", {})["note"] = (
                    "IntOGen returns 0 evidence rows for this query. "
                    "IntOGen only covers somatic tumor driver mutations — "
                    "it has no data for non-cancer diseases or non-driver genes. "
                    "For non-oncology phenotypes, use OpenTargets_get_evidence_by_datasource instead."
                )

        # A source holding nothing may be a hyphenated name the index spells differently,
        # so it is worth one differently-worded question -- but the answer is about the
        # question that was asked, and the caller is told which one that was.
        if result.get("status") != "success" and not _source_failed(result):
            asked = copy.deepcopy(arguments)
            if "drugName" in arguments and isinstance(arguments["drugName"], str):
                arguments["drugName"] = arguments["drugName"].split("-")[0]
            modified_arguments = copy.deepcopy(arguments)
            for each_arg, arg_value in modified_arguments.items():
                if isinstance(arg_value, str) and "-" in arg_value:
                    modified_arguments[each_arg] = arg_value.replace("-", " ")
            changed = {k: v for k, v in modified_arguments.items() if asked.get(k) != v}
            retried = super().run(modified_arguments)
            if changed and retried.get("status") == "success":
                retried.setdefault("metadata", {})["retried_with"] = changed
                retried["metadata"]["note"] = (
                    "The first query returned nothing, so it was asked again with "
                    f"{changed}. These rows answer that question, not the one as "
                    "written -- check the result names the intended entity before "
                    "quoting it."
                )
            result = retried

        # An unresolved disease id comes back as {"data": {}} after null stripping,
        # which must not pass as a real empty result.
        if result.get("status") == "success" and "disease(" in self.query_schema:
            data = result.get("data") or {}
            if not data.get("disease"):
                requested = arguments.get("efoId") or arguments.get("diseaseIds")
                return {
                    "status": "error",
                    "error": (
                        f"OpenTargets could not resolve the disease id {requested!r}, "
                        "so there is no result to report (this is not an empty result "
                        "set). The platform indexes many diseases under MONDO ids and "
                        "plain EFO ids frequently do not resolve -- EFO_0000384 returns "
                        "nothing while MONDO_0004975 returns data. Pass the MONDO id, "
                        "or pass disease_name instead and it will be resolved by search."
                    ),
                }

        return result


@register_tool("OpentargetToolDrugNameMatch")
class OpentargetToolDrugNameMatch(GraphQLTool):
    def __init__(self, tool_config, drug_generic_tool=None):
        endpoint_url = "https://api.platform.opentargets.org/api/v4/graphql"
        self.drug_generic_tool = drug_generic_tool
        self.possible_drug_name_args = ["drugName"]
        super().__init__(tool_config, endpoint_url)

    def run(self, arguments):
        arguments = copy.deepcopy(arguments)
        substituted = None
        results = execute_query(
            endpoint_url=self.endpoint_url, query=self.query_schema, variables=arguments
        )
        if _failed(results):
            # A failed source is not a drug whose brand name needs swapping.
            return results
        if results is None:
            # Find which drug name argument was provided
            matched_arg = None
            for arg_name in self.possible_drug_name_args:
                if arg_name in arguments:
                    matched_arg = arg_name
                    break
            if matched_arg is None:
                print("No drug name found in the arguments.")
                return {"status": "error", "error": "No drug name found in arguments"}
            drug_name_results = self.drug_generic_tool.run(
                {"drug_name": arguments[matched_arg]}
            )
            if (
                drug_name_results is not None
                and "openfda.generic_name" in drug_name_results
            ):
                arguments[matched_arg] = drug_name_results["openfda.generic_name"]
                print(
                    "Found generic name. Trying with the generic name: ",
                    arguments[matched_arg],
                )
                results = execute_query(
                    endpoint_url=self.endpoint_url,
                    query=self.query_schema,
                    variables=arguments,
                )
                substituted = arguments[matched_arg]
        if _failed(results):
            return results
        if results is None:
            return {"status": "error", "error": "No data returned from API"}
        answer = {"status": "success", "data": results.get("data", results)}
        if substituted is not None:
            answer["metadata"] = {
                "retried_with": {matched_arg: substituted},
                "note": (f"The brand name returned nothing, so openFDA's generic name "
                         f"{substituted!r} was queried instead. These rows are for that "
                         "name."),
            }
        return answer


@register_tool("OpenTargetGenetics")
class OpentargetGeneticsTool(GraphQLTool):
    def __init__(self, tool_config):
        endpoint_url = "https://api.genetics.opentargets.org/graphql"
        super().__init__(tool_config, endpoint_url)

    def run(self, arguments):
        arguments = copy.deepcopy(arguments)
        # Resolve disease_name → diseaseIds if not already provided
        if "diseaseIds" not in arguments:
            disease_name = None
            for alias in ("disease_name", "disease", "trait"):
                if arguments.get(alias):
                    disease_name = arguments.pop(alias)
                    break
            if disease_name:
                resolved = _ot_resolve_id(
                    "https://api.platform.opentargets.org/api/v4/graphql",
                    disease_name,
                    "disease",
                )
                if resolved:
                    arguments["diseaseIds"] = [resolved]
                else:
                    return {
                        "status": "error",
                        "error": (
                            f"Could not resolve '{disease_name}' to a disease ID. "
                            "Try passing diseaseIds directly (e.g. ['MONDO_0005148'] for type 2 diabetes)."
                        ),
                    }
        return super().run(arguments)


@register_tool("DiseaseTargetScoreTool")
class DiseaseTargetScoreTool(GraphQLTool):
    """Tool to extract disease-target association scores from specific data sources"""

    def __init__(self, tool_config, datasource_id=None):
        endpoint_url = "https://api.platform.opentargets.org/api/v4/graphql"
        # Get datasource_id from config if not provided as parameter
        self.datasource_id = datasource_id or tool_config.get("datasource_id")
        super().__init__(tool_config, endpoint_url)

    def run(self, arguments):
        """
        Extract disease-target scores for a specific datasource
        Arguments should contain: efoId, datasourceId (optional), pageSize (optional)
        """
        arguments = copy.deepcopy(arguments)
        efo_id = arguments.get("efoId")
        datasource_id = arguments.get("datasourceId", self.datasource_id)
        page_size = arguments.get("pageSize", 100)

        if not efo_id:
            return {"status": "error", "error": "efoId is required"}
        if not datasource_id:
            return {"status": "error", "error": "datasourceId is required"}

        results = []
        page_index = 0
        total_fetched = 0
        total_count = None
        disease_info = None
        truncated = False

        deadline = time.monotonic() + _DISEASE_TARGET_SCORE_TIME_BUDGET_S

        while True:
            # Bound total wall-clock time. A disease can have >10,000
            # associated targets; without this the loop can run for minutes.
            if time.monotonic() >= deadline:
                truncated = True
                break

            variables = {"efoId": efo_id, "index": page_index, "size": page_size}

            response_data = execute_query(
                self.endpoint_url, self.query_schema, variables
            )
            if _failed(response_data):
                # A page that failed is not the end of the results.
                return response_data
            if not response_data or "data" not in response_data:
                break

            # execute_query() runs remove_none_and_empty_values(), which strips
            # a null `disease` field — so a not-found disease arrives as
            # data={} (see its Feature-94A-002 note). Use .get() instead of
            # ["disease"]; the unguarded access raised KeyError -> surfaced as
            # "Unexpected error: 'disease'" whenever an invalid efoId (commonly
            # a disease *name* passed instead of an EFO/MONDO id) was given.
            disease_data = response_data["data"].get("disease")
            if not disease_data:
                # First page with no disease => the efoId was not found. Return
                # an actionable error rather than a silent empty "success" so the
                # caller knows to resolve the name to an id first. A later page
                # with no disease just means we've reached the end of results.
                if page_index == 0 and disease_info is None:
                    return {
                        "status": "error",
                        "error": (
                            f"No OpenTargets disease found for efoId '{efo_id}'. "
                            "Pass a valid EFO/MONDO id — resolve a disease name "
                            "first, e.g. via "
                            "OpenTargets_get_disease_id_description_by_name."
                        ),
                    }
                break

            if disease_info is None:
                disease_info = {
                    "disease_id": disease_data.get("id"),
                    "disease_name": disease_data.get("name"),
                }

            # Same reason the `disease` key above is read with .get(): the cleaner
            # deletes any key whose value is an empty list, so a page with no rows and
            # a target with no datasource scores both arrive with the key simply gone.
            associated = disease_data.get("associatedTargets") or {}
            rows = associated.get("rows") or []
            if total_count is None:
                total_count = associated.get("count") or 0

            for row in rows:
                target = row.get("target") or {}
                if not target.get("id") and not target.get("approvedSymbol"):
                    continue  # a score no target can be attributed to is not a result
                score_entry = next(
                    (ds for ds in (row.get("datasourceScores") or [])
                     if ds.get("id") == datasource_id),
                    None,
                )
                if score_entry:
                    results.append(
                        {
                            "target_symbol": target.get("approvedSymbol"),
                            "target_id": target.get("id"),
                            "datasource": datasource_id,
                            "score": score_entry.get("score"),
                        }
                    )

            total_fetched += len(rows)
            if total_fetched >= total_count or len(rows) == 0:
                break
            page_index += 1

        data = {
            "disease_info": disease_info,
            "datasource": datasource_id,
            "total_targets_with_scores": len(results),
            "target_scores": results,
        }
        if truncated:
            data["truncated"] = True
            data["note"] = (
                f"Stopped after {_DISEASE_TARGET_SCORE_TIME_BUDGET_S:.0f}s; "
                f"scanned {total_fetched} of {total_count} associated targets. "
                "Increase pageSize to scan more targets per request, or query a "
                "more specific disease."
            )
        return {"status": "success", "data": data}
