"""Minimal FastAPI proxy for a deployed A2A agent (Agent Runtime, agents-cli 1.1.0+).

The browser talks ONLY to this proxy (same origin, no CORS, no GCP creds in the
browser). The proxy authenticates with Application Default Credentials and
forwards chat to the deployed agent over the A2A protocol, returning replies as
structured parts the chat UI knows how to show:

  * {"kind": "text", "text": ...}  -> a normal chat bubble
  * {"kind": "a2ui", "data": ...}  -> one A2UI message (beginRendering /
    surfaceUpdate); static/index.html renders these as a card.

Why A2A: agents-cli 1.1.0 (GA) deploys ADK agents to Agent Runtime as A2A agents
and no longer registers the reasoning-engine operation schema the old
`agent_engines.get(...).stream_query()` path relied on (operation_schemas() comes
back empty). The container serves the A2A protocol over the Agent Engine HTTP
passthrough, so this proxy fetches the agent's card and sends messages with the
a2a-sdk client (the same path `agents-cli run --mode a2a` uses). This works for
both A2A and plain ADK 1.1.0 deployments (the container serves A2A either way).

Run:
  pip install -r requirements.txt
  export AGENT_ENGINE_RESOURCE_NAME="projects/.../locations/.../reasoningEngines/..."
  export AGENT_DIRECTORY="app"   # your agent's app directory (agents-cli-manifest.yaml)
  python main.py                 # -> http://localhost:8080
"""

import os
import uuid

import google.auth
import google.auth.transport.requests
import httpx
from a2a.client import ClientConfig, ClientFactory
from a2a.types import (
    AgentCard,
    FilePart,
    Message,
    Part,
    Role,
    TaskArtifactUpdateEvent,
    TextPart,
    TransportProtocol,
)
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

RESOURCE = os.environ.get(
    "AGENT_ENGINE_RESOURCE_NAME",
    "projects/625300775459/locations/us-east1/reasoningEngines/9181253044929560576",
)
# The agent's app directory (matches agent_directory in agents-cli-manifest.yaml).
AGENT_DIRECTORY = os.environ.get("AGENT_DIRECTORY", "app")
# Location is embedded in the resource name: projects/<p>/locations/<loc>/reasoningEngines/<id>.
LOCATION = RESOURCE.split("/locations/")[1].split("/")[0]

A2A_BASE = os.environ.get("A2A_BASE", (
    f"https://{LOCATION}-aiplatform.googleapis.com/reasoningEngines/v1/"
    f"{RESOURCE}/api/a2a/{AGENT_DIRECTORY}"
))
A2A_CARD_URL = f"{A2A_BASE}/.well-known/agent-card.json"

# The agent tags its A2UI data parts with this mime type.
_A2UI_MIME = "application/json+a2ui"

# One set of ADC credentials, refreshed per request (access tokens expire ~1h).
_creds, _ = google.auth.default(
    scopes=["https://www.googleapis.com/auth/cloud-platform"]
)


def _auth_headers() -> dict[str, str]:
    if "localhost" in A2A_BASE or "127.0.0.1" in A2A_BASE:
        return {"Content-Type": "application/json"}
    _creds.refresh(google.auth.transport.requests.Request())
    return {
        "Authorization": f"Bearer {_creds.token}",
        "Content-Type": "application/json",
    }


app = FastAPI()


@app.exception_handler(Exception)
async def _json_errors(request: Request, exc: Exception):
    # Always return JSON so the browser never receives a plain-text 500 page
    # (which shows up in the chat as "Unexpected token 'I', "Internal S"... is
    # not valid JSON"). Any server-side failure now surfaces as a readable
    # message in the chat bubble instead.
    return JSONResponse(
        status_code=200,
        content={
            "parts": [{"kind": "text", "text": f"Error: {type(exc).__name__}: {exc}"}]
        },
    )


# Reuse ONE A2A context per user so the agent remembers the conversation.
_contexts: dict[str, str] = {}
# Cache the agent card after the first fetch.
_card: AgentCard | None = None


async def _get_card(client: httpx.AsyncClient) -> AgentCard:
    global _card
    if _card is None:
        resp = await client.get(A2A_CARD_URL)
        resp.raise_for_status()
        card = AgentCard(**resp.json())
        # Agent Runtime does not serve a public card URL, so point the client at
        # the passthrough base for message sends.
        card.url = A2A_BASE
        _card = card
    return _card


