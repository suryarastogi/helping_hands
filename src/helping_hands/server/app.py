"""FastAPI application for app mode.

Exposes an HTTP API that enqueues repo-building jobs via Celery.
"""

from __future__ import annotations

import html
import json
from typing import Any, Literal
from urllib.parse import urlencode

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, ValidationError

from helping_hands.server.celery_app import build_feature
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
    ] = "e2e"
    model: str | None = None
    max_iterations: int = 6
    no_pr: bool = False
    pr_number: int | None = None


BackendName = Literal[
    "e2e",
    "basic-langgraph",
    "basic-atomic",
    "basic-agent",
    "codexcli",
    "claudecodecli",
    "goose",
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


_TERMINAL_TASK_STATES = {"SUCCESS", "FAILURE", "REVOKED"}
_BACKEND_LOOKUP: dict[str, BackendName] = {
    "e2e": "e2e",
    "basic-langgraph": "basic-langgraph",
    "basic-atomic": "basic-atomic",
    "basic-agent": "basic-agent",
    "codexcli": "codexcli",
    "claudecodecli": "claudecodecli",
    "goose": "goose",
}


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
Update README.md</textarea>
          </div>
          <div class="row">
            <div>
              <label for="backend">Backend</label>
              <select id="backend" name="backend">
                <option value="e2e" selected>e2e</option>
                <option value="basic-langgraph">basic-langgraph</option>
                <option value="basic-atomic">basic-atomic</option>
                <option value="basic-agent">basic-agent</option>
                <option value="codexcli">codexcli</option>
                <option value="claudecodecli">claudecodecli</option>
                <option value="goose">goose</option>
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
        const payload = {
          repo_path: repoPath,
          prompt,
          backend,
          max_iterations: maxIterationsRaw ? Number(maxIterationsRaw) : 6,
          no_pr: noPr,
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
    return HTMLResponse(_UI_HTML)


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
    `basic-agent`) plus `codexcli`/`claudecodecli`/`goose`, using CLI-equivalent
    backend options.
    """
    return _enqueue_build_task(req)


@app.post("/build/form")
def enqueue_build_form(
    repo_path: str = Form(...),
    prompt: str = Form(...),
    backend: str = Form("e2e"),
    model: str | None = Form(None),
    max_iterations: int = Form(6),
    no_pr: bool = Form(False),
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
    if req.pr_number is not None:
        query["pr_number"] = str(req.pr_number)
    return RedirectResponse(url=f"/monitor/{response.task_id}", status_code=303)


@app.get("/monitor/{task_id}", response_class=HTMLResponse)
def monitor(task_id: str) -> HTMLResponse:
    """No-JS monitor page with auto-refresh for task status/updates."""
    task_status = _build_task_status(task_id)
    return HTMLResponse(_render_monitor_page(task_status))


@app.get("/tasks/{task_id}", response_model=TaskStatus)
def get_task(task_id: str) -> TaskStatus:
    """Check the status of an enqueued task."""
    return _build_task_status(task_id)
