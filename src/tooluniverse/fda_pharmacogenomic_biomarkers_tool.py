from typing import Dict, Any, List, Optional
import requests
import re
from .base_tool import BaseTool
from .http_utils import upstream_error
from .tool_registry import register_tool

# fda.gov's Akamai edge refuses some networks outright. From sr-dev (2026-09-24) the
# host gets 403 "Access Denied" and the container is redirected to an apology page
# that answers 404; the same URL answers 200 from other networks. No machine-readable
# copy of this table is reachable from sr-dev: the FDA's PDF version sits behind the
# same edge, and openFDA labels carry a pharmacogenomics section only for some drugs
# (abacavir's HLA-B warning is not in it). So when fda.gov refuses, the tool answers
# from ClinPGx label annotations marked "On FDA Biomarker List" -- ClinPGx's reading
# of each FDA label, labelled as such, never as FDA's table.
_BLOCKED = "fda.gov refuses automated requests from this network"

CLINPGX_URL = "https://api.clinpgx.org/v1/data/labelAnnotation"
CLINPGX_PAGE = "https://www.clinpgx.org/labelAnnotation/{id}"
_ON_FDA_LIST = "On FDA Biomarker List"


class _Unread(Exception):
    """A source that gave no answer; the message says why."""

    def __init__(self, message: str, status: Optional[int]):
        super().__init__(message)
        self.status = status


