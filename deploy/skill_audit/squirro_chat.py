"""Minimal Squirro GenAI chat client — enough to drive one turn against an agent.

Deliberately self-contained. The audit lives in this repo, beside the skill bodies
it scores, so it cannot import the delivery repo's fuller `chat_sweep` client: a
clean clone of this fork has no delivery repo beside it, and the dependency only
runs one way (delivery installs this package, never the reverse).

Two cluster quirks are encapsulated here. The token endpoint answers in XML, not
JSON. And the chat endpoint is SSE — `_invoke` is broken platform-wide — so the
result arrives as an `event: result` frame among a stream of others.
"""
from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field

import requests

TOKEN_URL = "{cluster}/api/user/oauth2/token"
STREAMING_URL = "{cluster}/service/genai/v0/projects/{project}/streaming_chat"


class TokenExchangeError(RuntimeError):
    pass


@dataclass
class Turn:
    """One agent turn: the answer, the action trace, and how it ended."""
    answer: str = ""
    actions: list[dict] = field(default_factory=list)
    calls: list[str] = field(default_factory=list)
    error: str | None = None
    http_status: int = 0


def get_access_token(cluster: str, refresh_token: str, *, timeout: int = 30) -> str:
    try:
        resp = requests.post(
            TOKEN_URL.format(cluster=cluster.rstrip("/")),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=f"grant_type=refresh_token&refresh_token={refresh_token}",
            timeout=timeout,
        )
    except requests.RequestException as exc:
        raise TokenExchangeError(f"request failed: {exc}") from exc
    if not resp.ok:
        raise TokenExchangeError(
            f"HTTP {resp.status_code} from oauth2/token: {resp.text[:200]}")
    match = re.search(r"<access_token>([^<]+)</access_token>", resp.text)
    if not match:
        raise TokenExchangeError(f"no access_token in body: {resp.text[:200]}")
    return match.group(1)


class SquirroChatClient:
    def __init__(self, cluster: str, refresh_token: str, project_id: str):
        self.cluster = cluster.rstrip("/")
        self.project_id = project_id
        self._refresh = refresh_token
        self._access = get_access_token(self.cluster, refresh_token)

    def ask(self, agent_id: str, instruction: str, *, timeout: int = 600) -> Turn:
        """One question in a FRESH conversation.

        Fresh every time on purpose: Squirro binds the MCP tool list per
        conversation, so re-using one leaks a stale tool list between skills.
        """
        payload = {
            "instruction": instruction,
            "agent_id": agent_id,
            "conversation_id": str(uuid.uuid4()),
            "runtime_config": {
                "squirro_refresh_token": self._refresh,
                "squirro_cluster": self.cluster,
                "squirro_project_id": self.project_id,
            },
        }
        url = STREAMING_URL.format(cluster=self.cluster, project=self.project_id)
        for attempt in (1, 2):
            headers = {"Content-Type": "application/json",
                       "Accept": "text/event-stream",
                       "Authorization": f"Bearer {self._access}"}
            try:
                resp = requests.post(url, headers=headers, json=payload,
                                     timeout=timeout, stream=True)
            except requests.exceptions.Timeout:
                return Turn(error="timeout")
            except requests.RequestException as exc:
                return Turn(error=f"request_error: {exc}")
            if resp.status_code == 401 and attempt == 1:
                self._access = get_access_token(self.cluster, self._refresh)
                continue
            break

        if not resp.ok:
            return Turn(error=f"http_{resp.status_code}",
                        http_status=resp.status_code)

        result, error = parse_sse(resp.iter_lines(decode_unicode=True))
        if result is None:
            return Turn(error=error or "missing_result",
                        http_status=resp.status_code)
        actions = result.get("actions") or []
        return Turn(
            answer=result.get("answer") or "",
            actions=actions,
            calls=[a.get("tool_name") for a in actions if a.get("tool_name")],
            error=error or None,
            http_status=resp.status_code,
        )


def parse_sse(lines) -> tuple[dict | None, str]:
    """Pull the `result` frame out of an SSE stream.

    Returns (result, error). An `error` frame wins over a result: that is how a
    provider refusal arrives, and it must not be mistaken for a thin answer.
    """
    event = ""
    data: list[str] = []
    result: dict | None = None
    error = ""

    def flush(name: str, payload: list[str]) -> None:
        nonlocal result, error
        if not name:
            return
        text = "\n".join(payload)
        try:
            parsed = json.loads(text) if text else None
        except (json.JSONDecodeError, ValueError):
            parsed = text
        if name == "result" and isinstance(parsed, dict):
            result = parsed
        elif name == "error":
            error = parsed if isinstance(parsed, str) else str(parsed)

    for raw in lines:
        line = raw if raw is not None else ""
        if line.startswith("event:"):
            event = line[len("event:"):].strip()
        elif line.startswith("data:"):
            data.append(line[len("data:"):].strip())
        elif line == "":
            flush(event, data)
            event, data = "", []
    flush(event, data)

    if error:
        return None, error
    return result, ""
