"""Direct calls to Squirro (genai) tools in a Replay (ADR-0021 amended, SA-06a).

A Saved Analysis names such a call `squirro:<project>:<agent>:<tool_id>`. SMCP makes it through
genai's `POST /v0/tools/execute`, which takes no agent id, so the options come from the agent the
analysis was saved from, read at run time. Only tools with no required secret option are saved
this way: genai never returns a `writeOnly` option, so those tools stay Delegated calls.

SMCP authenticates with a Squirro service token (`SQUIRRO_REPLAY_TOKEN`, a refresh token) against
`SQUIRRO_CLUSTER_URL`. Nothing here stores an option value.
"""

from __future__ import annotations

import os
import threading
import time
from typing import Any, Callable

import requests

PREFIX = "squirro:"
TIMEOUT = 300           # a Clinical Trials search can take minutes
_TOKEN_MARGIN = 60      # renew this many seconds before the access token expires
_AGENT_SECONDS = 300    # an agent's options are read at most this often
# Squirro answers the token endpoint in XML unless JSON is asked for (seen on sr-dev).
_JSON = {"Accept": "application/json"}


class SquirroToolError(RuntimeError):
    """A direct call that could not be made, or that the tool itself refused."""


def call_name(project_id: str, agent_id: str, tool_id: str) -> str:
    return f"{PREFIX}{project_id}:{agent_id}:{tool_id}"


def _parts(name: str) -> tuple[str, str, str]:
    if not name.startswith(PREFIX):
        raise SquirroToolError(f"{name!r} is not a direct Squirro call")
    parts = name[len(PREFIX):].split(":", 2)
    if len(parts) != 3 or not all(parts):
        raise SquirroToolError(f"{name!r} does not name a project, an agent and a tool")
    return parts[0], parts[1], parts[2]


class SquirroTools:
    """Makes direct calls for one SMCP process; safe to share between activity threads."""

    def __init__(self, cluster: str, refresh_token: str, session: Any = requests):
        self.cluster, self.refresh_token, self.session = cluster.rstrip("/"), refresh_token, session
        self._lock = threading.Lock()
        self._token: tuple[str, float] | None = None
        self._agents: dict[tuple[str, str], tuple[dict, float]] = {}

    @classmethod
    def from_env(cls) -> SquirroTools | None:
        cluster, token = os.environ.get("SQUIRRO_CLUSTER_URL"), os.environ.get("SQUIRRO_REPLAY_TOKEN")
        return cls(cluster, token) if cluster and token else None

    def _access_token(self) -> str:
        with self._lock:
            if self._token and self._token[1] > time.monotonic():
                return self._token[0]
            r = self.session.post(f"{self.cluster}/api/user/oauth2/token", timeout=60,
                                  headers=_JSON,
                                  data={"grant_type": "refresh_token",
                                        "refresh_token": self.refresh_token})
            if not r.ok:
                raise SquirroToolError(f"the Squirro service token was refused: HTTP {r.status_code}")
            body = r.json()
            ttl = float(body.get("expires_in") or 600)
            self._token = (body["access_token"], time.monotonic() + max(ttl - _TOKEN_MARGIN, 30))
            return self._token[0]

    def _options(self, project: str, agent: str, tool_id: str) -> dict:
        key = (project, agent)
        with self._lock:
            cached = self._agents.get(key)
        if not cached or cached[1] <= time.monotonic():
            r = self.session.get(f"{self.cluster}/service/genai/v0/projects/{project}/agents/{agent}",
                                 headers={**_JSON, "Authorization": f"Bearer {self._access_token()}"},
                                 timeout=60)
            if not r.ok:
                raise SquirroToolError(f"the agent {agent} could not be read: HTTP {r.status_code}")
            cached = (r.json(), time.monotonic() + _AGENT_SECONDS)
            with self._lock:
                self._agents[key] = cached
        tools = (cached[0].get("toolkit") or {}).get("tools") or []
        match = next((t for t in tools if t.get("tool_id") == tool_id), None)
        if match is None:
            raise SquirroToolError(f"the agent {agent} no longer has the tool {tool_id}")
        return dict(match.get("options") or {})

    def execute(self, name: str, arguments: dict) -> Any:
        """Run the named tool; its result as genai returns it (a JSON string for our plugins)."""
        project, agent, tool_id = _parts(name)
        options = self._options(project, agent, tool_id)
        r = self.session.post(f"{self.cluster}/service/genai/v0/tools/execute", timeout=TIMEOUT,
                              headers={**_JSON, "Authorization": f"Bearer {self._access_token()}"},
                              json={"tool_id": tool_id, "tool_options": options,
                                    "inputs": dict(arguments or {})})
        if not r.ok:
            raise SquirroToolError(f"{tool_id} answered HTTP {r.status_code}")
        body = r.json()
        if not body.get("success"):
            raise SquirroToolError(f"{tool_id} failed: {body.get('error')}")
        return body.get("result")


def routed(dispatch: Callable[[dict], Any], squirro: SquirroTools | None) -> Callable[[dict], Any]:
    """ToolUniverse's dispatch, with direct Squirro calls sent to genai instead."""
    def route(call: dict) -> Any:
        name = call.get("name") or ""
        if not name.startswith(PREFIX):
            return dispatch(call)
        if squirro is None:
            raise SquirroToolError("direct Squirro calls need SQUIRRO_CLUSTER_URL and "
                                   "SQUIRRO_REPLAY_TOKEN in SMCP's environment")
        return squirro.execute(name, call.get("arguments") or {})
    return route
