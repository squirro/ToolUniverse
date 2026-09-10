#!/usr/bin/env python3
"""Publish the reviewed Skill Processes to GraphDB (ADR-0016, DSR-709).

    GRAPHDB_ENDPOINT=http://localhost:7200 GRAPHDB_USERNAME=… GRAPHDB_PASSWORD=… \\
        python publish_skill_graphs.py            # every YAML under data/skill_graphs
    python publish_skill_graphs.py rare-disease-diagnosis   # one

Each process replaces its own named graph in the `skill-processes` repository
(created if absent), stamped with the git commit and the definition hash. The YAML
in the repo stays authoritative; this is the deploy step that makes GraphDB agree.
"""
import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tooluniverse.skill_graph import GRAPHS_DIR, load_graph  # noqa: E402
from tooluniverse.skill_process_store import Store  # noqa: E402


def _git_commit() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"],
                                       cwd=Path(__file__).parent, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("skills", nargs="*", help="skill ids; default: every shipped process")
    ap.add_argument("--verify", action="store_true",
                    help="load each published process back and compare with the YAML")
    args = ap.parse_args()

    store = Store.from_env()
    store.ensure_repository()
    commit = _git_commit()
    skills = args.skills or sorted(p.stem for p in GRAPHS_DIR.glob("*.yaml"))
    for skill in skills:
        process = load_graph(skill)
        iri = store.publish(process, git_commit=commit)
        line = f"published {skill} -> {iri} (commit {commit})"
        if args.verify:
            loaded, prov = store.load(skill)
            line += "  verified" if loaded == process else "  MISMATCH"
            line += f"  hash={prov['definition_hash'][:12]}"
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
