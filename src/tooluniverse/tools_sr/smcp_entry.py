"""Server entry that installs central interception, then runs SMCP unchanged (DSR-666).

The image used to run ``tooluniverse-smcp`` directly, which resolves to
``smcp_server:run_smcp_server`` -- an upstream file that re-syncs from
``mims-harvard:main``. Adding the install call there would put a permanent edit on a
re-syncing file for the sake of two lines, so the image points here instead: install
first, then hand over to the upstream server untouched.

Everything about the server's behaviour is unchanged. ``run_smcp_server`` parses
``sys.argv`` itself, so every flag the image passes still reaches it.

Run as ``python -m tooluniverse.tools_sr.smcp_entry <same flags as before>``.
"""

from __future__ import annotations


def _run_upstream_server() -> None:
    """Indirection so the ordering test can observe the handover without a live server."""
    from tooluniverse.smcp_server import run_smcp_server

    run_smcp_server()


def install_interception() -> None:
    """Switch on the central repairs for every tool invocation.

    Idempotent. Must happen before the server starts accepting calls: transport status
    would otherwise miss results already served, and the ID-namespace cue is applied when
    the registry loads, which happens on the first call if not before.
    """
    from tooluniverse import ToolUniverse

    from . import id_cue, source_url, transport_status

    transport_status.install(ToolUniverse)  # DSR-666: an empty result says which empty
    source_url.install(ToolUniverse)  # DSR-667: cite the call, minus its credentials
    id_cue.install(ToolUniverse)  # DSR-662: the description names the ID namespace


def main() -> None:
    install_interception()
    _run_upstream_server()


if __name__ == "__main__":
    main()
