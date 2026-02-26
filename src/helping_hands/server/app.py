"""FastAPI application for app mode.

Exposes an HTTP API that enqueues repo-building jobs via Celery.
"""

from __future__ import annotations

import ast
import html
import json
import os
from typing import Any, Literal
from urllib import error as urllib_error
from urllib import request as urllib_request
from urllib.parse import urlencode

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, ValidationError

from helping_hands.lib.default_prompts import DEFAULT_SMOKE_TEST_PROMPT
from helping_hands.server.celery_app import build_feature, celery_app
from helping_hands.server.task_result import normalize_task_result

app = FastAPI(
    title="helping_hands",
    description="AI-powered repo builder — app mode.",
    version="0.1.0",
)


class BuildRequest(BaseModel):
    """Request body for the /build endpoint."""

    repo_path: str
    prompt: str
    backend: Literal[
        "e2e",
        "basic-langgraph",
        "basic-atomic",
        "basic-agent",
        "codexcli",
        "claudecodecli",
        "goose",
        "geminicli",
    ] = "codexcli"
    model: str | None = None
    max_iterations: int = 6
    no_pr: bool = False
    enable_execution: bool = False
    enable_web: bool = False
    use_native_cli_auth: bool = False
    pr_number: int | None = None


BackendName = Literal[
    "e2e",
    "basic-langgraph",
    "basic-atomic",
    "basic-agent",
    "codexcli",
    "claudecodecli",
    "goose",
    "geminicli",
]


class BuildResponse(BaseModel):
    """Response for an enqueued build job."""

    task_id: str
    status: str
    backend: str


class TaskStatus(BaseModel):
    """Response for checking task status."""

    task_id: str
    status: str
    result: dict[str, Any] | None = None


class CurrentTask(BaseModel):
    """Summary of a currently active/queued task."""

    task_id: str
    status: str
    backend: str | None = None
    repo_path: str | None = None
    worker: str | None = None
    source: str


class CurrentTasksResponse(BaseModel):
    """Response for listing currently active/queued task UUIDs."""

    tasks: list[CurrentTask]
    source: str


_TERMINAL_TASK_STATES = {"SUCCESS", "FAILURE", "REVOKED"}
_CURRENT_TASK_STATES = {
    "PENDING",
    "QUEUED",
    "RECEIVED",
    "STARTED",
    "RUNNING",
    "PROGRESS",
    "RETRY",
    "RESERVED",
    "SCHEDULED",
    "SENT",
}
_TASK_STATE_PRIORITY = {
    "STARTED": 6,
    "RUNNING": 6,
    "PROGRESS": 6,
    "RETRY": 5,
    "RECEIVED": 4,
    "PENDING": 3,
    "QUEUED": 3,
    "SENT": 3,
    "RESERVED": 2,
    "SCHEDULED": 1,
}
_BACKEND_LOOKUP: dict[str, BackendName] = {
    "e2e": "e2e",
    "basic-langgraph": "basic-langgraph",
    "basic-atomic": "basic-atomic",
    "basic-agent": "basic-agent",
    "codexcli": "codexcli",
    "claudecodecli": "claudecodecli",
    "goose": "goose",
    "geminicli": "geminicli",
}
_FLOWER_API_URL_ENV = "HELPING_HANDS_FLOWER_API_URL"
_FLOWER_API_TIMEOUT_SECONDS_ENV = "HELPING_HANDS_FLOWER_API_TIMEOUT_SECONDS"
_DEFAULT_FLOWER_API_TIMEOUT_SECONDS = 0.75
_HELPING_HANDS_TASK_NAME = "helping_hands.build_feature"


