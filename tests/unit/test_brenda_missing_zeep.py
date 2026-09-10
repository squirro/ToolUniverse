"""BRENDA must say `zeep` is missing, not raise UnboundLocalError over it.

`_get_client()` already returns an excellent, actionable message when the
optional `zeep` dependency is absent:

    "zeep is required for BRENDA SOAP access. Install with: pip install zeep"

That message was unreachable. Each SOAP handler did `from zeep.exceptions import
Fault` *inside* its own `try`, then caught `except Fault`. When the import is the
thing that fails, Python still has to evaluate the except clause -- and the name
is unbound, so it raises

    UnboundLocalError: cannot access local variable 'Fault'
                       where it is not associated with a value

which replaces a fixable instruction with a traceback about an internal
variable. Observed live over SMCP on all four SOAP tools.

An exception class used in an `except` clause has to be bound before the `try`
it guards, always.
"""

import json

import pytest

from tooluniverse.brenda_tool import BRENDATool

pytest.importorskip  # noqa: B018  - keep the import list explicit

SOAP_OPERATIONS = ["get_km", "get_kcat", "get_inhibitors", "get_enzyme_info"]


def _tool():
    return BRENDATool({"name": "BRENDA_get_km", "type": "BRENDATool"})


@pytest.mark.unit
@pytest.mark.parametrize("operation", SOAP_OPERATIONS)
def test_absent_zeep_is_reported_as_a_missing_dependency(monkeypatch, operation):
    """With credentials present but zeep absent, the user must learn about zeep."""
    zeep_installed = True
    try:
        import zeep  # noqa: F401
    except ImportError:
        zeep_installed = False
    if zeep_installed:
        pytest.skip("zeep is installed; this guards the absent-dependency path")

    monkeypatch.setenv("BRENDA_EMAIL", "someone@example.org")
    monkeypatch.setenv("BRENDA_PASSWORD", "not-a-real-password")

    result = _tool().run({"operation": operation, "ec_number": "1.1.1.1"})
    text = json.dumps(result)

    assert "UnboundLocalError" not in text, (
        f"{operation} leaked an internal variable error: {text[:200]}"
    )
    assert "Fault" not in text, (
        f"{operation} surfaced the exception class name rather than the cause: "
        f"{text[:200]}"
    )
    assert "zeep" in text.lower(), (
        f"{operation} did not tell the caller the zeep dependency is missing: "
        f"{text[:200]}"
    )


@pytest.mark.unit
def test_missing_credentials_still_short_circuit(monkeypatch):
    """The auth path must keep working; it runs before any zeep import."""
    monkeypatch.delenv("BRENDA_EMAIL", raising=False)
    monkeypatch.delenv("BRENDA_PASSWORD", raising=False)

    result = _tool().run({"operation": "get_km", "ec_number": "1.1.1.1"})

    assert result["status"] == "error"
    assert "BRENDA_EMAIL" in result["error"]
