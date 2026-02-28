"""FastAPI application for app mode.

Exposes an HTTP API that enqueues repo-building jobs via Celery.
"""

from __future__ import annotations

import ast
import html
import json
import os
from pathlib import Path
from typing import Any, Literal
from urllib import error as urllib_error
from urllib import request as urllib_request
from urllib.parse import urlencode

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from pydantic import BaseModel, Field, ValidationError, field_validator

from helping_hands.lib.default_prompts import DEFAULT_SMOKE_TEST_PROMPT
from helping_hands.lib.meta import skills as meta_skills
from helping_hands.server.celery_app import build_feature, celery_app
from helping_hands.server.task_result import normalize_task_result

# Lazy import for optional schedule dependencies
_schedule_manager = None

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
    ] = "claudecodecli"
    model: str | None = None
    max_iterations: int = 6
    no_pr: bool = False
    enable_execution: bool = False
    enable_web: bool = False
    use_native_cli_auth: bool = False
    pr_number: int | None = None
    skills: list[str] = Field(default_factory=list)

    @field_validator("skills", mode="before")
    @classmethod
    def _coerce_skills(
        cls, value: str | list[str] | tuple[str, ...] | None
    ) -> list[str]:
        normalized = meta_skills.normalize_skill_selection(value)
        return list(normalized)

    @field_validator("skills")
    @classmethod
    def _validate_skills(cls, value: list[str]) -> list[str]:
        meta_skills.validate_skill_names(tuple(value))
        return value


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


class WorkerCapacityResponse(BaseModel):
    """Response for worker capacity introspection."""

    max_workers: int = Field(ge=1)
    source: str
    workers: dict[str, int] = Field(default_factory=dict)


class ServerConfig(BaseModel):
    """Runtime configuration exposed to the frontend."""

    in_docker: bool
    native_auth_default: bool


# --- Scheduled Task Models ---


class ScheduleRequest(BaseModel):
    """Request body for creating/updating a scheduled task."""

    name: str = Field(min_length=1, max_length=100)
    cron_expression: str = Field(
        min_length=1,
        description="Cron expression (e.g., '0 0 * * *') or preset name",
    )
    repo_path: str
    prompt: str
    backend: BackendName = "claudecodecli"
    model: str | None = None
    max_iterations: int = Field(default=6, ge=1)
    pr_number: int | None = None
    no_pr: bool = False
    enable_execution: bool = False
    enable_web: bool = False
    use_native_cli_auth: bool = False
    skills: list[str] = Field(default_factory=list)
    enabled: bool = True

    @field_validator("skills", mode="before")
    @classmethod
    def _coerce_skills(
        cls, value: str | list[str] | tuple[str, ...] | None
    ) -> list[str]:
        normalized = meta_skills.normalize_skill_selection(value)
        return list(normalized)

    @field_validator("skills")
    @classmethod
    def _validate_skills(cls, value: list[str]) -> list[str]:
        meta_skills.validate_skill_names(tuple(value))
        return value


class ScheduleResponse(BaseModel):
    """Response for a scheduled task."""

    schedule_id: str
    name: str
    cron_expression: str
    repo_path: str
    prompt: str
    backend: str
    model: str | None = None
    max_iterations: int = 6
    pr_number: int | None = None
    no_pr: bool = False
    enable_execution: bool = False
    enable_web: bool = False
    use_native_cli_auth: bool = False
    skills: list[str] = Field(default_factory=list)
    enabled: bool = True
    created_at: str
    last_run_at: str | None = None
    last_run_task_id: str | None = None
    run_count: int = 0
    next_run_at: str | None = None


class ScheduleListResponse(BaseModel):
    """Response for listing scheduled tasks."""

    schedules: list[ScheduleResponse]
    total: int


class ScheduleTriggerResponse(BaseModel):
    """Response for manually triggering a scheduled task."""

    schedule_id: str
    task_id: str
    message: str


class CronPresetsResponse(BaseModel):
    """Response for listing available cron presets."""

    presets: dict[str, str]


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
_WORKER_CAPACITY_ENV_VARS = (
    "HELPING_HANDS_MAX_WORKERS",
    "HELPING_HANDS_WORKER_CONCURRENCY",
    "CELERY_WORKER_CONCURRENCY",
    "CELERYD_CONCURRENCY",
)
_DEFAULT_WORKER_CAPACITY = 8