_UI_HTML = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>helping_hands runner</title>
    <style>
      :root {
        --bg: #f4f7f8;
        --panel: #ffffff;
        --text: #0f172a;
        --muted: #475569;
        --accent: #0f766e;
        --border: #d8e0e3;
      }
      * { box-sizing: border-box; }
      body {
        margin: 0;
        padding: 24px;
        font-family: ui-sans-serif, -apple-system, BlinkMacSystemFont,
          "Segoe UI", sans-serif;
        background: linear-gradient(180deg, #eef6f5 0%, var(--bg) 100%);
        color: var(--text);
      }
      .container {
        max-width: 920px;
        margin: 0 auto;
        display: grid;
        gap: 16px;
      }
      .panel {
        background: var(--panel);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 16px;
      }
      h1 { margin: 0 0 8px 0; font-size: 1.4rem; }
      p { margin: 0; color: var(--muted); }
      form { display: grid; gap: 10px; margin-top: 14px; }
      label { font-size: 0.9rem; color: var(--muted); }
      input, textarea, select, button {
        font: inherit;
      }
      input, textarea, select {
        width: 100%;
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 10px;
      }
      input[type="checkbox"] {
        width: auto;
      }
      textarea { min-height: 120px; resize: vertical; }
      .row {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 10px;
      }
      .actions {
        display: flex;
        gap: 10px;
        flex-wrap: wrap;
      }
      button {
        border: 0;
        border-radius: 8px;
        padding: 10px 14px;
        background: var(--accent);
        color: #fff;
        cursor: pointer;
      }
      button.secondary {
        background: #334155;
      }
      pre {
        margin: 0;
        padding: 12px;
        border-radius: 8px;
        background: #0f172a;
        color: #d1fae5;
        overflow: auto;
        min-height: 160px;
      }
      .meta {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 10px;
        margin-bottom: 10px;
      }
      .updates {
        margin-top: 10px;
      }
      .checkbox-row {
        display: flex;
        align-items: center;
        gap: 8px;
      }
      @media (max-width: 720px) {
        .row, .meta { grid-template-columns: 1fr; }
      }
    </style>
  </head>
  <body>
    <div class="container">
      <section class="panel">
        <h1>helping_hands app runner</h1>
        <p>
          Submit a run to <code>/build</code> and monitor status via
          <code>/tasks/{task_id}</code>.
        </p>
        <form id="run-form" method="post" action="/build/form">
          <div>
            <label for="repo_path">Repo path (owner/repo)</label>
            <input
              id="repo_path"
              name="repo_path"
              value="suryarastogi/helping_hands"
              required
            />
          </div>
          <div>
            <label for="prompt">Prompt</label>
            <textarea id="prompt" name="prompt" required>
__DEFAULT_SMOKE_TEST_PROMPT__</textarea>
          </div>
          <div class="row">
            <div>
              <label for="backend">Backend</label>
              <select id="backend" name="backend">
                <option value="e2e">e2e</option>
                <option value="basic-langgraph">basic-langgraph</option>
                <option value="basic-atomic">basic-atomic</option>
                <option value="basic-agent">basic-agent</option>
                <option value="codexcli" selected>codexcli</option>
                <option value="claudecodecli">claudecodecli</option>
                <option value="goose">goose</option>
                <option value="geminicli">geminicli</option>
              </select>
            </div>
            <div>
              <label for="model">Model (optional)</label>
              <input id="model" name="model" placeholder="gpt-5.2" />
            </div>
          </div>
          <div class="row">
            <div>
              <label for="max_iterations">Max iterations</label>
              <input
                id="max_iterations"
                name="max_iterations"
                type="number"
                min="1"
                value="6"
              />
            </div>
            <div>
              <label for="pr_number">PR number (optional)</label>
              <input id="pr_number" name="pr_number" type="number" min="1" />
            </div>
          </div>
          <div class="row">
            <div class="checkbox-row">
              <input id="no_pr" name="no_pr" type="checkbox" />
              <label for="no_pr">Disable final PR push/create</label>
            </div>
            <div class="checkbox-row">
              <input id="enable_execution" name="enable_execution" type="checkbox" />
              <label for="enable_execution">Enable execution tools</label>
            </div>
          </div>
          <div class="row">
            <div class="checkbox-row">
              <input id="enable_web" name="enable_web" type="checkbox" />
              <label for="enable_web">Enable web tools</label>
            </div>
            <div class="checkbox-row">
              <input
                id="use_native_cli_auth"
                name="use_native_cli_auth"
                type="checkbox"
              />
              <label for="use_native_cli_auth">
                Use native CLI auth (Codex/Claude)
              </label>
            </div>
          </div>
          <div class="row">
            <div>
              <label for="task_id">Task ID (for manual monitor)</label>
              <input id="task_id" name="task_id" />
            </div>
          </div>
          <div class="actions">
            <button type="submit">Submit Run</button>
            <button id="monitor-btn" type="button" class="secondary">
              Monitor Task
            </button>
            <button id="stop-btn" type="button" class="secondary">Stop Polling</button>
          </div>
        </form>
      </section>

      <section class="panel">
        <div class="meta">
          <div><strong>Status:</strong> <span id="status">idle</span></div>
          <div><strong>Task:</strong> <span id="task_label">-</span></div>
        </div>
        <pre id="updates">No updates yet.</pre>
        <pre id="output" class="updates">{}</pre>
      </section>
    </div>

    <script>
      const form = document.getElementById("run-form");
      const monitorBtn = document.getElementById("monitor-btn");
      const stopBtn = document.getElementById("stop-btn");
      const statusEl = document.getElementById("status");
      const taskLabelEl = document.getElementById("task_label");
      const updatesEl = document.getElementById("updates");
      const outputEl = document.getElementById("output");
      const taskIdInput = document.getElementById("task_id");
      let pollHandle = null;

      function setStatus(value) {
        statusEl.textContent = value;
      }

      function setOutput(value) {
        outputEl.textContent = JSON.stringify(value, null, 2);
      }

      function setUpdates(value) {
        if (!value || value.length === 0) {
          updatesEl.textContent = "No updates yet.";
          return;
        }
        updatesEl.textContent = value.join("\n");
      }

      function isTerminal(status) {
        return ["SUCCESS", "FAILURE", "REVOKED"].includes(status);
      }

      async function pollTaskOnce(taskId) {
        const pollUrl = `/tasks/${encodeURIComponent(taskId)}?_=${Date.now()}`;
        const response = await fetch(pollUrl, { cache: "no-store" });
        if (!response.ok) {
          let details = "";
          try {
            const errData = await response.json();
            if (errData && typeof errData === "object") {
              details = errData.detail || JSON.stringify(errData);
            }
          } catch (_ignored) {
            details = await response.text();
          }
          const suffix = details ? `: ${details}` : "";
          throw new Error(`Task lookup failed: ${response.status}${suffix}`);
        }
        const data = await response.json();
        setStatus(data.status);
        if (Array.isArray(data?.result?.updates)) {
          setUpdates(data.result.updates);
        } else {
          setUpdates([]);
        }
        setOutput(data);
        if (isTerminal(data.status)) {
          stopPolling();
        }
      }

      function stopPolling() {
        if (pollHandle) {
          clearInterval(pollHandle);
          pollHandle = null;
        }
      }

      function startPolling(taskId) {
        stopPolling();
        taskLabelEl.textContent = taskId;
        pollTaskOnce(taskId).catch((err) => {
          setStatus("error");
          setOutput({ error: String(err) });
        });
        pollHandle = setInterval(() => {
          pollTaskOnce(taskId).catch((err) => {
            // Keep retrying; transient backend errors should not stop monitoring.
            setStatus("poll_error");
            setOutput({ error: String(err) });
          });
        }, 2000);
      }

      function applyQueryDefaults() {
        const params = new URLSearchParams(window.location.search);
        const repoPath = params.get("repo_path");
        const prompt = params.get("prompt");
        const backend = params.get("backend");
        const model = params.get("model");
        const maxIterations = params.get("max_iterations");
        const prNumber = params.get("pr_number");
        const noPr = params.get("no_pr");
        const enableExecution = params.get("enable_execution");
        const enableWeb = params.get("enable_web");
        const useNativeCliAuth = params.get("use_native_cli_auth");
        const taskId = params.get("task_id");
        const status = params.get("status");
        const error = params.get("error");

        if (repoPath) {
          document.getElementById("repo_path").value = repoPath;
        }
        if (prompt) {
          document.getElementById("prompt").value = prompt;
        }
        if (backend) {
          document.getElementById("backend").value = backend;
        }
        if (model) {
          document.getElementById("model").value = model;
        }
        if (maxIterations) {
          document.getElementById("max_iterations").value = maxIterations;
        }
        if (prNumber) {
          document.getElementById("pr_number").value = prNumber;
        }
        if (noPr === "1" || noPr === "true") {
          document.getElementById("no_pr").checked = true;
        }
        if (enableExecution === "1" || enableExecution === "true") {
          document.getElementById("enable_execution").checked = true;
        }
        if (enableWeb === "1" || enableWeb === "true") {
          document.getElementById("enable_web").checked = true;
        }
        if (useNativeCliAuth === "1" || useNativeCliAuth === "true") {
          document.getElementById("use_native_cli_auth").checked = true;
        }
        if (error) {
          setStatus("error");
          setOutput({ error });
        }
        if (taskId) {
          taskIdInput.value = taskId;
          setStatus(status || "queued");
          startPolling(taskId);
        }
      }

      applyQueryDefaults();

      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        setStatus("submitting");
        const repoPath = document.getElementById("repo_path").value.trim();
        const prompt = document.getElementById("prompt").value.trim();
        const backend = document.getElementById("backend").value;
        const model = document.getElementById("model").value.trim();
        const maxIterationsRaw = document.getElementById("max_iterations").value.trim();
        const prRaw = document.getElementById("pr_number").value.trim();
        const noPr = document.getElementById("no_pr").checked;
        const enableExecution = document.getElementById("enable_execution").checked;
        const enableWeb = document.getElementById("enable_web").checked;
        const useNativeCliAuth = document.getElementById("use_native_cli_auth").checked;
        const payload = {
          repo_path: repoPath,
          prompt,
          backend,
          max_iterations: maxIterationsRaw ? Number(maxIterationsRaw) : 6,
          no_pr: noPr,
          enable_execution: enableExecution,
          enable_web: enableWeb,
          use_native_cli_auth: useNativeCliAuth,
        };
        if (model) {
          payload.model = model;
        }
        if (prRaw) {
          payload.pr_number = Number(prRaw);
        }

        try {
          const response = await fetch("/build", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
          });
          const data = await response.json();
          if (!response.ok) {
            throw new Error(data?.detail || `Build enqueue failed: ${response.status}`);
          }
          taskIdInput.value = data.task_id;
          setUpdates([]);
          setOutput(data);
          setStatus(data.status);
          startPolling(data.task_id);
        } catch (err) {
          setStatus("error");
          setOutput({ error: String(err) });
        }
      });

      monitorBtn.addEventListener("click", () => {
        const taskId = taskIdInput.value.trim();
        if (!taskId) {
          setOutput({ error: "Provide a task_id to monitor." });
          return;
        }
        setStatus("monitoring");
        startPolling(taskId);
      });

      stopBtn.addEventListener("click", () => {
        stopPolling();
        setStatus("stopped");
      });
    </script>
  </body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def home() -> HTMLResponse:
    """Simple browser UI to submit and monitor build runs."""
    rendered = _UI_HTML.replace(
        "__DEFAULT_SMOKE_TEST_PROMPT__",
        html.escape(DEFAULT_SMOKE_TEST_PROMPT),
    )
    return HTMLResponse(rendered)


