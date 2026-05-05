"""SR Analysis Tools -- Swiss Rockets custom biomedical analysis tools.

Dispatches run() calls to standalone exec_* functions that do the actual work.
Each exec_* function follows the signature:
    exec_*(arguments, input_table, output_table, db_path) -> None

The tool class bridges TU's BaseTool.run(arguments) interface to this signature
by extracting _input_table, _output_table, _db_path from the arguments dict.
These are injected by the AIRA research pipeline before calling run_one_function().
"""
from __future__ import annotations

import logging
from typing import Dict, Any

from .base_tool import BaseTool
from .tool_registry import register_tool

log = logging.getLogger(__name__)

# Import exec functions from their individual modules
from .tools_sr.internalization import exec_internalization
from .tools_sr.differential import exec_differential_expression
from .tools_sr.shedding import exec_shedding_risk
from .tools_sr.organs_at_risk import exec_organs_at_risk
from .tools_sr.competition import exec_competition_landscape
from .tools_sr.patents import exec_patent_landscape
from .tools_sr.validation import exec_validation_level
from .tools_sr.clinical_trials import exec_ct_search
from .tools_sr.successful_trials import exec_successful_trials
from .tools_sr.trial_population import exec_trial_population
from .tools_sr.trial_outcomes import exec_trial_outcomes
from .tools_sr.analyze_table import exec_analyze_table

# export_table depends on Squirro SDK -- optional
try:
    from .tools_sr.export_table import exec_export_table
except ImportError:
    exec_export_table = None
    log.info("export_table unavailable (Squirro SDK not installed)")

# Dispatch map: tool_name -> exec function
_DISPATCH: Dict[str, Any] = {
    "internalization_score": exec_internalization,
    "differential_expression": exec_differential_expression,
    "shedding_risk": exec_shedding_risk,
    "organs_at_risk": exec_organs_at_risk,
    "competition_landscape": exec_competition_landscape,
    "patent_landscape": exec_patent_landscape,
    "validation_level": exec_validation_level,
    "ClinicalTrials_search_by_intervention_and_condition": exec_ct_search,
    "successful_trials_classifier": exec_successful_trials,
    "trial_population_summary": exec_trial_population,
    "trial_outcomes_extractor": exec_trial_outcomes,
    "analyze_table_with_python": exec_analyze_table,
}
if exec_export_table is not None:
    _DISPATCH["export_table"] = exec_export_table


@register_tool("SRAnalysisTool")
class SRAnalysisTool(BaseTool):
    """Swiss Rockets custom analysis tools for biomedical target identification."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        tool_name = self.tool_config.get("name", "")
        exec_fn = _DISPATCH.get(tool_name)

        if exec_fn is None:
            return {
                "error": f"SR analysis tool '{tool_name}' not supported",
                "available_tools": list(_DISPATCH.keys()),
            }

        # Extract pipeline context from arguments (injected by research_pipeline)
        input_table = arguments.pop("_input_table", "")
        output_table = arguments.pop("_output_table", f"result_{tool_name}")
        db_path = arguments.pop("_db_path", "")

        try:
            # exec functions return a list of dicts (results).
            # The pipeline's _exec_tu() handles writing them to SQLite,
            # just like any other TU tool.
            results = exec_fn(arguments, input_table, output_table, db_path)
            if results is None:
                results = []
            return results
        except Exception as e:
            log.error("SRAnalysisTool.run(%s): %s", tool_name, e, exc_info=True)
            return {
                "error": str(e),
                "tool_name": tool_name,
            }