_UI_HTML = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>helping_hands · server ui</title>
    <style>
      :root {
        --background: #020817;
        --background-soft: #0b1220;
        --panel: #0f172a;
        --panel-elevated: #111b31;
        --foreground: #e2e8f0;
        --muted: #94a3b8;
        --border: #1f2937;
        --ring: #334155;
        --primary: #2563eb;
        --primary-hover: #1d4ed8;
        --secondary: #1e293b;
        --secondary-hover: #334155;
        --mono: ui-monospace, SFMono-Regular, Menlo, monospace;
      }
      * {
        box-sizing: border-box;
      }
      html,
      body {
        min-height: 100%;
      }
      body {
        margin: 0;
        min-height: 100vh;
        font-family: "Space Grotesk", "Segoe UI", sans-serif;
        color: var(--foreground);
        background:
          radial-gradient(circle at 10% -10%, #172554 0%, transparent 40%),
          radial-gradient(circle at 110% 0%, #1e1b4b 0%, transparent 42%),
          linear-gradient(180deg, var(--background-soft) 0%, var(--background) 100%);
      }
      .page {
        max-width: 1280px;
        min-height: 100vh;
        margin: 0 auto;
        padding: 28px 20px 36px;
        display: grid;
        gap: 14px;
        grid-template-columns: 300px minmax(0, 1fr);
        align-items: start;
      }
      .main-column {
        display: grid;
        gap: 14px;
      }
      .card {
        background: linear-gradient(
          180deg,
          var(--panel-elevated) 0%,
          var(--panel) 100%
        );
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 16px;
        box-shadow: 0 20px 40px rgba(2, 8, 23, 0.45);
      }
      .task-list-card {
        position: sticky;
        top: 14px;
      }
      .new-submission-button {
        width: 100%;
        margin-bottom: 10px;
      }
      .new-submission-button.active {
        background: var(--primary-hover);
      }
      .task-list-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 10px;
        margin-bottom: 8px;
      }
      .task-list-header h2 {
        margin: 0;
        font-size: 1rem;
      }
      .text-button {
        background: transparent;
        border: 0;
        color: var(--muted);
        font-weight: 600;
        padding: 0;
        cursor: pointer;
      }
      .text-button:hover {
        color: var(--foreground);
      }
      .text-button:disabled {
        opacity: 0.45;
        cursor: not-allowed;
      }
      .empty-list {
        margin: 8px 0 0;
        color: var(--muted);
        font-size: 0.92rem;
      }
      .task-list {
        list-style: none;
        margin: 0;
        padding: 0;
        display: grid;
        gap: 8px;
        max-height: calc(100vh - 140px);
        overflow: auto;
      }
      .task-row {
        width: 100%;
        text-align: left;
        display: grid;
        gap: 6px;
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 9px;
        background: #0b1326;
        color: var(--foreground);
        cursor: pointer;
      }
      .task-row:hover {
        border-color: var(--ring);
        background: #101a31;
      }
      .task-row.active {
        border-color: #3b82f6;
        background: #10203d;
      }
      .task-row-top {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 8px;
      }
      .task-row code {
        font-family: var(--mono);
        font-size: 0.76rem;
        color: #93c5fd;
      }
      .task-row-meta {
        font-size: 0.74rem;
        color: var(--muted);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
      .status-pill {
        font-size: 0.68rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.03em;
        border-radius: 999px;
        padding: 3px 7px;
        border: 1px solid transparent;
      }
      .status-pill.ok {
        color: #86efac;
        background: #052e16;
        border-color: rgba(34, 197, 94, 0.45);
      }
      .status-pill.fail {
        color: #fca5a5;
        background: #450a0a;
        border-color: rgba(239, 68, 68, 0.5);
      }
      .status-pill.run {
        color: #67e8f9;
        background: #083344;
        border-color: rgba(6, 182, 212, 0.5);
      }
      .status-pill.idle {
        color: #cbd5e1;
        background: #0f172a;
        border-color: #334155;
      }
      .header h1 {
        margin: 0;
        font-size: 1.4rem;
        letter-spacing: -0.015em;
      }
      .header p {
        margin: 6px 0 0;
        color: var(--muted);
      }
      .form-grid {
        display: grid;
        gap: 10px;
        margin-top: 12px;
      }
      .advanced-settings {
        border: 1px solid var(--border);
        border-radius: 10px;
        background: #0b1326;
        overflow: hidden;
      }
      .advanced-settings > summary {
        cursor: pointer;
        padding: 10px 12px;
        font-size: 0.9rem;
        font-weight: 600;
        color: var(--foreground);
      }
      .advanced-settings[open] > summary {
        background: #101a31;
        border-bottom: 1px solid var(--border);
      }
      .advanced-settings-body {
        display: grid;
        gap: 10px;
        padding: 12px;
      }
      label {
        display: grid;
        gap: 6px;
        font-size: 0.93rem;
        color: var(--muted);
      }
      input,
      textarea,
      select,
      button {
        font: inherit;
      }
      input,
      textarea,
      select {
        width: 100%;
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 10px;
        color: var(--foreground);
        background: #0a1324;
      }
      input:focus,
      textarea:focus,
      select:focus {
        outline: 2px solid rgba(59, 130, 246, 0.45);
        outline-offset: 0;
        border-color: #3b82f6;
      }
      input[type="checkbox"] {
        width: auto;
        accent-color: var(--primary);
      }
      textarea {
        resize: vertical;
      }
      .row {
        display: grid;
        gap: 10px;
      }
      .two-col {
        grid-template-columns: 1fr 1fr;
      }
      .check-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }
      .check-row {
        display: flex;
        align-items: center;
        gap: 8px;
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 9px 10px;
        background: #0b1326;
        color: var(--foreground);
      }
      .actions {
        display: flex;
        flex-wrap: wrap;
        gap: 9px;
      }
      button {
        border: 1px solid transparent;
        border-radius: 10px;
        padding: 10px 14px;
        background: var(--primary);
        color: #eff6ff;
        cursor: pointer;
        font-weight: 600;
      }
      button:hover {
        background: var(--primary-hover);
      }
      button.secondary {
        background: var(--secondary);
        border-color: var(--border);
        color: var(--foreground);
      }
      button.secondary:hover {
        background: var(--secondary-hover);
      }
      .meta-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 10px;
        margin-top: 10px;
      }
      .meta-item {
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 10px;
        background: #0b1326;
      }
      .meta-label {
        display: block;
        font-size: 0.82rem;
        color: var(--muted);
        margin-bottom: 4px;
      }
      .meta-item strong {
        display: block;
        font-family: var(--mono);
        font-size: 0.84rem;
        line-height: 1.35;
        overflow-wrap: anywhere;
      }
      .output-pane {
        margin-top: 12px;
      }
      .pane-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 10px;
        margin-bottom: 8px;
      }
      .pane-header h2 {
        margin: 0;
        font-size: 1rem;
      }
      .pane-tabs {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        border: 1px solid var(--border);
        border-radius: 8px;
        background: #0a1324;
        padding: 2px;
      }
      .tab-btn {
        border: 0;
        border-radius: 6px;
        padding: 5px 10px;
        background: transparent;
        color: var(--muted);
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.01em;
        cursor: pointer;
      }
      .tab-btn:hover {
        background: #16233f;
        color: var(--foreground);
      }
      .tab-btn.active {
        background: var(--secondary);
        color: var(--foreground);
      }
      .output-pane pre {
        margin: 0;
        min-height: 280px;
        max-height: min(68vh, 860px);
        overflow: auto;
        padding: 12px;
        border-radius: 10px;
        border: 1px solid var(--border);
        background: #020817;
        color: #cbd5e1;
        font-family: var(--mono);
        font-size: 0.8rem;
        line-height: 1.45;
        white-space: pre-wrap;
        word-break: break-word;
      }
      code {
        font-family: var(--mono);
        font-size: 0.84rem;
      }
      .is-hidden {
        display: none;
      }
      @media (max-width: 1020px) {
        .page {
          grid-template-columns: 1fr;
        }
        .task-list-card {
          position: static;
        }
        .task-list {
          max-height: 280px;
        }
      }
      @media (max-width: 920px) {
        .two-col,
        .check-grid,
        .meta-grid {
          grid-template-columns: 1fr;
        }
        .pane-header {
          align-items: flex-start;
          flex-direction: column;
        }
      }
      .server-ui-badge {
        font-size: 0.6em;
        font-weight: 600;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        color: #93c5fd;
        background: rgba(37, 99, 235, 0.15);
        border: 1px solid rgba(59, 130, 246, 0.3);
        border-radius: 6px;
        padding: 2px 7px;
        vertical-align: middle;
      }
      .status-blinker {
        width: 10px;
        height: 10px;
        border-radius: 999px;
        flex-shrink: 0;
        display: inline-block;
        cursor: help;
      }
      .status-blinker.pulse {
        animation: blinker-pulse 1.4s ease-in-out infinite;
      }
      @keyframes blinker-pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.35; }
      }
      .status-with-blinker {
        display: flex;
        align-items: center;
        gap: 6px;
      }
      .toast-container {
        position: fixed;
        bottom: 16px;
        right: 16px;
        display: flex;
        flex-direction: column;
        gap: 8px;
        z-index: 200;
        pointer-events: none;
      }
      .toast {
        display: flex;
        align-items: center;
        gap: 10px;
        background: #111b31;
        border: 1px solid #1f2937;
        border-left: 3px solid #94a3b8;
        border-radius: 8px;
        padding: 10px 14px;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.8rem;
        color: #e2e8f0;
        backdrop-filter: blur(8px);
        pointer-events: auto;
        animation: toast-slide-in 0.3s ease-out;
        min-width: 240px;
        max-width: 380px;
      }
      .toast--ok { border-left-color: #22c55e; }
      .toast--fail { border-left-color: #ef4444; }
      .toast-text {
        flex: 1;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      .toast-close {
        background: none;
        border: none;
        color: #94a3b8;
        cursor: pointer;
        font-size: 1.1rem;
        padding: 0 2px;
        line-height: 1;
      }
      .toast-close:hover { color: #e2e8f0; }
      @keyframes toast-slide-in {
        from { opacity: 0; transform: translateX(100%); }
        to { opacity: 1; transform: translateX(0); }
      }
    </style>
  </head>
  <body>
    <main class="page">
      <aside class="card task-list-card">
        <button
          type="button"
          id="new-submission-btn"
          class="new-submission-button active"
        >
          New submission
        </button>
        <button
          type="button"
          id="schedules-btn"
          class="new-submission-button"
          style="margin-top: 8px;"
        >
          Scheduled tasks
        </button>
        <div class="task-list-header">
          <h2>Submitted tasks</h2>
          <button type="button" id="clear-history-btn" class="text-button">
            Clear
          </button>
        </div>
        <p id="empty-list" class="empty-list">No tasks submitted yet.</p>
        <ul id="task-list" class="task-list"></ul>
      </aside>

      <div class="main-column">
        <section id="submission-view" class="card">
          <header class="header">
            <h1>helping_hands <span class="server-ui-badge">server&nbsp;ui</span></h1>
            <p>
              Submit runs to <code>/build</code> and track progress from
              <code>/tasks/{task_id}</code>.
            </p>
          </header>

          <form id="run-form" method="post" action="/build/form" class="form-grid">
            <label for="repo_path">
              Repo path (owner/repo)
              <input
                id="repo_path"
                name="repo_path"
                value="suryarastogi/helping_hands"
                required
              />
            </label>

            <label for="prompt">
              Prompt
              <textarea id="prompt" name="prompt" required rows="6">
__DEFAULT_SMOKE_TEST_PROMPT__</textarea>
            </label>

            <details class="advanced-settings">
              <summary>Advanced settings</summary>
              <div class="advanced-settings-body">
                <div class="row two-col">
                  <label for="backend">
                    Backend
                    <select id="backend" name="backend">
                      <option value="e2e">Smoke Test (internal)</option>
                      <option value="basic-langgraph">basic-langgraph</option>
                      <option value="basic-atomic">basic-atomic</option>
                      <option value="basic-agent">basic-agent</option>
                      <option value="codexcli" selected>codexcli</option>
                      <option value="claudecodecli">claudecodecli</option>
                      <option value="goose">goose</option>
                      <option value="geminicli">geminicli</option>
                    </select>
                  </label>

                  <label for="model">
                    Model (optional)
                    <input id="model" name="model" placeholder="claude-opus-4-6" />
                  </label>
                </div>

                <div class="row two-col">
                  <label for="max_iterations">
                    Max iterations
                    <input
                      id="max_iterations"
                      name="max_iterations"
                      type="number"
                      min="1"
                      value="6"
                    />
                  </label>

                  <label for="pr_number">
                    PR number (optional)
                    <input id="pr_number" name="pr_number" type="number" min="1" />
                  </label>
                </div>

                <label for="skills">
                  Skills (comma-separated, optional)
                  <input
                    id="skills"
                    name="skills"
                    placeholder="execution,web,prd,ralph"
                  />
                </label>

                <div class="row check-grid">
                  <label class="check-row" for="no_pr">
                    <input id="no_pr" name="no_pr" type="checkbox" />
                    Disable final PR push/create
                  </label>

                  <label class="check-row" for="enable_execution">
                    <input
                      id="enable_execution"
                      name="enable_execution"
                      type="checkbox"
                    />
                    Enable execution tools
                  </label>

                  <label class="check-row" for="enable_web">
                    <input id="enable_web" name="enable_web" type="checkbox" />
                    Enable web tools
                  </label>

                  <label class="check-row" for="use_native_cli_auth">
                    <input
                      id="use_native_cli_auth"
                      name="use_native_cli_auth"
                      type="checkbox"
                    />
                    Use native CLI auth (Codex/Claude)
                  </label>
                </div>
              </div>
            </details>

            <div class="actions">
              <button type="submit">Submit run</button>
            </div>
          </form>
        </section>

        <section id="monitor-view" class="card is-hidden">
          <div class="actions">
            <button id="stop-btn" type="button" class="secondary">
              Stop polling
            </button>
          </div>
          <div class="meta-grid">
            <div class="meta-item">
              <span class="meta-label">Status</span>
              <strong class="status-with-blinker">
                <span id="status-blinker" class="status-blinker"
                  style="background-color:#6b7280" title="idle"></span>
                <span id="status">idle</span>
              </strong>
            </div>
            <div class="meta-item">
              <span class="meta-label">Task</span>
              <strong id="task_label">-</strong>
            </div>
            <div class="meta-item">
              <span class="meta-label">Polling</span>
              <strong id="polling_label">off</strong>
            </div>
          </div>

          <article class="output-pane">
            <div class="pane-header">
              <h2>Output</h2>
              <div class="pane-tabs" role="tablist" aria-label="Output mode">
                <button
                  type="button"
                  class="tab-btn active"
                  data-output-tab="updates"
                >
                  Updates
                </button>
                <button type="button" class="tab-btn" data-output-tab="raw">
                  Raw
                </button>
                <button type="button" class="tab-btn" data-output-tab="payload">
                  Payload
                </button>
              </div>
            </div>
            <pre id="output_text">No updates yet.</pre>
          </article>
        </section>

        <section id="schedules-view" class="card is-hidden">
          <header class="header">
            <h1>Scheduled tasks <span class="server-ui-badge">cron</span></h1>
            <p>Create and monitor recurring builds with cron expressions.</p>
          </header>

          <div class="actions" style="margin-bottom: 16px;">
            <button type="button" id="new-schedule-btn">New schedule</button>
            <button type="button" id="refresh-schedules-btn" class="secondary">
              Refresh
            </button>
          </div>

          <div id="schedules-list">
            <p class="empty-list">No scheduled tasks yet.</p>
          </div>

          <div id="schedule-form-container" class="is-hidden" style="margin-top: 16px; padding-top: 16px; border-top: 1px solid var(--border);">
            <h2 id="schedule-form-title" style="margin-bottom: 12px;">New schedule</h2>
            <form id="schedule-form" class="form-grid">
              <input type="hidden" id="schedule_id" name="schedule_id" />
              <label for="schedule_name">
                Name
                <input id="schedule_name" name="name" required placeholder="e.g. Daily docs update" />
              </label>

              <div class="row two-col">
                <label for="schedule_cron">
                  Cron expression
                  <input id="schedule_cron" name="cron_expression" required placeholder="0 0 * * * (midnight)" />
                </label>
                <label for="schedule_preset">
                  Or preset
                  <select id="schedule_preset">
                    <option value="">Custom</option>
                    <option value="every_minute">Every minute</option>
                    <option value="every_5_minutes">Every 5 minutes</option>
                    <option value="every_15_minutes">Every 15 minutes</option>
                    <option value="hourly">Hourly</option>
                    <option value="daily">Daily (midnight)</option>
                    <option value="weekly">Weekly (Sunday midnight)</option>
                    <option value="monthly">Monthly (1st midnight)</option>
                    <option value="weekdays">Weekdays (9am)</option>
                  </select>
                </label>
              </div>

              <label for="schedule_repo">
                Repo path (owner/repo)
                <input id="schedule_repo" name="repo_path" required placeholder="owner/repo" />
              </label>

              <label for="schedule_prompt">
                Prompt
                <textarea id="schedule_prompt" name="prompt" required rows="4" placeholder="Update documentation..."></textarea>
              </label>

              <details class="advanced-settings">
                <summary>Advanced settings</summary>
                <div class="advanced-settings-body">
                  <div class="row two-col">
                    <label for="schedule_backend">
                      Backend
                      <select id="schedule_backend" name="backend">
                        <option value="claudecodecli" selected>claudecodecli</option>
                        <option value="codexcli">codexcli</option>
                        <option value="basic-langgraph">basic-langgraph</option>
                        <option value="basic-atomic">basic-atomic</option>
                        <option value="goose">goose</option>
                        <option value="geminicli">geminicli</option>
                      </select>
                    </label>
                    <label for="schedule_model">
                      Model (optional)
                      <input id="schedule_model" name="model" placeholder="claude-opus-4-6" />
                    </label>
                  </div>
                  <label for="schedule_pr_number">
                    PR number (optional)
                    <input id="schedule_pr_number" name="pr_number" type="number" min="1" />
                  </label>
                  <div class="row check-grid">
                    <label class="check-row" for="schedule_no_pr">
                      <input id="schedule_no_pr" name="no_pr" type="checkbox" />
                      Disable final PR
                    </label>
                    <label class="check-row" for="schedule_enabled">
                      <input id="schedule_enabled" name="enabled" type="checkbox" checked />
                      Enabled
                    </label>
                  </div>
                </div>
              </details>

              <div class="actions">
                <button type="submit" id="schedule-submit-btn">Create schedule</button>
                <button type="button" id="schedule-cancel-btn" class="secondary">Cancel</button>
              </div>
            </form>
          </div>
        </section>
      </div>
    </main>

    <script>
      const form = document.getElementById("run-form");
      const submissionView = document.getElementById("submission-view");
      const monitorView = document.getElementById("monitor-view");
      const newSubmissionBtn = document.getElementById("new-submission-btn");
      const clearHistoryBtn = document.getElementById("clear-history-btn");
      const taskListEl = document.getElementById("task-list");
      const emptyListEl = document.getElementById("empty-list");
      const stopBtn = document.getElementById("stop-btn");
      const statusEl = document.getElementById("status");
      const taskLabelEl = document.getElementById("task_label");
      const pollingLabelEl = document.getElementById("polling_label");
      const outputTextEl = document.getElementById("output_text");
      const statusBlinkerEl = document.getElementById("status-blinker");
      const tabButtons = Array.from(document.querySelectorAll("[data-output-tab]"));
      const historyStorageKey = "helping_hands_task_history_v1";
      const terminalStatuses = new Set(["SUCCESS", "FAILURE", "REVOKED"]);

      let taskId = null;
      let status = "idle";
      let payloadData = null;
      let updates = [];
      let outputTab = "updates";
      let isPolling = false;
      let pollHandle = null;
      let discoveryHandle = null;
      let taskHistory = loadTaskHistory();

      // Schedule elements
      const schedulesBtn = document.getElementById("schedules-btn");
      const schedulesView = document.getElementById("schedules-view");
      const schedulesList = document.getElementById("schedules-list");
      const newScheduleBtn = document.getElementById("new-schedule-btn");
      const refreshSchedulesBtn = document.getElementById("refresh-schedules-btn");
      const scheduleFormContainer = document.getElementById("schedule-form-container");
      const scheduleForm = document.getElementById("schedule-form");
      const scheduleFormTitle = document.getElementById("schedule-form-title");
      const scheduleSubmitBtn = document.getElementById("schedule-submit-btn");
      const scheduleCancelBtn = document.getElementById("schedule-cancel-btn");
      const schedulePreset = document.getElementById("schedule_preset");
      const scheduleCron = document.getElementById("schedule_cron");

      const cronPresets = {
        "every_minute": "* * * * *",
        "every_5_minutes": "*/5 * * * *",
        "every_15_minutes": "*/15 * * * *",
        "hourly": "0 * * * *",
        "daily": "0 0 * * *",
        "weekly": "0 0 * * 0",
        "monthly": "0 0 1 * *",
        "weekdays": "0 9 * * 1-5"
      };

      function setView(nextView) {
        const isSubmission = nextView === "submission";
        const isSchedules = nextView === "schedules";
        submissionView.classList.toggle("is-hidden", !isSubmission);
        monitorView.classList.toggle("is-hidden", isSubmission || isSchedules);
        schedulesView.classList.toggle("is-hidden", !isSchedules);
        newSubmissionBtn.classList.toggle("active", isSubmission);
        schedulesBtn.classList.toggle("active", isSchedules);
      }

      function setStatus(value) {
        status = value;
        statusEl.textContent = value;
        const tone = statusTone(value);
        statusBlinkerEl.style.backgroundColor = statusBlinkerColor(tone);
        statusBlinkerEl.title = value;
        statusBlinkerEl.classList.toggle("pulse", tone === "run");
      }

      function setTaskId(value) {
        taskId = value || null;
        taskLabelEl.textContent = taskId || "-";
      }

      function setPolling(value) {
        isPolling = value;
        pollingLabelEl.textContent = value ? "active" : "off";
      }

      function setOutput(value) {
        payloadData = value;
        renderOutput();
      }

      function setUpdates(value) {
        updates = Array.isArray(value) ? value.map((item) => String(item)) : [];
        renderOutput();
      }

      function shortTaskId(value) {
        if (!value || value.length <= 26) {
          return value || "-";
        }
        return `${value.slice(0, 10)}...${value.slice(-8)}`;
      }

      let toastCounter = 0;
      const toastContainerEl = document.getElementById("toast-container");

      function showToast(tid, tStatus) {
        const tone = statusTone(tStatus);
        const el = document.createElement("div");
        el.className = "toast toast--" + tone;
        el.innerHTML =
          '<span class="toast-text">Task ' + shortTaskId(tid) + " \u2014 " + tStatus + "</span>" +
          '<button class="toast-close" aria-label="Dismiss">\u00d7</button>';
        el.querySelector(".toast-close").onclick = function () { el.remove(); };
        toastContainerEl.appendChild(el);
        setTimeout(function () { el.remove(); }, 5000);
      }

      var _swReg = null;
      if ("serviceWorker" in navigator) {
        navigator.serviceWorker.register("/notif-sw.js").then(function(reg) {
          _swReg = reg;
        }).catch(function() {});
      }

      function sendBrowserNotification(tid, tStatus) {
        if (typeof Notification === "undefined" || Notification.permission !== "granted") return;
        var tone = tStatus.toUpperCase() === "SUCCESS" ? "completed successfully" : "failed";
        var body = "Task " + shortTaskId(tid) + " " + tone;
        if (_swReg) {
          _swReg.showNotification("Helping Hands", { body: body, tag: tid });
        } else {
          try { new Notification("Helping Hands", { body: body }); } catch(e) {}
        }
      }

      if (typeof Notification !== "undefined" && Notification.permission === "default") {
        Notification.requestPermission();
      }

      function statusTone(value) {
        const normalized = String(value || "").trim().toUpperCase();
        if (normalized === "SUCCESS") {
          return "ok";
        }
        if (
          normalized === "FAILURE" ||
          normalized === "REVOKED" ||
          normalized === "POLL_ERROR"
        ) {
          return "fail";
        }
        if (
          [
            "QUEUED",
            "PENDING",
            "STARTED",
            "RUNNING",
            "RECEIVED",
            "RETRY",
            "PROGRESS",
            "SCHEDULED",
            "RESERVED",
            "SENT",
            "MONITORING",
            "SUBMITTING",
          ].includes(normalized)
        ) {
          return "run";
        }
        return "idle";
      }

      function statusBlinkerColor(tone) {
        if (tone === "ok") return "#22c55e";
        if (tone === "fail") return "#ef4444";
        if (tone === "run") return "#eab308";
        return "#6b7280";
      }

      function parseOptimisticUpdates(rawUpdates) {
        const lines = [];
        const source = Array.isArray(rawUpdates) ? rawUpdates : [];
        for (const entry of source) {
          const chunks = String(entry).split(/\r?\n/);
          for (const chunk of chunks) {
            const trimmed = chunk.trim();
            if (!trimmed) {
              continue;
            }
            if (trimmed.includes(".zshenv:.:1: no such file or directory")) {
              continue;
            }
            lines.push(trimmed);
          }
        }
        return lines;
      }

      function renderOutput() {
        let text = "No updates yet.";
        if (outputTab === "payload") {
          text = payloadData ? JSON.stringify(payloadData, null, 2) : "{}";
        } else if (outputTab === "raw") {
          text = updates.length > 0 ? updates.join("\n") : "No raw output yet.";
        } else {
          const parsed = parseOptimisticUpdates(updates);
          text = parsed.length > 0 ? parsed.join("\n") : "No updates yet.";
        }
        outputTextEl.textContent = text;
      }

      function setOutputTab(nextTab) {
        outputTab = nextTab;
        for (const button of tabButtons) {
          const active = button.getAttribute("data-output-tab") === nextTab;
          button.classList.toggle("active", active);
        }
        renderOutput();
      }

      function loadTaskHistory() {
        try {
          const raw = window.localStorage.getItem(historyStorageKey);
          if (!raw) {
            return [];
          }
          const parsed = JSON.parse(raw);
          if (!Array.isArray(parsed)) {
            return [];
          }
          return parsed
            .filter(
              (item) =>
                item &&
                typeof item === "object" &&
                String(item.taskId || "").trim()
            )
            .slice(0, 60);
        } catch (_ignored) {
          return [];
        }
      }

      function persistTaskHistory() {
        try {
          window.localStorage.setItem(historyStorageKey, JSON.stringify(taskHistory));
        } catch (_ignored) {
          // Best effort only.
        }
      }

      function upsertTaskHistory(patch) {
        const normalizedId = String(patch.taskId || "").trim();
        if (!normalizedId) {
          return;
        }
        const now = Date.now();
        const idx = taskHistory.findIndex((item) => item.taskId === normalizedId);
        if (idx >= 0) {
          const existing = taskHistory[idx];
          const updated = {
            ...existing,
            status: patch.status || existing.status,
            backend: patch.backend || existing.backend,
            repoPath: patch.repoPath || existing.repoPath,
            lastUpdatedAt: now,
          };
          taskHistory = [updated].concat(
            taskHistory.filter((_, index) => index !== idx)
          );
        } else {
          taskHistory = [
            {
              taskId: normalizedId,
              status: patch.status || "queued",
              backend: patch.backend || "unknown",
              repoPath: patch.repoPath || "",
              createdAt: now,
              lastUpdatedAt: now,
            },
          ].concat(taskHistory);
        }
        taskHistory = taskHistory.slice(0, 60);
        persistTaskHistory();
        renderTaskHistory();
      }

      function renderTaskHistory() {
        taskListEl.innerHTML = "";
        if (taskHistory.length === 0) {
          emptyListEl.style.display = "block";
          clearHistoryBtn.disabled = true;
          return;
        }
        emptyListEl.style.display = "none";
        clearHistoryBtn.disabled = false;

        for (const item of taskHistory) {
          const row = document.createElement("button");
          row.type = "button";
          row.className = "task-row";
          if (!monitorView.classList.contains("is-hidden") && taskId === item.taskId) {
            row.classList.add("active");
          }

          const top = document.createElement("span");
          top.className = "task-row-top";
          const idCode = document.createElement("code");
          idCode.textContent = shortTaskId(item.taskId);
          const tone = statusTone(item.status);
          const rowBlinker = document.createElement("span");
          rowBlinker.className = `status-blinker${tone === "run" ? " pulse" : ""}`;
          rowBlinker.style.backgroundColor = statusBlinkerColor(tone);
          rowBlinker.title = item.status;
          const statusPill = document.createElement("span");
          statusPill.className = `status-pill ${tone}`;
          statusPill.textContent = item.status;
          top.appendChild(idCode);
          top.appendChild(rowBlinker);
          top.appendChild(statusPill);

          const meta = document.createElement("span");
          meta.className = "task-row-meta";
          const backend = item.backend || "unknown";
          const repoPath = item.repoPath || "manual";
          const timestamp = new Date(
            item.lastUpdatedAt || Date.now()
          ).toLocaleTimeString();
          meta.textContent = `${backend} | ${repoPath} | ${timestamp}`;

          row.appendChild(top);
          row.appendChild(meta);
          row.title = item.taskId;
          row.addEventListener("click", () => {
            selectTask(item.taskId);
          });

          const listItem = document.createElement("li");
          listItem.appendChild(row);
          taskListEl.appendChild(listItem);
        }
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
        if (Array.isArray(data && data.result && data.result.updates)) {
          setUpdates(data.result.updates);
        } else {
          setUpdates([]);
        }
        setOutput(data);
        upsertTaskHistory({
          taskId: data.task_id,
          status: data.status,
        });
        if (terminalStatuses.has(data.status)) {
          showToast(data.task_id, data.status);
          sendBrowserNotification(data.task_id, data.status);
          stopPolling();
        }
      }

      function stopPolling() {
        if (pollHandle) {
          clearInterval(pollHandle);
          pollHandle = null;
        }
        setPolling(false);
      }

      function startPolling(taskId) {
        stopPolling();
        setTaskId(taskId);
        setPolling(true);
        setView("monitor");
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

      function selectTask(selectedTaskId) {
        setStatus("monitoring");
        setOutput(null);
        setUpdates([]);
        setOutputTab("updates");
        startPolling(selectedTaskId);
        upsertTaskHistory({
          taskId: selectedTaskId,
          status: "monitoring",
        });
      }

      function clearForNewSubmission() {
        stopPolling();
        setStatus("idle");
        setTaskId(null);
        setOutput(null);
        setUpdates([]);
        setOutputTab("updates");
        setView("submission");
        renderTaskHistory();
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
        const skills = params.get("skills");
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
        if (skills) {
          document.getElementById("skills").value = skills;
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
          upsertTaskHistory({
            taskId,
            status: status || "queued",
            backend: backend || undefined,
            repoPath: repoPath || undefined,
          });
          setStatus(status || "queued");
          selectTask(taskId);
        }
      }

      async function refreshCurrentTasks() {
        try {
          const response = await fetch(`/tasks/current?_=${Date.now()}`, {
            cache: "no-store",
          });
          if (!response.ok) {
            return;
          }
          const data = await response.json();
          if (!Array.isArray(data.tasks)) {
            return;
          }
          for (const item of data.tasks) {
            const discoveredTaskId = String(
              item && item.task_id ? item.task_id : ""
            ).trim();
            if (!discoveredTaskId) {
              continue;
            }
            upsertTaskHistory({
              taskId: discoveredTaskId,
              status: String(item.status || "unknown"),
              backend: typeof item.backend === "string" ? item.backend : undefined,
              repoPath: typeof item.repo_path === "string" ? item.repo_path : undefined,
            });
          }
        } catch (_ignored) {
          // Best effort only.
        }
      }

      applyQueryDefaults();
      renderTaskHistory();
      renderOutput();

      refreshCurrentTasks();
      discoveryHandle = setInterval(() => {
        refreshCurrentTasks();
      }, 5000);

      newSubmissionBtn.addEventListener("click", () => {
        clearForNewSubmission();
      });

      clearHistoryBtn.addEventListener("click", () => {
        taskHistory = [];
        persistTaskHistory();
        renderTaskHistory();
      });

      for (const button of tabButtons) {
        button.addEventListener("click", () => {
          const nextTab = button.getAttribute("data-output-tab");
          if (!nextTab) {
            return;
          }
          setOutputTab(nextTab);
        });
      }

      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        setStatus("submitting");
        setView("monitor");
        setPolling(false);
        setTaskId(null);
        setUpdates([]);
        setOutputTab("updates");
        const repoPath = document.getElementById("repo_path").value.trim();
        const prompt = document.getElementById("prompt").value.trim();
        const backend = document.getElementById("backend").value;
        const model = document.getElementById("model").value.trim();
        const maxIterationsRaw = document.getElementById("max_iterations").value.trim();
        const prRaw = document.getElementById("pr_number").value.trim();
        const skillsRaw = document.getElementById("skills").value.trim();
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
        if (skillsRaw) {
          payload.skills = skillsRaw
            .split(",")
            .map((item) => item.trim())
            .filter((item) => item.length > 0);
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
          setTaskId(data.task_id);
          setStatus(data.status);
          setOutput(data);
          setUpdates([]);
          upsertTaskHistory({
            taskId: data.task_id,
            status: data.status,
            backend: data.backend,
            repoPath,
          });
          startPolling(data.task_id);
        } catch (err) {
          setStatus("error");
          setOutput({ error: String(err) });
          setPolling(false);
        }
      });

      stopBtn.addEventListener("click", () => {
        stopPolling();
        setStatus("stopped");
      });

      window.addEventListener("beforeunload", () => {
        stopPolling();
        if (discoveryHandle) {
          clearInterval(discoveryHandle);
          discoveryHandle = null;
        }
      });

      // Schedule management functions
      schedulesBtn.addEventListener("click", () => {
        setView("schedules");
        loadSchedules();
      });

      schedulePreset.addEventListener("change", (e) => {
        const preset = e.target.value;
        if (preset && cronPresets[preset]) {
          scheduleCron.value = cronPresets[preset];
        }
      });

      newScheduleBtn.addEventListener("click", () => {
        scheduleFormTitle.textContent = "New schedule";
        scheduleSubmitBtn.textContent = "Create schedule";
        scheduleForm.reset();
        document.getElementById("schedule_id").value = "";
        document.getElementById("schedule_enabled").checked = true;
        scheduleFormContainer.classList.remove("is-hidden");
      });

      scheduleCancelBtn.addEventListener("click", () => {
        scheduleFormContainer.classList.add("is-hidden");
        scheduleForm.reset();
      });

      refreshSchedulesBtn.addEventListener("click", loadSchedules);

      async function loadSchedules() {
        try {
          const response = await fetch("/schedules");
          if (!response.ok) throw new Error("Failed to load schedules");
          const data = await response.json();
          renderSchedules(data.schedules);
        } catch (err) {
          schedulesList.innerHTML = `<p class="empty-list" style="color:#ef4444;">Error: ${err.message}</p>`;
        }
      }

      function renderSchedules(schedules) {
        if (!schedules || schedules.length === 0) {
          schedulesList.innerHTML = '<p class="empty-list">No scheduled tasks yet.</p>';
          return;
        }
        let html = '<div style="display: flex; flex-direction: column; gap: 12px;">';
        for (const s of schedules) {
          const statusColor = s.enabled ? "#22c55e" : "#6b7280";
          const statusText = s.enabled ? "enabled" : "disabled";
          const nextRun = s.next_run_at ? new Date(s.next_run_at).toLocaleString() : "N/A";
          const lastRun = s.last_run_at ? new Date(s.last_run_at).toLocaleString() : "Never";
          html += `
            <div class="schedule-item" style="background: var(--secondary); border-radius: 8px; padding: 12px;">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <strong>${escapeHtml(s.name)}</strong>
                <span style="display: flex; align-items: center; gap: 6px;">
                  <span class="status-blinker" style="background-color: ${statusColor};"></span>
                  <span class="status-pill" style="background: ${statusColor};">${statusText}</span>
                </span>
              </div>
              <div style="font-size: 12px; color: var(--muted); display: grid; gap: 4px;">
                <div><strong>Cron:</strong> <code>${escapeHtml(s.cron_expression)}</code></div>
                <div><strong>Repo:</strong> ${escapeHtml(s.repo_path)}</div>
                <div><strong>Prompt:</strong> ${escapeHtml(s.prompt.substring(0, 80))}${s.prompt.length > 80 ? "..." : ""}</div>
                <div><strong>Next run:</strong> ${nextRun}</div>
                <div><strong>Last run:</strong> ${lastRun} (${s.run_count} runs)</div>
              </div>
              <div style="margin-top: 10px; display: flex; gap: 8px;">
                <button type="button" class="secondary" onclick="editSchedule('${s.schedule_id}')" style="font-size: 12px; padding: 4px 8px;">Edit</button>
                <button type="button" class="secondary" onclick="triggerSchedule('${s.schedule_id}')" style="font-size: 12px; padding: 4px 8px;">Run now</button>
                <button type="button" class="secondary" onclick="toggleSchedule('${s.schedule_id}', ${!s.enabled})" style="font-size: 12px; padding: 4px 8px;">${s.enabled ? "Disable" : "Enable"}</button>
                <button type="button" class="secondary" onclick="deleteSchedule('${s.schedule_id}')" style="font-size: 12px; padding: 4px 8px; color: #ef4444;">Delete</button>
              </div>
            </div>
          `;
        }
        html += '</div>';
        schedulesList.innerHTML = html;
      }

      function escapeHtml(str) {
        const div = document.createElement("div");
        div.textContent = str || "";
        return div.innerHTML;
      }

      scheduleForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const scheduleId = document.getElementById("schedule_id").value;
        const payload = {
          name: document.getElementById("schedule_name").value,
          cron_expression: document.getElementById("schedule_cron").value,
          repo_path: document.getElementById("schedule_repo").value,
          prompt: document.getElementById("schedule_prompt").value,
          backend: document.getElementById("schedule_backend").value,
          model: document.getElementById("schedule_model").value || null,
          pr_number: document.getElementById("schedule_pr_number").value ? Number(document.getElementById("schedule_pr_number").value) : null,
          no_pr: document.getElementById("schedule_no_pr").checked,
          enabled: document.getElementById("schedule_enabled").checked
        };

        try {
          const url = scheduleId ? `/schedules/${scheduleId}` : "/schedules";
          const method = scheduleId ? "PUT" : "POST";
          const response = await fetch(url, {
            method,
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
          });
          if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || "Failed to save schedule");
          }
          scheduleFormContainer.classList.add("is-hidden");
          loadSchedules();
        } catch (err) {
          alert("Error: " + err.message);
        }
      });

      window.editSchedule = async function(scheduleId) {
        try {
          const response = await fetch(`/schedules/${scheduleId}`);
          if (!response.ok) throw new Error("Schedule not found");
          const s = await response.json();

          document.getElementById("schedule_id").value = s.schedule_id;
          document.getElementById("schedule_name").value = s.name;
          document.getElementById("schedule_cron").value = s.cron_expression;
          document.getElementById("schedule_repo").value = s.repo_path;
          document.getElementById("schedule_prompt").value = s.prompt;
          document.getElementById("schedule_backend").value = s.backend;
          document.getElementById("schedule_model").value = s.model || "";
          document.getElementById("schedule_pr_number").value = s.pr_number != null ? s.pr_number : "";
          document.getElementById("schedule_no_pr").checked = s.no_pr;
          document.getElementById("schedule_enabled").checked = s.enabled;

          scheduleFormTitle.textContent = "Edit schedule";
          scheduleSubmitBtn.textContent = "Update schedule";
          scheduleFormContainer.classList.remove("is-hidden");
        } catch (err) {
          alert("Error: " + err.message);
        }
      };

      window.triggerSchedule = async function(scheduleId) {
        if (!confirm("Run this schedule now?")) return;
        try {
          const response = await fetch(`/schedules/${scheduleId}/trigger`, { method: "POST" });
          if (!response.ok) throw new Error("Failed to trigger schedule");
          const data = await response.json();
          alert(`Triggered! Task ID: ${data.task_id}`);
          loadSchedules();
        } catch (err) {
          alert("Error: " + err.message);
        }
      };

      window.toggleSchedule = async function(scheduleId, enable) {
        try {
          const action = enable ? "enable" : "disable";
          const response = await fetch(`/schedules/${scheduleId}/${action}`, { method: "POST" });
          if (!response.ok) throw new Error(`Failed to ${action} schedule`);
          loadSchedules();
        } catch (err) {
          alert("Error: " + err.message);
        }
      };

      window.deleteSchedule = async function(scheduleId) {
        if (!confirm("Delete this schedule? This cannot be undone.")) return;
        try {
          const response = await fetch(`/schedules/${scheduleId}`, { method: "DELETE" });
          if (!response.ok) throw new Error("Failed to delete schedule");
          loadSchedules();
        } catch (err) {
          alert("Error: " + err.message);
        }
      };
    </script>
    <div id="toast-container" class="toast-container"></div>
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