@app.get("/health")
def health() -> dict[str, str]:
    """Health check."""
    return {"status": "ok"}


def _enqueue_build_task(req: BuildRequest) -> BuildResponse:
    """Enqueue a build task and return a consistent response shape."""
    task = build_feature.delay(
        repo_path=req.repo_path,
        prompt=req.prompt,
        pr_number=req.pr_number,
        backend=req.backend,
        model=req.model,
        max_iterations=req.max_iterations,
        no_pr=req.no_pr,
        enable_execution=req.enable_execution,
        enable_web=req.enable_web,
        use_native_cli_auth=req.use_native_cli_auth,
    )
    return BuildResponse(task_id=task.id, status="queued", backend=req.backend)


def _parse_backend(value: str) -> BackendName:
    """Validate backend values coming from untyped form submissions."""
    normalized = value.strip().lower()
    backend = _BACKEND_LOOKUP.get(normalized)
    if backend is None:
        choices = ", ".join(_BACKEND_LOOKUP.keys())
        msg = f"unsupported backend {value!r}; expected one of: {choices}"
        raise ValueError(msg)
    return backend


def _build_task_status(task_id: str) -> TaskStatus:
    """Fetch and normalize current Celery task status."""
    result = build_feature.AsyncResult(task_id)
    raw_result = result.result if result.ready() else result.info
    normalized_result = normalize_task_result(result.status, raw_result)
    return TaskStatus(
        task_id=task_id,
        status=result.status,
        result=normalized_result,
    )


