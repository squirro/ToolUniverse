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
from collections.abc import Iterator
import re
import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path

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


def payload_for(agent_id: str, instruction: str, conversation_id: str,
                refresh_token: str, cluster: str, project_id: str) -> dict:
    """The body of one streaming_chat turn.

    The route builds the agent's runtime config from `runtime_config` alone (plus the path
    variables and the agent's own config); the top-level `conversation_id` names the thread
    for the history but never reaches a tool's `conversation_id` placeholder. Tools that need
    the conversation -- the code container is keyed by it -- get it only from here.
    """
    return {
        "instruction": instruction,
        "agent_id": agent_id,
        "conversation_id": conversation_id,
        "runtime_config": {
            "squirro_refresh_token": refresh_token,
            "squirro_cluster": cluster,
            "squirro_project_id": project_id,
            "conversation_id": conversation_id,
        },
    }


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
        payload = payload_for(agent_id, instruction, str(uuid.uuid4()),
                              self._refresh, self.cluster, self.project_id)
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

        return turn_from(resp.iter_content(chunk_size=None), resp.status_code)


def lines_of(chunks) -> Iterator[str]:
    """The lines of a byte stream, split on newline ONLY.

    `iter_lines(decode_unicode=True)` splits like `str.splitlines()`: on U+2028 and its
    relatives too. One such character in a tool output cut the result frame mid-JSON, and a
    turn the service had logged as a success read as a dead one.
    """
    pending = b""
    for chunk in chunks:
        pending += chunk
        *whole, pending = pending.split(b"\n")
        for line in whole:
            yield line.rstrip(b"\r").decode("utf-8", errors="replace")
    if pending:
        yield pending.rstrip(b"\r").decode("utf-8", errors="replace")


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


def turn_from(chunks, http_status: int, dump_dir: str | Path | None = None) -> Turn:
    """One turn read off the wire. A stream with no result frame is kept, whole, on disk."""
    raw = b"".join(chunks)
    result, error = parse_sse(lines_of([raw]))
    if result is None:
        if error:
            return Turn(error=error, http_status=http_status)
        directory = Path(dump_dir) if dump_dir else Path(tempfile.gettempdir())
        saved = directory / f"sse-missing-result-{uuid.uuid4().hex[:8]}.txt"
        saved.write_bytes(raw)
        return Turn(error=f"missing_result (raw stream: {saved})", http_status=http_status)
    actions = result.get("actions") or []
    return Turn(
        answer=result.get("answer") or "",
        actions=actions,
        calls=[a.get("tool_name") for a in actions if a.get("tool_name")],
        error=None,
        http_status=http_status,
    )


STUDIO_PROXY_URL = "{cluster}/studio/genai_proxy/projects/{project}/streaming_chat"


class StudioProxyChatClient(SquirroChatClient):
    """The same one-turn client, through the Studio genai proxy.

    On swiss-rockets-dev.squirro.com the documented /service/genai route is blocked
    by nginx (405); the UI goes through a Studio proxy plugin that authenticates with
    the refresh token as a query parameter. Same SSE stream, same result frame.
    """

    def __init__(self, cluster: str, refresh_token: str, project_id: str):
        self.cluster = cluster.rstrip("/")
        self.project_id = project_id
        self._refresh = refresh_token

    def ask(self, agent_id: str, instruction: str, *, timeout: int = 600) -> Turn:
        payload = {"instruction": instruction, "agent_id": agent_id,
                   "conversation_id": str(uuid.uuid4())}
        url = STUDIO_PROXY_URL.format(cluster=self.cluster, project=self.project_id)
        try:
            resp = requests.post(url, params={"token": self._refresh},
                                 headers={"Content-Type": "application/json",
                                          "Accept": "text/event-stream"},
                                 json=payload, timeout=timeout, stream=True)
        except requests.exceptions.Timeout:
            return Turn(error="timeout")
        except requests.RequestException as exc:
            return Turn(error=f"request_error: {exc}")
        if not resp.ok:
            return Turn(error=f"http_{resp.status_code}", http_status=resp.status_code)
        return turn_from(resp.iter_content(chunk_size=None), resp.status_code)
