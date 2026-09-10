"""A definition on disk is not a tool the server can serve (DSR-663).

The loader reads a configured set of category files plus a scan of ``data/remote_tools``.
Anything else under ``data/`` is inert, and inert in a way nothing else catches: the name
is in the registry files so a name check passes, and it is absent from the image's
``--exclude-tools`` so the exclusion check passes too. The agent still gets "Tool 'X' not
found even after loading tools", which reads as a registry bug rather than a mistake in the
body and burns an iteration against a default cap of 10.

Re-measured 2026-08-12, and the ticket's headline of 19 does not reproduce. 47 definitions
are unreachable: 39 are the API-key catalogue, whose records carry a ``name`` and a
``type`` of ``endpoint``/``secret`` and are not tools at all, and 8 are the ``broken_apis``
archive, unwired on purpose with an "Archived at:" comment left at each removed entry in
``default_config.py``. Both are declared, so the guard is green today -- and green on
arrival is only trustworthy because ``test_an_unwired_data_file_fails_the_guard`` shows it
is not green by construction.
"""

import json

from tooluniverse.tools_sr import wiring


def _definition(name, tool_type="RESTTool"):
    return {"name": name, "type": tool_type, "description": "x"}


# --- the guard itself ---


def test_no_tool_definition_is_stranded_off_the_loader():
    """The ratchet. Adding a data file without wiring it turns this red."""
    assert wiring.unwired_definitions() == {}


def test_an_unwired_data_file_fails_the_guard(tmp_path):
    """Proof the guard is capable of failing -- otherwise its green tells you nothing."""
    (tmp_path / "orphan_tools.json").write_text(
        json.dumps([_definition("Orphan_search"), _definition("Orphan_get")])
    )

    unwired = wiring.unwired_definitions(tmp_path)

    assert unwired == {"orphan_tools.json": ["Orphan_search", "Orphan_get"]}


def test_the_report_names_the_file_and_every_tool_in_it(tmp_path):
    """Reported by name and by file: a count alone does not tell you what to wire."""
    (tmp_path / "a_tools.json").write_text(json.dumps([_definition("A_one")]))
    (tmp_path / "b_tools.json").write_text(json.dumps([_definition("B_one")]))

    unwired = wiring.unwired_definitions(tmp_path)

    assert set(unwired) == {"a_tools.json", "b_tools.json"}
    assert unwired["a_tools.json"] == ["A_one"]


def test_a_file_dropped_into_remote_tools_is_wired_by_being_there(tmp_path):
    """That directory is loaded by a scan, not by a configured list."""
    remote = tmp_path / "remote_tools"
    remote.mkdir()
    (remote / "new_tools.json").write_text(json.dumps([_definition("Remote_one")]))

    assert wiring.unwired_definitions(tmp_path) == {}


# --- declared exceptions ---


def test_a_declared_collection_is_not_reported(tmp_path):
    """Deliberately unwired collections must be declarable, or the guard is red forever
    and gets deleted rather than fixed."""
    (tmp_path / "api_keys_catalog.json").write_text(
        json.dumps([{"name": "OPENAI_API_KEY", "type": "secret"}])
    )

    assert wiring.unwired_definitions(tmp_path) == {}


def test_a_declared_directory_covers_everything_beneath_it(tmp_path):
    archive = tmp_path / "broken_apis"
    archive.mkdir()
    (archive / "hmdb_tools.json").write_text(json.dumps([_definition("HMDB_get")]))

    assert wiring.unwired_definitions(tmp_path) == {}


def test_every_declaration_says_why():
    """An undeclared exception and a forgotten wiring bug look identical six months on."""
    for path, reason in wiring.DECLARED_UNWIRED.items():
        assert reason.strip(), path
        assert len(reason) > 30, (path, reason)


def test_the_declared_collections_are_still_there():
    """A declaration for a path that no longer exists is a stale waiver, and a stale waiver
    silently covers whatever is put at that path next."""
    data = wiring.data_dir()
    for path in wiring.DECLARED_UNWIRED:
        assert (data / path).exists(), path


# --- what it means for the persona linter ---


def test_the_loader_reachable_set_excludes_what_disk_scanning_accepts():
    """The blind spot, quantified: reading every JSON under data/ accepts names the server
    never serves, so a body naming an archived tool passes a disk check and fails live."""
    servable = wiring.servable_definition_names()

    on_disk = set()
    for path, names in wiring.definitions_by_file().items():
        on_disk.update(names)

    only_on_disk = on_disk - servable
    assert only_on_disk, "expected the archive and the key catalogue to be excluded"
    assert "OPENAI_API_KEY" in only_on_disk, sorted(only_on_disk)[:10]
    assert servable < on_disk