def _task_state_priority(status: str) -> int:
    """Return a relative sort priority for active task states."""
    return _TASK_STATE_PRIORITY.get(status.upper(), 0)


def _normalize_task_status(raw: Any, *, default: str) -> str:
    """Normalize arbitrary state/status values into uppercase labels."""
    text = str(raw or "").strip().upper()
    return text or default


def _extract_task_id(entry: dict[str, Any]) -> str | None:
    """Extract a task UUID from Celery/Flower payload shapes."""
    for key in ("task_id", "uuid", "id"):
        value = entry.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    request_payload = entry.get("request")
    if isinstance(request_payload, dict):
        return _extract_task_id(request_payload)
    return None


def _extract_task_name(entry: dict[str, Any]) -> str | None:
    """Extract task name from Celery/Flower payload shapes."""
    for key in ("name", "task"):
        value = entry.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    request_payload = entry.get("request")
    if isinstance(request_payload, dict):
        return _extract_task_name(request_payload)
    return None


def _extract_task_kwargs(entry: dict[str, Any]) -> dict[str, Any]:
    """Extract kwargs payload if available as an already-decoded mapping."""
    kwargs_payload = entry.get("kwargs")
    if isinstance(kwargs_payload, dict):
        return kwargs_payload
    if isinstance(kwargs_payload, str):
        parsed_kwargs = _parse_task_kwargs_str(kwargs_payload)
        if parsed_kwargs:
            return parsed_kwargs
    request_payload = entry.get("request")
    if isinstance(request_payload, dict):
        request_kwargs = request_payload.get("kwargs")
        if isinstance(request_kwargs, dict):
            return request_kwargs
        if isinstance(request_kwargs, str):
            parsed_request_kwargs = _parse_task_kwargs_str(request_kwargs)
            if parsed_request_kwargs:
                return parsed_request_kwargs
    return {}