@register_tool("FDAPharmacogenomicBiomarkersTool")
class FDAPharmacogenomicBiomarkersTool(BaseTool):
    """
    Tool to retrieve data from the FDA's Table of Pharmacogenomic Biomarkers in Drug Labeling.
    Fetches the table from the FDA website and provides filtering capabilities.
    """

    FDA_URL = "https://www.fda.gov/drugs/science-and-research-drugs/table-pharmacogenomic-biomarkers-drug-labeling"

    # Standard headers to avoid 403/404 errors from FDA servers
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the tool to retrieve and filter pharmacogenomic biomarkers.

        Args:
            arguments (Dict[str, Any]):
                - drug_name (str, optional): Filter by drug name (case-insensitive partial match).
                - biomarker (str, optional): Filter by biomarker (case-insensitive partial match).
                - limit (int, optional): Maximum number of results to return (default: 10).

        Returns:
            Dict[str, Any]: A dictionary containing the 'count' and 'results' list.
        """
        drug_name_filter = arguments.get("drug_name")
        biomarker_filter = arguments.get("biomarker")
        limit = arguments.get("limit", 10)

        try:
            records = self._read_fda_table()
        except _Unread as refused:
            return self._from_clinpgx(str(refused), refused.status,
                                      drug_name_filter, biomarker_filter, limit)
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to retrieve or parse FDA data: {str(e)}",
            }

        filtered_results = [
            record for record in records
            if (not drug_name_filter
                or drug_name_filter.lower() in record.get("Drug", "").lower())
            and (not biomarker_filter
                 or biomarker_filter.lower() in record.get("Biomarker", "").lower())
        ]
        limited_results = filtered_results[:limit]
        return {
            "status": "success",
            "source": "FDA",
            "source_url": self.FDA_URL,
            "count": len(filtered_results),
            "shown": len(limited_results),
            "results": limited_results,
        }

    def _read_fda_table(self) -> List[Dict[str, str]]:
        """The FDA table's rows, or _Unread when fda.gov did not serve it."""
        try:
            response = requests.get(self.FDA_URL, headers=self.HEADERS, timeout=30)
        except requests.RequestException as e:
            raise _Unread(f"fda.gov request failed: {type(e).__name__}: {e}", None) from e
        if response.status_code == 403 or "apology" in (response.url or ""):
            raise _Unread(f"{_BLOCKED} (HTTP {response.status_code} at {response.url})",
                          response.status_code)
        if response.status_code >= 400:
            raise _Unread(f"fda.gov answered HTTP {response.status_code} at {response.url}",
                          response.status_code)
        records = self._parse_html_table(response.text)
        # The full table always has rows; none means we were not served it.
        if not records:
            raise _Unread(f"FDA page answered {response.status_code} without the biomarker "
                          "table; likely a bot-check page", response.status_code)
        return records

    def _from_clinpgx(self, fda_reason: str, fda_status: Optional[int],
                      drug_name: Optional[str], biomarker: Optional[str],
                      limit: int) -> Dict[str, Any]:
        """ClinPGx's annotations of FDA labels on FDA's biomarker list, labelled as ClinPGx."""
        unread = f"FDA table not read: {fda_reason}"
        try:
            annotations = self._clinpgx_annotations(drug_name)
        except _Unread as failed:
            return upstream_error(f"{unread}; ClinPGx fallback failed too: {failed}",
                                  failed.status or fda_status, retryable=False)
        rows = [self._clinpgx_row(a) for a in annotations]
        if biomarker:
            rows = [r for r in rows if biomarker.lower() in r["Biomarker"].lower()
                    or biomarker.lower() in r["Alleles"].lower()]
        if not rows:
            # ClinPGx listing nothing says nothing about FDA's table, which stays unread.
            asked = ", ".join(f"{k} {v!r}" for k, v in
                              (("drug", drug_name), ("biomarker", biomarker)) if v)
            return upstream_error(
                f"{unread}; ClinPGx lists no FDA-biomarker label annotation for {asked or 'the query'}, "
                "which is not an FDA answer: whether FDA's table lists it is unknown",
                fda_status, retryable=False)
        shown = rows[:limit]
        return {
            "status": "success",
            "source": "ClinPGx",
            "fallback_from": "fda.gov",
            "fda_table": unread,
            "note": ("ClinPGx (formerly PharmGKB) annotations of FDA drug labels that ClinPGx "
                     f"marks \"{_ON_FDA_LIST}\" -- not the FDA table, which could not be read. "
                     "Cite each row by its ClinPGx link."),
            "count": len(rows),
            "shown": len(shown),
            "results": shown,
        }

    def _clinpgx_annotations(self, drug_name: Optional[str]) -> List[Dict[str, Any]]:
        params = {"source": "FDA", "biomarkerStatus": _ON_FDA_LIST, "view": "base"}
        # ClinPGx matches names exactly and holds most in lower case.
        names = list(dict.fromkeys([drug_name.lower(), drug_name])) if drug_name else [None]
        for name in names:
            query = {**params, "relatedChemicals.name": name} if name else params
            try:
                response = requests.get(CLINPGX_URL, params=query, timeout=30)
                body = response.json()
            except (requests.RequestException, ValueError) as e:
                raise _Unread(f"ClinPGx request failed: {type(e).__name__}: {e}", None) from e
            data = body.get("data") if isinstance(body, dict) else None
            if response.status_code == 200 and isinstance(data, list):
                return [a for a in data if a.get("biomarkerStatus") == _ON_FDA_LIST]
            # 404 with "No results matching criteria." is ClinPGx's empty answer.
            if not (response.status_code == 404 and "No results" in response.text):
                raise _Unread(f"ClinPGx answered HTTP {response.status_code} at {CLINPGX_URL}",
                              response.status_code)
        return []

    @staticmethod
    def _clinpgx_row(annotation: Dict[str, Any]) -> Dict[str, Any]:
        genes = annotation.get("prescribingGenes") or annotation.get("relatedGenes") or []
        return {
            "Drug": ", ".join(c.get("name", "") for c in annotation.get("relatedChemicals") or []),
            "Biomarker": ", ".join(g.get("symbol", "") for g in genes),
            "Alleles": ", ".join(a.get("symbol", "") for a in annotation.get("relatedAlleles") or []),
            # ClinPGx's PGx level for the label; it gives no labeling-section column.
            "PGxLevel": (annotation.get("testing") or {}).get("term") or "not given by ClinPGx",
            "DosingInformation": bool(annotation.get("dosingInformation")),
            "Annotation": annotation.get("name", ""),
            "source": "ClinPGx",
            "url": CLINPGX_PAGE.format(id=annotation.get("id", "")),
        }

    def _parse_html_table(self, html_content: str) -> List[Dict[str, str]]:
        """
        Parses the HTML content to extract the biomarkers table.
        Uses regex/simple parsing to avoid heavy dependencies like BeautifulSoup if possible,
        or assumes BeautifulSoup is available in the environment (it usually is in this project).
        """
        records = []
        try:
            # Try importing BeautifulSoup, fallback to regex if not available (though highly recommended)
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html_content, "html.parser")

            # Find the table - usually the first table in the main content or identified by headers
            # The FDA page structure has a table with specific headers
            tables = soup.find_all("table")
            target_table = None

            for table in tables:
                headers = [th.get_text(strip=True) for th in table.find_all("th")]
                # Partial match check for crucial columns
                if any("Drug" in h for h in headers) and any(
                    "Biomarker" in h for h in headers
                ):
                    target_table = table
                    break

            if target_table:
                # Get the header mapping
                headers = [
                    th.get_text(strip=True) for th in target_table.find_all("th")
                ]
                # Map headers to cleaner keys
                header_map = {
                    "Drug": "Drug",
                    "Therapeutic Area": "TherapeuticArea",
                    "Biomarker": "Biomarker",
                    "Labeling Section": "LabelingSection",
                }

                rows = target_table.find_all("tr")[1:]  # Skip header row
                for row in rows:
                    cells = row.find_all(["td", "th"])
                    if not cells:
                        continue

                    record = {}
                    for i, cell in enumerate(cells):
                        if i < len(headers):
                            original_header = headers[i]
                            # Clean header for mapping (remove special chars)
                            clean_header = (
                                original_header.replace("\xa0", " ")
                                .replace("*", "")
                                .replace("†", "")
                                .strip()
                            )

                            # Clean cell text
                            cell_text = cell.get_text(strip=True)

                            # Find matching key based on partial match
                            key = None
                            for k in header_map:
                                # Check if configured key is part of the cleaned actual header (e.g. "Labeling Section" in "Labeling Sections")
                                if k in clean_header:
                                    key = header_map[k]
                                    break

                            if key:
                                record[key] = cell_text
                            elif (
                                clean_header
                            ):  # Store unmapped columns if header is not empty
                                record[clean_header] = cell_text

                    if record.get("Drug"):  # Only add valid records
                        records.append(record)

            return records

        except ImportError:
            # Fallback regex parsing if BS4 is missing (less robust)
            # Find table rows
            row_pattern = re.compile(r"<tr[^>]*>(.*?)</tr>", re.DOTALL)
            cell_pattern = re.compile(r"<td[^>]*>(.*?)</td>", re.DOTALL)

            matches = row_pattern.findall(html_content)
            for match in matches:
                cells = cell_pattern.findall(match)
                if len(cells) >= 3:  # Assuming at least Drug, Area, Biomarker
                    # Cleanup tags
                    clean_cells = [re.sub(r"<[^>]+>", "", c).strip() for c in cells]
                    # This is very brittle, BS4 is preferred.
                    # Assuming standard FDA columns order: Drug, Therapeutic Area, Biomarker, Labeling Section
                    if len(clean_cells) >= 4:
                        records.append(
                            {
                                "Drug": clean_cells[0],
                                "TherapeuticArea": clean_cells[1],
                                "Biomarker": clean_cells[2],
                                "LabelingSection": clean_cells[3],
                            }
                        )
            return records