_NOTIF_SW_JS = """\
self.addEventListener("notificationclick", function(event) {
  event.notification.close();
  event.waitUntil(
    clients.matchAll({ type: "window" }).then(function(list) {
      for (var i = 0; i < list.length; i++) {
        if (list[i].url && "focus" in list[i]) return list[i].focus();
      }
      if (clients.openWindow) return clients.openWindow("/");
    })
  );
});
"""


@app.get("/notif-sw.js")
def notif_sw() -> Response:
    """Minimal service worker for OS notifications."""
    return Response(content=_NOTIF_SW_JS, media_type="application/javascript")


@app.get("/health")
def health() -> dict[str, str]:
    """Health check."""
    return {"status": "ok"}


class ServiceHealthResponse(BaseModel):
    """Per-service connectivity status."""

    redis: Literal["ok", "error"]
    db: Literal["ok", "error", "na"]
    workers: Literal["ok", "error"]


def _check_redis_health() -> Literal["ok", "error"]:
    try:
        import redis as redis_lib  # bundled with celery[redis]

        broker_url = celery_app.conf.broker_url or "redis://localhost:6379/0"
        r = redis_lib.Redis.from_url(
            broker_url,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        r.ping()
        return "ok"
    except Exception:
        return "error"


def _check_db_health() -> Literal["ok", "error", "na"]:
    db_url = os.environ.get("DATABASE_URL", "").strip()
    if not db_url:
        return "na"
    try:
        import psycopg2  # psycopg2-binary is a declared dependency

        conn = psycopg2.connect(db_url, connect_timeout=3)
        conn.close()
        return "ok"
    except Exception:
        return "error"


def _check_workers_health() -> Literal["ok", "error"]:
    try:
        inspector = celery_app.control.inspect(timeout=2.0)
        ping = inspector.ping()
        return "ok" if ping else "error"
    except Exception:
        return "error"


@app.get("/health/services", response_model=ServiceHealthResponse)
def health_services() -> ServiceHealthResponse:
    """Check connectivity to Redis, Postgres, and Celery workers."""
    return ServiceHealthResponse(
        redis=_check_redis_health(),
        db=_check_db_health(),
        workers=_check_workers_health(),
    )


def _is_running_in_docker() -> bool:
    """Return True when the process is running inside a Docker container."""
    if Path("/.dockerenv").exists():
        return True
    raw = os.environ.get("HELPING_HANDS_IN_DOCKER", "").strip().lower()
    return raw in {"1", "true", "yes"}


@app.get("/config", response_model=ServerConfig)
def get_server_config() -> ServerConfig:
    """Return runtime configuration used to seed frontend defaults."""
    in_docker = _is_running_in_docker()
    return ServerConfig(in_docker=in_docker, native_auth_default=not in_docker)


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
        skills=req.skills,
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
      :root {{
        --background: #020817;
        --background-soft: #0b1220;
        --panel: #0f172a;
        --panel-elevated: #111b31;
        --foreground: #e2e8f0;
        --muted: #94a3b8;
        --border: #1f2937;
        --secondary: #1e293b;
        --secondary-hover: #334155;
        --mono: ui-monospace, SFMono-Regular, Menlo, monospace;
      }}
      * {{
        box-sizing: border-box;
      }}
      html,
      body {{
        min-height: 100%;
      }}
      body {{
        margin: 0;
        min-height: 100vh;
        font-family: "Space Grotesk", "Segoe UI", sans-serif;
        color: var(--foreground);
        background:
          radial-gradient(circle at 10% -10%, #172554 0%, transparent 40%),
          radial-gradient(circle at 110% 0%, #1e1b4b 0%, transparent 42%),
          linear-gradient(180deg, var(--background-soft) 0%, var(--background) 100%);
      }}
      .page {{
        max-width: 1200px;
        min-height: 100vh;
        margin: 0 auto;
        padding: 28px 20px 36px;
        display: grid;
        gap: 14px;
      }}
      .card {{
        background: linear-gradient(
          180deg,
          var(--panel-elevated) 0%,
          var(--panel) 100%
        );
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 16px;
        box-shadow: 0 20px 40px rgba(2, 8, 23, 0.45);
      }}
      .meta {{
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 10px;
      }}
      .meta-item {{
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 10px;
        background: #0b1326;
      }}
      .meta-label {{
        display: block;
        font-size: 0.82rem;
        color: var(--muted);
        margin-bottom: 4px;
      }}
      .meta-item strong {{
        display: block;
        font-family: var(--mono);
        font-size: 0.84rem;
        line-height: 1.35;
        overflow-wrap: anywhere;
      }}
      pre {{
        margin: 0;
        min-height: 220px;
        max-height: min(68vh, 860px);
        overflow: auto;
        padding: 12px;
        border-radius: 10px;
        border: 1px solid var(--border);
        background: #020817;
        color: #cbd5e1;
        font-family: var(--mono);
        font-size: 0.8rem;
        line-height: 1.45;
        white-space: pre-wrap;
        word-break: break-word;
      }}
      .updates {{
        min-height: 140px;
      }}
      .actions {{
        display: flex;
        gap: 9px;
        flex-wrap: wrap;
        margin-top: 12px;
      }}
      a {{
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 8px 12px;
        background: var(--secondary);
        color: var(--foreground);
        text-decoration: none;
      }}
      a:hover {{
        background: var(--secondary-hover);
      }}
      h2 {{
        margin: 0 0 8px;
        font-size: 1rem;
      }}
      @media (max-width: 720px) {{
        .meta {{ grid-template-columns: 1fr; }}
      }}
    </style>
  </head>
  <body>
    <main class="page">
      <section class="card">
        <div class="meta">
          <div class="meta-item">
            <span class="meta-label">Task</span>
            <strong>{html.escape(task_status.task_id)}</strong>
          </div>
          <div class="meta-item">
            <span class="meta-label">Status</span>
            <strong>{html.escape(status)}</strong>
          </div>
          <div class="meta-item">
            <span class="meta-label">Polling</span>
            <strong>
              {"active" if status not in _TERMINAL_TASK_STATES else "off"}
            </strong>
          </div>
        </div>
        <div class="actions">
          <a href="/">Back to runner</a>
          <a href="/tasks/{html.escape(task_status.task_id)}">Raw JSON</a>
        </div>
      </section>
      <section class="card">
        <h2>Updates</h2>
        <pre class="updates">{updates_html}</pre>
      </section>
      <section class="card">
        <h2>Payload</h2>
        <pre>{escaped_payload}</pre>
      </section>
    </main>
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
    skills: str | None = Form(None),
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
        if skills and skills.strip():
            query["skills"] = skills
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
            skills=list(meta_skills.normalize_skill_selection(skills)),
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
        if skills and skills.strip():
            query["skills"] = skills
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
    if req.skills:
        query["skills"] = ",".join(req.skills)
    return RedirectResponse(url=f"/monitor/{response.task_id}", status_code=303)


@app.get("/monitor/{task_id}", response_class=HTMLResponse)
def monitor(task_id: str) -> HTMLResponse:
    """No-JS monitor page with auto-refresh for task status/updates."""
    task_status = _build_task_status(task_id)
    return HTMLResponse(_render_monitor_page(task_status))


def _resolve_worker_capacity() -> WorkerCapacityResponse:
    """Resolve max worker capacity: Celery inspect stats > env override > default."""
    per_worker: dict[str, int] = {}
    try:
        inspector = celery_app.control.inspect(timeout=1.0)
        if inspector is not None:
            stats = _safe_inspect_call(inspector, "stats")
            if isinstance(stats, dict):
                for worker_name, worker_stats in stats.items():
                    if not isinstance(worker_stats, dict):
                        continue
                    pool = worker_stats.get("pool", {})
                    if isinstance(pool, dict):
                        concurrency = pool.get("max-concurrency")
                        if isinstance(concurrency, int) and concurrency > 0:
                            per_worker[worker_name] = concurrency
    except Exception:
        pass

    if per_worker:
        return WorkerCapacityResponse(
            max_workers=sum(per_worker.values()),
            source="celery",
            workers=per_worker,
        )

    for env_var in _WORKER_CAPACITY_ENV_VARS:
        raw = os.environ.get(env_var, "").strip()
        if not raw:
            continue
        try:
            parsed = int(raw)
        except ValueError:
            continue
        if parsed >= 1:
            return WorkerCapacityResponse(
                max_workers=parsed,
                source=f"env:{env_var}",
                workers={},
            )

    return WorkerCapacityResponse(
        max_workers=_DEFAULT_WORKER_CAPACITY,
        source="default",
        workers={},
    )


@app.get("/workers/capacity", response_model=WorkerCapacityResponse)
def get_worker_capacity() -> WorkerCapacityResponse:
    """Report current max worker capacity for the cluster."""
    return _resolve_worker_capacity()


@app.get("/tasks/current", response_model=CurrentTasksResponse)
def get_current_tasks() -> CurrentTasksResponse:
    """List currently active/queued task UUIDs discovered by Flower/Celery."""
    return _collect_current_tasks()


@app.get("/tasks/{task_id}", response_model=TaskStatus)
def get_task(task_id: str) -> TaskStatus:
    """Check the status of an enqueued task."""
    return _build_task_status(task_id)


# --- Schedule Endpoints ---


def _get_schedule_manager():
    """Get or create the schedule manager singleton."""
    global _schedule_manager
    if _schedule_manager is None:
        try:
            from helping_hands.server.schedules import get_schedule_manager

            _schedule_manager = get_schedule_manager(celery_app)
        except ImportError as exc:
            from fastapi import HTTPException

            raise HTTPException(
                status_code=503,
                detail=f"Scheduling not available: {exc}. "
                "Install with: uv sync --extra server",
            ) from exc
    return _schedule_manager


def _schedule_to_response(task) -> ScheduleResponse:
    """Convert a ScheduledTask to a ScheduleResponse."""
    import contextlib

    from helping_hands.server.schedules import next_run_time

    next_run = None
    if task.enabled:
        with contextlib.suppress(Exception):
            next_run = next_run_time(task.cron_expression).isoformat()

    return ScheduleResponse(
        schedule_id=task.schedule_id,
        name=task.name,
        cron_expression=task.cron_expression,
        repo_path=task.repo_path,
        prompt=task.prompt,
        backend=task.backend,
        model=task.model,
        max_iterations=task.max_iterations,
        pr_number=task.pr_number,
        no_pr=task.no_pr,
        enable_execution=task.enable_execution,
        enable_web=task.enable_web,
        use_native_cli_auth=task.use_native_cli_auth,
        skills=task.skills,
        enabled=task.enabled,
        created_at=task.created_at,
        last_run_at=task.last_run_at,
        last_run_task_id=task.last_run_task_id,
        run_count=task.run_count,
        next_run_at=next_run,
    )


@app.get("/schedules/presets", response_model=CronPresetsResponse)
def get_cron_presets() -> CronPresetsResponse:
    """Get available cron expression presets."""
    from helping_hands.server.schedules import CRON_PRESETS

    return CronPresetsResponse(presets=CRON_PRESETS)


@app.get("/schedules", response_model=ScheduleListResponse)
def list_schedules() -> ScheduleListResponse:
    """List all scheduled tasks."""
    manager = _get_schedule_manager()
    tasks = manager.list_schedules()
    return ScheduleListResponse(
        schedules=[_schedule_to_response(t) for t in tasks],
        total=len(tasks),
    )


@app.post("/schedules", response_model=ScheduleResponse, status_code=201)
def create_schedule(request: ScheduleRequest) -> ScheduleResponse:
    """Create a new scheduled task."""
    from fastapi import HTTPException

    from helping_hands.server.schedules import ScheduledTask, generate_schedule_id

    manager = _get_schedule_manager()

    task = ScheduledTask(
        schedule_id=generate_schedule_id(),
        name=request.name,
        cron_expression=request.cron_expression,
        repo_path=request.repo_path,
        prompt=request.prompt,
        backend=request.backend,
        model=request.model,
        max_iterations=request.max_iterations,
        pr_number=request.pr_number,
        no_pr=request.no_pr,
        enable_execution=request.enable_execution,
        enable_web=request.enable_web,
        use_native_cli_auth=request.use_native_cli_auth,
        skills=request.skills,
        enabled=request.enabled,
    )

    try:
        created = manager.create_schedule(task)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _schedule_to_response(created)


@app.get("/schedules/{schedule_id}", response_model=ScheduleResponse)
def get_schedule(schedule_id: str) -> ScheduleResponse:
    """Get a scheduled task by ID."""
    from fastapi import HTTPException

    manager = _get_schedule_manager()
    task = manager.get_schedule(schedule_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return _schedule_to_response(task)


@app.put("/schedules/{schedule_id}", response_model=ScheduleResponse)
def update_schedule(schedule_id: str, request: ScheduleRequest) -> ScheduleResponse:
    """Update a scheduled task."""
    from fastapi import HTTPException

    from helping_hands.server.schedules import ScheduledTask

    manager = _get_schedule_manager()

    task = ScheduledTask(
        schedule_id=schedule_id,
        name=request.name,
        cron_expression=request.cron_expression,
        repo_path=request.repo_path,
        prompt=request.prompt,
        backend=request.backend,
        model=request.model,
        max_iterations=request.max_iterations,
        pr_number=request.pr_number,
        no_pr=request.no_pr,
        enable_execution=request.enable_execution,
        enable_web=request.enable_web,
        use_native_cli_auth=request.use_native_cli_auth,
        skills=request.skills,
        enabled=request.enabled,
    )

    try:
        updated = manager.update_schedule(task)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return _schedule_to_response(updated)


@app.delete("/schedules/{schedule_id}", status_code=204)
def delete_schedule(schedule_id: str) -> None:
    """Delete a scheduled task."""
    from fastapi import HTTPException

    manager = _get_schedule_manager()
    if not manager.delete_schedule(schedule_id):
        raise HTTPException(status_code=404, detail="Schedule not found")


@app.post("/schedules/{schedule_id}/enable", response_model=ScheduleResponse)
def enable_schedule(schedule_id: str) -> ScheduleResponse:
    """Enable a scheduled task."""
    from fastapi import HTTPException

    manager = _get_schedule_manager()
    task = manager.enable_schedule(schedule_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return _schedule_to_response(task)


@app.post("/schedules/{schedule_id}/disable", response_model=ScheduleResponse)
def disable_schedule(schedule_id: str) -> ScheduleResponse:
    """Disable a scheduled task."""
    from fastapi import HTTPException

    manager = _get_schedule_manager()
    task = manager.disable_schedule(schedule_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return _schedule_to_response(task)


@app.post("/schedules/{schedule_id}/trigger", response_model=ScheduleTriggerResponse)
def trigger_schedule(schedule_id: str) -> ScheduleTriggerResponse:
    """Manually trigger a scheduled task to run immediately."""
    from fastapi import HTTPException

    manager = _get_schedule_manager()
    task_id = manager.trigger_now(schedule_id)
    if task_id is None:
        raise HTTPException(status_code=404, detail="Schedule not found")

    return ScheduleTriggerResponse(
        schedule_id=schedule_id,
        task_id=task_id,
        message="Schedule triggered successfully",
    )