def _coerce_optional_str(value: Any) -> str | None:
    """Convert arbitrary values into trimmed optional strings."""
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _parse_task_kwargs_str(raw: str) -> dict[str, Any]:
    """Parse kwargs strings from Flower/Celery payloads into a mapping."""
    text = raw.strip()
    if not text:
        return {}
    try:
        json_payload = json.loads(text)
    except ValueError:
        json_payload = None
    if isinstance(json_payload, dict):
        return json_payload
    try:
        literal_payload = ast.literal_eval(text)
    except (SyntaxError, ValueError):
        literal_payload = None
    if isinstance(literal_payload, dict):
        return literal_payload
    return {}


def _is_helping_hands_task(entry: dict[str, Any]) -> bool:
    """Filter out unrelated Celery tasks when task name is available."""
    task_name = _extract_task_name(entry)
    if not task_name:
        return True
    return task_name == _HELPING_HANDS_TASK_NAME


def _upsert_current_task(
    tasks_by_id: dict[str, dict[str, Any]],
    *,
    task_id: str,
    status: str,
    backend: str | None,
    repo_path: str | None,
    worker: str | None,
    source: str,
) -> None:
    """Insert/merge a discovered task summary keyed by UUID."""
    incoming = {
        "task_id": task_id,
        "status": status,
        "backend": backend,
        "repo_path": repo_path,
        "worker": worker,
        "source": source,
    }
    existing = tasks_by_id.get(task_id)
    if existing is None:
        tasks_by_id[task_id] = incoming
        return

    if _task_state_priority(status) >= _task_state_priority(existing["status"]):
        existing["status"] = status

    for key in ("backend", "repo_path", "worker"):
        if not existing.get(key) and incoming.get(key):
            existing[key] = incoming[key]

    if source and source not in str(existing.get("source", "")).split("+"):
        merged = sorted(
            set([*str(existing.get("source", "")).split("+"), source]) - {""}
        )
        existing["source"] = "+".join(merged)


def _flower_timeout_seconds() -> float:
    """Resolve Flower HTTP timeout from env with safe bounds."""
    raw = os.environ.get(_FLOWER_API_TIMEOUT_SECONDS_ENV, "").strip()
    if not raw:
        return _DEFAULT_FLOWER_API_TIMEOUT_SECONDS
    try:
        parsed = float(raw)
    except ValueError:
        return _DEFAULT_FLOWER_API_TIMEOUT_SECONDS
    return min(max(parsed, 0.1), 10.0)


def _flower_api_base_url() -> str | None:
    """Resolve Flower API base URL from env if configured."""
    raw = os.environ.get(_FLOWER_API_URL_ENV, "").strip()
    if not raw:
        return None
    return raw.rstrip("/")


