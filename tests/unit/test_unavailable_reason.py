"""A missing Python package must not be reported as a missing API key.

Seven CELLxGENE tools are gated on a fake credential named
`CELLXGENE_CENSUS_PACKAGE_INSTALLED`, so calling one returns:

    Tool 'CELLxGENE_get_expression_data' requires API key(s) not set:
    CELLXGENE_CENSUS_PACKAGE_INSTALLED. Set them as environment variables
    and retry.

Nothing about that is true. There is no such credential to obtain, and an agent
that follows the instruction will export the variable, satisfy the gate, and hit
a worse failure further in. The real fix is `pip install cellxgene-census`, and
every one of the seven already declares it correctly:

    "required_packages": ["cellxgene_census", "tiledbsoma"]

So the information needed for an accurate message is present and unused. This is
the same defect shape as the BRENDA `Fault` bug -- the tool knows exactly what is
wrong and structurally cannot say it.
"""

import pytest

from tooluniverse.execute_function import ToolUniverse


@pytest.mark.unit
def test_missing_package_is_reported_as_a_package_not_a_key():
    tu = ToolUniverse()
    tu._excluded_api_key_tools = {
        "CELLxGENE_get_expression_data": ["CELLXGENE_CENSUS_PACKAGE_INSTALLED"]
    }
    tu._excluded_tool_packages = {
        "CELLxGENE_get_expression_data": ["cellxgene_census", "tiledbsoma"]
    }

    msg = tu._tool_unavailable_message("CELLxGENE_get_expression_data")

    assert "cellxgene_census" in msg, "the message must name the package"
    assert "pip install" in msg, "the message must give the actual remedy"
    assert "environment variable" not in msg.lower(), (
        "there is no credential to set; saying so sends the agent to do the "
        "wrong thing"
    )


@pytest.mark.unit
def test_a_genuinely_missing_key_still_says_so():
    """The package path must not swallow real credential failures."""
    tu = ToolUniverse()
    tu._excluded_api_key_tools = {"BioCyc_get_pathway": ["BIOCYC_EMAIL",
                                                         "BIOCYC_PASSWORD"]}
    tu._excluded_tool_packages = {}

    msg = tu._tool_unavailable_message("BioCyc_get_pathway")

    assert "BIOCYC_EMAIL" in msg and "BIOCYC_PASSWORD" in msg
    assert "environment variable" in msg.lower()


@pytest.mark.unit
def test_an_unknown_tool_reports_not_found():
    tu = ToolUniverse()
    tu._excluded_api_key_tools = {}
    tu._excluded_tool_packages = {}

    msg = tu._tool_unavailable_message("No_such_tool")

    assert "not found" in msg.lower()
