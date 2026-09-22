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
                               response.status_code, retryable=response.status_code in RETRY_STATUSES)
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
    def __init__(self, tool_config):
        super().__init__(tool_config)

    def run(self, arguments):
        arguments = copy.deepcopy(arguments)
        query_schema_runtime = copy.deepcopy(self.query_schema)
        for key in query_schema_runtime:
            if (key != "HPO_ID_list") and (key in arguments):
                query_schema_runtime[key] = arguments[key]
        all_diseases = []
        for HPOID in arguments["HPO_ID_list"]:
            each_query_schema_runtime = copy.deepcopy(query_schema_runtime)
            each_query_schema_runtime["object"] = HPOID
            each_query_schema_runtime["limit"] = 500
            each_output = execute_RESTful_query(
                endpoint_url=self.endpoint_url, variables=each_query_schema_runtime
            )
            if isinstance(each_output, dict) and each_output.get("status") == "error":
                # One list missing makes the intersection meaningless, so the call fails whole.
                return each_output
            items = each_output.get("items", []) if isinstance(each_output, dict) else []
            all_diseases.append([disease["subject_label"] for disease in items])

        intersection = set(all_diseases[0])
        for element in all_diseases[1:]:
            intersection &= set(element)
        intersection = list(intersection)
        if query_schema_runtime["limit"] < len(intersection):
            intersection = intersection[: query_schema_runtime["limit"]]
        return intersection