def _fetch_flower_current_tasks() -> list[dict[str, Any]]:
    """Fetch currently active tasks from Flower API when configured."""
    base_url = _flower_api_base_url()
    if not base_url:
        return []

    url = f"{base_url}/api/tasks"
    request = urllib_request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib_request.urlopen(
            request, timeout=_flower_timeout_seconds()
        ) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (
        TimeoutError,
        OSError,
        ValueError,
        UnicodeDecodeError,
        urllib_error.HTTPError,
        urllib_error.URLError,
    ):
        return []

    if not isinstance(payload, dict):
        return []

    tasks_by_id: dict[str, dict[str, Any]] = {}
    for key, raw_entry in payload.items():
        if not isinstance(raw_entry, dict):
            continue

        entry = dict(raw_entry)
        if isinstance(key, str) and key.strip() and "uuid" not in entry:
            entry["uuid"] = key.strip()
        if not _is_helping_hands_task(entry):
            continue

        task_id = _extract_task_id(entry)
        if not task_id:
            continue

        status = _normalize_task_status(
            entry.get("state") or entry.get("status"), default="PENDING"
        )
        if status not in _CURRENT_TASK_STATES:
            continue

        kwargs_payload = _extract_task_kwargs(entry)
        backend = _coerce_optional_str(kwargs_payload.get("backend"))
        repo_path = _coerce_optional_str(kwargs_payload.get("repo_path"))
        worker = _coerce_optional_str(entry.get("worker"))
        _upsert_current_task(
            tasks_by_id,
            task_id=task_id,
            status=status,
            backend=backend,
            repo_path=repo_path,
            worker=worker,
            source="flower",
        )

    return list(tasks_by_id.values())


def _iter_worker_task_entries(payload: Any) -> list[tuple[str, dict[str, Any]]]:
    """Flatten worker->task payloads returned by Celery inspect APIs."""
    if not isinstance(payload, dict):
        return []

    entries: list[tuple[str, dict[str, Any]]] = []
    for worker, worker_tasks in payload.items():
        if not isinstance(worker, str):
            continue
        if not isinstance(worker_tasks, list):
            continue
        for task_entry in worker_tasks:
            if isinstance(task_entry, dict):
                entries.append((worker, task_entry))
    return entries


def _safe_inspect_call(inspector: Any, method_name: str) -> Any:
    """Call inspect methods safely so one failure doesn't break listing."""
    method = getattr(inspector, method_name, None)
    if not callable(method):
        return None
    try:
        return method()
    except Exception:  # pragma: no cover - defensive runtime guard
        return None


def _collect_celery_current_tasks() -> list[dict[str, Any]]:
    """Collect currently active/queued task summaries from Celery inspect."""
    try:
        inspector = celery_app.control.inspect(timeout=1.0)
    except Exception:  # pragma: no cover - defensive runtime guard
        return []
    if inspector is None:
        return []

    tasks_by_id: dict[str, dict[str, Any]] = {}
    inspect_shapes = (
        ("active", "STARTED"),
        ("reserved", "RECEIVED"),
        ("scheduled", "SCHEDULED"),
    )

    for method_name, default_status in inspect_shapes:
        payload = _safe_inspect_call(inspector, method_name)
        for worker, entry in _iter_worker_task_entries(payload):
            if not _is_helping_hands_task(entry):
                continue
            task_id = _extract_task_id(entry)
            if not task_id:
                continue
            status = _normalize_task_status(
                entry.get("state") or entry.get("status"), default=default_status
            )
            if status not in _CURRENT_TASK_STATES:
                status = default_status
            kwargs_payload = _extract_task_kwargs(entry)
            backend = _coerce_optional_str(kwargs_payload.get("backend"))
            repo_path = _coerce_optional_str(kwargs_payload.get("repo_path"))
            _upsert_current_task(
                tasks_by_id,
                task_id=task_id,
                status=status,
                backend=backend,
                repo_path=repo_path,
                worker=worker,
                source="celery",
            )

    return list(tasks_by_id.values())