import json
import re

_A2UI_TAG_PATTERN = re.compile(r"<(?:a2a_datapart_json|a2ui-json)>([\s\S]*?)</(?:a2a_datapart_json|a2ui-json)>", re.DOTALL)
_CODE_BLOCK_PATTERN = re.compile(r"```(?:json|a2ui)?\s*([\s\S]*?)\s*```", re.DOTALL)


def _normalize_a2ui_payload(data: any) -> list[dict]:
    """Normalize various A2UI payload structures into standard A2UI messages.

    Handles:
      - Raw dictionary with {"surfaceId": ..., "components": [...]}
      - List of component definitions [{"id": ..., "component": ...}]
      - List of standard messages [{"beginRendering": ...}, {"surfaceUpdate": ...}]
      - Single message dictionary
    """
    if isinstance(data, dict):
        if "components" in data:
            sid = data.get("surfaceId", "default")
            comps = data["components"]
            root_id = "root" if any(c.get("id") == "root" for c in comps) else (comps[0].get("id") if comps else None)
            msgs = []
            if root_id:
                msgs.append({"beginRendering": {"surfaceId": sid, "root": root_id}})
            msgs.append({"surfaceUpdate": {"surfaceId": sid, "components": comps}})
            return msgs
        elif any(k in data for k in ("beginRendering", "surfaceUpdate", "dataModelUpdate")):
            return [data]
        elif "id" in data and "component" in data:
            return [{"surfaceUpdate": {"surfaceId": "default", "components": [data]}}]
    elif isinstance(data, list):
        if data and isinstance(data[0], dict):
            if "id" in data[0] and "component" in data[0]:
                root_id = "root" if any(c.get("id") == "root" for c in data) else data[0].get("id")
                msgs = []
                if root_id:
                    msgs.append({"beginRendering": {"surfaceId": "default", "root": root_id}})
                msgs.append({"surfaceUpdate": {"surfaceId": "default", "components": data}})
                return msgs
            else:
                return data
    return []


def _try_parse_a2ui(candidate: str):
    candidate = candidate.strip()
    if not (candidate.startswith("{") or candidate.startswith("[")):
        return None
    try:
        data = json.loads(candidate)
        if isinstance(data, dict) and data.get("kind") == "data" and "data" in data:
            data = data["data"]
        
        if isinstance(data, dict):
            if "components" in data or any(k in data for k in ("beginRendering", "surfaceUpdate")):
                return _normalize_a2ui_payload(data)
        elif isinstance(data, list):
            if data and isinstance(data[0], dict) and ("id" in data[0] or "components" in data[0] or "beginRendering" in data[0] or "surfaceUpdate" in data[0]):
                return _normalize_a2ui_payload(data)
    except Exception:
        pass
    return None


