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
from pydantic import BaseModel, Field, ValidationError, field_validator

from helping_hands.lib.default_prompts import DEFAULT_SMOKE_TEST_PROMPT
from helping_hands.lib.meta import skills as meta_skills
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
            <h1>helping_hands runner</h1>
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
                      <option value="e2e">e2e</option>
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
                    <input id="model" name="model" placeholder="gpt-5.2" />
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
              <strong id="status">idle</strong>
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

      function setView(nextView) {
        const isSubmission = nextView === "submission";
        submissionView.classList.toggle("is-hidden", !isSubmission);
        monitorView.classList.toggle("is-hidden", isSubmission);
        newSubmissionBtn.classList.toggle("active", isSubmission);
      }

      function setStatus(value) {
        status = value;
        statusEl.textContent = value;
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
          const statusPill = document.createElement("span");
          statusPill.className = `status-pill ${statusTone(item.status)}`;
          statusPill.textContent = item.status;
          top.appendChild(idCode);
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


@app.get("/tasks/current", response_model=CurrentTasksResponse)
def get_current_tasks() -> CurrentTasksResponse:
    """List currently active/queued task UUIDs discovered by Flower/Celery."""
    return _collect_current_tasks()


@app.get("/tasks/{task_id}", response_model=TaskStatus)
def get_task(task_id: str) -> TaskStatus:
    """Check the status of an enqueued task."""
    return _build_task_status(task_id)