def _collect_current_tasks() -> CurrentTasksResponse:
    """Collect current task UUIDs from Flower and Celery inspect."""
    tasks_by_id: dict[str, dict[str, Any]] = {}
    sources: set[str] = set()

    for task in _fetch_flower_current_tasks():
        _upsert_current_task(tasks_by_id, **task)
        sources.add("flower")

    for task in _collect_celery_current_tasks():
        _upsert_current_task(tasks_by_id, **task)
        sources.add("celery")

    sorted_tasks = sorted(
        tasks_by_id.values(),
        key=lambda item: (-_task_state_priority(str(item["status"])), item["task_id"]),
    )
    response_source = "+".join(sorted(sources)) if sources else "none"
    return CurrentTasksResponse(
        tasks=[CurrentTask(**task) for task in sorted_tasks],
        source=response_source,
    )


def _render_monitor_page(task_status: TaskStatus) -> str:
    """Render a minimal monitor page that works without client JS."""
    payload = task_status.model_dump()
    status = task_status.status
    escaped_payload = html.escape(json.dumps(payload, indent=2))

    updates: list[str] = []
    if isinstance(task_status.result, dict):
        maybe_updates = task_status.result.get("updates")
        if isinstance(maybe_updates, list):
            updates = [str(item) for item in maybe_updates]
    updates_html = "<br/>".join(html.escape(line) for line in updates)
    if not updates_html:
        updates_html = "No updates yet."

    refresh_meta = (
        '<meta http-equiv="refresh" content="2">'
        if status not in _TERMINAL_TASK_STATES
        else ""
    )

    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    {refresh_meta}
    <title>Task Monitor - {html.escape(task_status.task_id)}</title>
    <style>
      body {{
        margin: 0;
        padding: 20px;
        font-family: ui-sans-serif, -apple-system, BlinkMacSystemFont,
          "Segoe UI", sans-serif;
        background: #f7f9fa;
        color: #0f172a;
      }}
      .wrap {{
        max-width: 980px;
        margin: 0 auto;
        display: grid;
        gap: 12px;
      }}
      .panel {{
        background: #fff;
        border: 1px solid #d8e0e3;
        border-radius: 10px;
        padding: 14px;
      }}
      .meta {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 10px;
      }}
      .meta-cell {{
        width: 100%;
        height: 72px;
        box-sizing: border-box;
        padding: 10px 12px;
        border: 1px solid #d8e0e3;
        border-radius: 8px;
        background: #f8fbfc;
        display: flex;
        align-items: center;
        overflow: auto;
      }}
      .status {{
        font-weight: 700;
      }}
      .content-cell {{
        width: 100%;
        height: 280px;
        box-sizing: border-box;
        border: 1px solid #d8e0e3;
        border-radius: 8px;
        padding: 10px;
        overflow: auto;
        background: #fff;
      }}
      pre {{
        margin: 0;
        padding: 0;
        border-radius: 8px;
        background: transparent;
        color: #0f172a;
        min-height: 100%;
      }}
      .updates {{
        white-space: pre-wrap;
        line-height: 1.45;
      }}
      .actions {{
        display: flex;
        gap: 10px;
        flex-wrap: wrap;
      }}
      a {{
        color: #0f766e;
        text-decoration: none;
      }}
      @media (max-width: 720px) {{
        .meta {{ grid-template-columns: 1fr; }}
      }}
    </style>
  </head>
  <body>
    <div class="wrap">
      <section class="panel">
        <div class="meta">
          <div class="meta-cell">
            <strong>Task:</strong>&nbsp;{html.escape(task_status.task_id)}
          </div>
          <div class="meta-cell">
            <strong>Status:</strong>
            &nbsp;<span class="status">{html.escape(status)}</span>
          </div>
        </div>
        <div class="actions">
          <a href="/">Back to runner</a>
          <a href="/tasks/{html.escape(task_status.task_id)}">Raw JSON</a>
        </div>
      </section>
      <section class="panel">
        <h3>Updates</h3>
        <div class="content-cell">
          <div class="updates">{updates_html}</div>
        </div>
      </section>
      <section class="panel">
        <h3>Payload</h3>
        <div class="content-cell">
          <pre>{escaped_payload}</pre>
        </div>
      </section>
    </div>
  </body>
