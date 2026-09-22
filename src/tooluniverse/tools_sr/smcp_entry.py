"""Server entry that installs central interception, then runs SMCP unchanged.

``smcp_server`` re-syncs from upstream, so the install call lives here instead of there:
install first, then hand over to the upstream server untouched. Behaviour is unchanged,
because ``run_smcp_server`` parses ``sys.argv`` itself and every flag still reaches it.

Run as ``python -m tooluniverse.tools_sr.smcp_entry <same flags as before>``.
"""

from __future__ import annotations


def _run_upstream_server() -> None:
    """Indirection so the ordering test can observe the handover without a live server."""
    from tooluniverse.smcp_server import run_smcp_server

    run_smcp_server()


def install_interception() -> None:
    """Switch on the central repairs for every tool invocation.

    Idempotent. Must happen before the server accepts calls: the ID-namespace cue is
    applied when the registry loads, which happens on the first call if not before.
    """
    from tooluniverse import ToolUniverse

    from . import id_cue, source_url, transport_status

    transport_status.install(ToolUniverse)  # an empty result says which kind of empty
    source_url.install(ToolUniverse)  # cite the call, minus its credentials
    id_cue.install(ToolUniverse)  # the description names the ID namespace


def main() -> None:
    install_interception()
    _run_upstream_server()


if __name__ == "__main__":
    main()
