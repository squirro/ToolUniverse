from .graphql_tool import GraphQLTool, remove_none_and_empty_values
import requests
import copy
from .http_utils import request_with_retry, upstream_error as _upstream_error
from .tool_registry import register_tool

_SESSION = requests.Session()
RETRY_STATUSES = (408, 429, 500, 502, 503, 504)
BACKOFF_SECONDS = 0.5


def execute_RESTful_query(endpoint_url, variables=None):
    try:
        response = request_with_retry(_SESSION, "GET", endpoint_url, params=variables, timeout=30,
                                      retry_statuses=RETRY_STATUSES, max_attempts=3,
                                      backoff_seconds=BACKOFF_SECONDS)
    except requests.exceptions.RequestException as exc:
        return _upstream_error(f"request failed: {type(exc).__name__}: {exc}", None, retryable=True)
    if response.status_code >= 400:
        reason = (response.text or "")[:120].replace("\n", " ")
        return _upstream_error(f"{endpoint_url} answered HTTP {response.status_code}: {reason}",
                               response.status_code,
                               retryable=response.status_code in RETRY_STATUSES,
                               # A 404 is the source answering that nothing matches. Stamped
                               # as a service error it read as the source having failed,
                               # because the type string is what the run matches on.
                               error_type=("UpstreamNotFound" if response.status_code == 404
                                           else "UpstreamServiceError"))
    try:
        result = response.json()
    except ValueError:
        return _upstream_error(f"{endpoint_url} answered HTTP {response.status_code} with a body that is "
                               "not JSON", response.status_code, retryable=True)
    if isinstance(result, dict) and "error" in result:
        return _upstream_error(f"{endpoint_url} answered an error: {result['error']}",
                               response.status_code, retryable=False)
    return result


@register_tool("RESTfulTool")
class RESTfulTool(GraphQLTool):
    def __init__(self, tool_config, endpoint_url):
        super().__init__(tool_config, endpoint_url)

    def run(self, arguments):
        arguments = copy.deepcopy(arguments)
        return execute_RESTful_query(
            endpoint_url=self.endpoint_url, variables=arguments
        )


@register_tool("Monarch")
class MonarchTool(RESTfulTool):
    def __init__(self, tool_config):
        endpoint_url = (
            "https://api.monarchinitiative.org/v3/api" + tool_config["tool_url"]
        )
        super().__init__(tool_config, endpoint_url)

    def run(self, arguments):
        arguments = copy.deepcopy(arguments)
        query_schema_runtime = copy.deepcopy(self.query_schema)
        for key in query_schema_runtime:
            if key in arguments:
                query_schema_runtime[key] = arguments[key]
        if "url_key" in query_schema_runtime:
            url_key_name = query_schema_runtime["url_key"]
            formatted_endpoint_url = self.endpoint_url.format(
                url_key=query_schema_runtime[url_key_name]
            )
            del query_schema_runtime["url_key"]
        else:
            formatted_endpoint_url = self.endpoint_url
        if isinstance(query_schema_runtime, dict):
            if "query" in query_schema_runtime:
                query_schema_runtime["q"] = query_schema_runtime[
                    "query"
                ]  # match with the api
        response = execute_RESTful_query(
            endpoint_url=formatted_endpoint_url, variables=query_schema_runtime
        )
        if isinstance(response, dict) and response.get("status") == "error":
            return response
        if "facet_fields" in response:
            del response["facet_fields"]

        response = remove_none_and_empty_values(response)
        if isinstance(response, dict) and "status" not in response:
            return {"status": "success", "data": response}
        return response


@register_tool("MonarchDiseasesForMultiplePheno")
class MonarchDiseasesForMultiplePhenoTool(MonarchTool):
    """The diseases every one of several phenotypes is annotated with."""

    # Monarch's own page for one phenotype. A common phenotype is annotated on thousands
    # of diseases, so a page is not the set and the response's `total` says which it is.
    PHENOTYPE_PAGE = 500

    def __init__(self, tool_config):
        super().__init__(tool_config)

    def run(self, arguments):
        arguments = copy.deepcopy(arguments)
        phenotypes = list(arguments.get("HPO_ID_list") or [])
        if not phenotypes:
            return {"status": "error",
                    "error": "HPO_ID_list is empty, so there is no intersection to take. "
                             "Pass at least one HPO id."}

        query_schema_runtime = copy.deepcopy(self.query_schema)
        for key in query_schema_runtime:
            if (key != "HPO_ID_list") and (key in arguments):
                query_schema_runtime[key] = arguments[key]
        limit = int(query_schema_runtime.get("limit") or 0)
        # Never ask for less than the caller wants: the intersection cannot hold more
        # than the smallest per-phenotype page it was built from.
        page = max(limit, self.PHENOTYPE_PAGE)

        per_phenotype: dict = {}
        truncated = []
        for hpo_id in phenotypes:
            each = copy.deepcopy(query_schema_runtime)
            each["object"] = hpo_id
            each["limit"] = page
            answer = execute_RESTful_query(endpoint_url=self.endpoint_url, variables=each)
            if isinstance(answer, dict) and answer.get("status") == "error":
                # One list missing makes the intersection meaningless, so the call fails whole.
                return answer
            if not isinstance(answer, dict) or "items" not in answer:
                return {"status": "error",
                        "error": (f"Monarch answered for {hpo_id} without an `items` list, so "
                                  "that phenotype contributed nothing. An empty contribution "
                                  "would empty the whole intersection, which would read as a "
                                  "real negative.")}
            items = answer["items"] or []
            total = answer.get("total")
            if isinstance(total, int) and total > len(items):
                truncated.append({"phenotype": hpo_id, "read": len(items),
                                  "source_total": total})
            per_phenotype[hpo_id] = [d.get("subject_label") for d in items
                                     if isinstance(d, dict) and d.get("subject_label")]

        shared = set(per_phenotype[phenotypes[0]])
        for hpo_id in phenotypes[1:]:
            shared &= set(per_phenotype[hpo_id])
        # Ordered by the first phenotype's own order. Cutting an unordered set to a limit
        # drops arbitrary candidates, and the one dropped can be the diagnosis.
        ordered = [name for name in dict.fromkeys(per_phenotype[phenotypes[0]])
                   if name in shared]
        kept = ordered[:limit] if limit and limit < len(ordered) else ordered

        data = {"diseases": kept, "total": len(ordered), "phenotypes": phenotypes,
                "per_phenotype_counts": {k: len(v) for k, v in per_phenotype.items()}}
        if len(kept) < len(ordered):
            data["note"] = (f"{len(ordered)} diseases carry every phenotype; the {len(kept)} "
                            "shown are the caller's limit, in the first phenotype's order.")
        if truncated:
            data["truncated_phenotypes"] = truncated
            data["truncation_warning"] = (
                "Monarch cut at least one phenotype's disease list, so the intersection is a "
                "lower bound: a disease past the cut left it without being counted. The "
                "phenotypes and their totals are under `truncated_phenotypes`.")
        return {"status": "success", "data": data}