</html>
"""


@app.post("/build", response_model=BuildResponse)
def enqueue_build(req: BuildRequest) -> BuildResponse:
    """Enqueue a hand task and return the task ID.

    Supports E2E and iterative backends (`basic-langgraph`, `basic-atomic`,
    `basic-agent`) plus CLI-driven backends (`codexcli`, `claudecodecli`,
    `goose`, `geminicli`) using CLI-equivalent backend options.
    """
    return _enqueue_build_task(req)


@app.post("/build/form")
def enqueue_build_form(
    repo_path: str = Form(...),
    prompt: str = Form(...),
    backend: str = Form("codexcli"),
    model: str | None = Form(None),
    max_iterations: int = Form(6),
    no_pr: bool = Form(False),
    enable_execution: bool = Form(False),
    enable_web: bool = Form(False),
    use_native_cli_auth: bool = Form(False),
    pr_number: int | None = Form(None),
) -> RedirectResponse:
    """Fallback form endpoint so UI submits still enqueue without JS."""
    try:
        validated_backend = _parse_backend(backend)
    except ValueError as exc:
        query: dict[str, str] = {
            "repo_path": repo_path,
            "prompt": prompt,
            "backend": backend,
            "max_iterations": str(max_iterations),
            "error": str(exc),
        }
        if model:
            query["model"] = model
        if no_pr:
            query["no_pr"] = "1"
        if enable_execution:
            query["enable_execution"] = "1"
        if enable_web:
            query["enable_web"] = "1"
        if use_native_cli_auth:
            query["use_native_cli_auth"] = "1"
        if pr_number is not None:
            query["pr_number"] = str(pr_number)
        return RedirectResponse(url=f"/?{urlencode(query)}", status_code=303)

    try:
        req = BuildRequest(
            repo_path=repo_path,
            prompt=prompt,
            backend=validated_backend,
            model=model,
            max_iterations=max_iterations,
            no_pr=no_pr,
            enable_execution=enable_execution,
            enable_web=enable_web,
            use_native_cli_auth=use_native_cli_auth,
            pr_number=pr_number,
        )
    except ValidationError as exc:
        error_msg = "Invalid form submission."
        errors = exc.errors()
        if errors:
            first_error = errors[0]
            if isinstance(first_error, dict):
                maybe_msg = first_error.get("msg")
                if isinstance(maybe_msg, str):
                    error_msg = maybe_msg

        query: dict[str, str] = {
            "repo_path": repo_path,
            "prompt": prompt,
            "backend": backend,
            "max_iterations": str(max_iterations),
            "error": error_msg,
        }
        if model:
            query["model"] = model
        if no_pr:
            query["no_pr"] = "1"
        if enable_execution:
            query["enable_execution"] = "1"
        if enable_web:
            query["enable_web"] = "1"
        if use_native_cli_auth:
            query["use_native_cli_auth"] = "1"
        if pr_number is not None:
            query["pr_number"] = str(pr_number)
        return RedirectResponse(url=f"/?{urlencode(query)}", status_code=303)

    response = _enqueue_build_task(req)
    query = {
        "repo_path": req.repo_path,
        "prompt": req.prompt,
        "backend": req.backend,
        "max_iterations": str(req.max_iterations),
        "task_id": response.task_id,
        "status": response.status,
    }
    if req.model:
        query["model"] = req.model
    if req.no_pr:
        query["no_pr"] = "1"
    if req.enable_execution:
        query["enable_execution"] = "1"
    if req.enable_web:
        query["enable_web"] = "1"
    if req.use_native_cli_auth:
        query["use_native_cli_auth"] = "1"
    if req.pr_number is not None:
        query["pr_number"] = str(req.pr_number)
    return RedirectResponse(url=f"/monitor/{response.task_id}", status_code=303)


@app.get("/monitor/{task_id}", response_class=HTMLResponse)
def monitor(task_id: str) -> HTMLResponse:
    """No-JS monitor page with auto-refresh for task status/updates."""
    task_status = _build_task_status(task_id)
    return HTMLResponse(_render_monitor_page(task_status))


@app.get("/tasks/current", response_model=CurrentTasksResponse)
def get_current_tasks() -> CurrentTasksResponse:
    """List currently active/queued task UUIDs discovered by Flower/Celery."""
    return _collect_current_tasks()


@app.get("/tasks/{task_id}", response_model=TaskStatus)
def get_task(task_id: str) -> TaskStatus:
    """Check the status of an enqueued task."""
    return _build_task_status(task_id)