def _extract_parts(parts: list) -> list[dict]:
    """Turn A2A response parts into structured parts for the chat UI."""
    out: list[dict] = []
    for p in parts:
        root = getattr(p, "root", p)
        text = getattr(root, "text", getattr(p, "text", None))
        inline_data = getattr(root, "inline_data", getattr(p, "inline_data", None))
        data_attr = getattr(root, "data", getattr(p, "data", None))

        if data_attr:
            if isinstance(data_attr, dict):
                inner_data = data_attr.get("data", data_attr)
                if isinstance(inner_data, dict):
                    if "components" in inner_data or any(k in inner_data for k in ("beginRendering", "surfaceUpdate")):
                        for m in _normalize_a2ui_payload(inner_data) or []:
                            out.append({"kind": "a2ui", "data": m})
                        continue

        if inline_data and getattr(inline_data, "data", None):
            try:
                text = inline_data.data.decode("utf-8")
            except Exception:
                pass

        if text:
            
            # 1. Match <a2ui-json> tags
            a2ui_matches = list(_A2UI_TAG_PATTERN.finditer(text))
            if a2ui_matches:
                last_idx = 0
                for match in a2ui_matches:
                    prefix = text[last_idx:match.start()].strip()
                    if prefix:
                        out.append({"kind": "text", "text": prefix})
                    raw_json = match.group(1).strip()
                    parsed_msgs = _try_parse_a2ui(raw_json)
                    if parsed_msgs:
                        for m in parsed_msgs:
                            out.append({"kind": "a2ui", "data": m})
                    else:
                        out.append({"kind": "text", "text": raw_json})
                    last_idx = match.end()
                suffix = text[last_idx:].strip()
                if suffix:
                    out.append({"kind": "text", "text": suffix})
                continue

            # 2. Match ```json ... ``` code blocks containing A2UI
            code_matches = list(_CODE_BLOCK_PATTERN.finditer(text))
            if code_matches:
                last_idx = 0
                extracted_any = False
                temp_out = []
                for match in code_matches:
                    prefix = text[last_idx:match.start()].strip()
                    if prefix:
                        temp_out.append({"kind": "text", "text": prefix})
                    candidate = match.group(1).strip()
                    parsed_msgs = _try_parse_a2ui(candidate)
                    if parsed_msgs:
                        extracted_any = True
                        for m in parsed_msgs:
                            temp_out.append({"kind": "a2ui", "data": m})
                    else:
                        temp_out.append({"kind": "text", "text": match.group(0)})
                    last_idx = match.end()
                suffix = text[last_idx:].strip()
                if suffix:
                    temp_out.append({"kind": "text", "text": suffix})
                
                if extracted_any:
                    out.extend(temp_out)
                    continue

            # 3. Direct raw JSON string check
            parsed_msgs = _try_parse_a2ui(text)
            if parsed_msgs:
                for m in parsed_msgs:
                    out.append({"kind": "a2ui", "data": m})
                continue

            out.append({"kind": "text", "text": text})

        elif getattr(root, "data", None) is not None:
            meta = getattr(root, "metadata", None) or {}
            mime = meta.get("mimeType") if isinstance(meta, dict) else None
            if mime == _A2UI_MIME:
                for m in _normalize_a2ui_payload(root.data):
                    out.append({"kind": "a2ui", "data": m})
        elif isinstance(root, FilePart):
            uri = getattr(getattr(root, "file", None), "uri", None)
            if uri:
                out.append({"kind": "text", "text": uri})
    return out


@app.post("/chat")
async def chat(req: Request):
    body = await req.json()
    message = body.get("message", "")
    user_id = body.get("user_id") or "web-user"
    parts: list[dict] = []

    async with httpx.AsyncClient(headers=_auth_headers(), timeout=120) as client:
        card = await _get_card(client)
        factory = ClientFactory(
            ClientConfig(
                supported_transports=[
                    TransportProtocol.jsonrpc,
                    TransportProtocol.http_json,
                ],
                httpx_client=client,
            )
        )
        a2a_client = factory.create(card)

        msg = Message(
            message_id=str(uuid.uuid4()),
            role=Role.user,
            parts=[Part(root=TextPart(text=message))],
            context_id=_contexts.get(user_id),
        )

        last_task = None
        got_artifact_update = False
        async for event in a2a_client.send_message(msg):
            if not isinstance(event, tuple):
                continue
            task, update = event
            if task is not None:
                last_task = task
                if getattr(task, "context_id", None):
                    _contexts[user_id] = task.context_id
            if isinstance(update, TaskArtifactUpdateEvent):
                got_artifact_update = True
                parts.extend(_extract_parts(update.artifact.parts))

        # Non-streaming fallback: pull parts from the final task's artifacts.
        if not got_artifact_update and last_task is not None:
            for artifact in getattr(last_task, "artifacts", None) or []:
                parts.extend(_extract_parts(artifact.parts))
            
            # If still no parts, inspect last_task.history for agent text/ui parts
            if not parts and getattr(last_task, "history", None):
                for hist_msg in reversed(last_task.history):
                    if getattr(hist_msg, "role", None) == Role.model and getattr(hist_msg, "parts", None):
                        extracted = _extract_parts(hist_msg.parts)
                        if extracted:
                            parts.extend(extracted)
                            break

    if not parts:
        parts = [{"kind": "text", "text": "(The agent didn't return a reply.)"}]
    return JSONResponse({"parts": parts})


# Serve the chat UI (keep this mount last so /chat wins).
app.mount("/", StaticFiles(directory="static", html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
