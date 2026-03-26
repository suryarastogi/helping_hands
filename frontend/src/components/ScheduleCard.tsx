import { type FormEvent, useMemo } from "react";

import { BACKEND_OPTIONS, backendDisplayName, CRON_PRESETS } from "../App.utils";
import type { Backend, ScheduleFormState, ScheduleItem } from "../types";
import RepoChipInput from "./RepoChipInput";
import RepoSuggestInput from "./RepoSuggestInput";

export interface ScheduleCardProps {
  schedules: ScheduleItem[];
  scheduleForm: ScheduleFormState;
  editingScheduleId: string | null;
  showScheduleForm: boolean;
  scheduleError: string | null;
  onUpdateField: <K extends keyof ScheduleFormState>(
    key: K,
    value: ScheduleFormState[K],
  ) => void;
  onNewSchedule: () => void;
  onEditSchedule: (scheduleId: string) => Promise<void>;
  onSaveSchedule: (event: FormEvent) => Promise<void>;
  onDeleteSchedule: (scheduleId: string) => Promise<void>;
  onTriggerSchedule: (scheduleId: string) => Promise<void>;
  onToggleSchedule: (scheduleId: string, enable: boolean) => Promise<void>;
  onCancelForm: () => void;
  onRefresh: () => Promise<void>;
  recentRepos?: string[];
}

function ScheduleFormFields({
  scheduleForm,
  editingScheduleId,
  onUpdateField,
  onSaveSchedule,
  onCancelForm,
  recentRepos = [],
}: Pick<
  ScheduleCardProps,
  "scheduleForm" | "editingScheduleId" | "onUpdateField" | "onSaveSchedule" | "onCancelForm" | "recentRepos"
>) {
  const referenceChips = useMemo(
    () =>
      scheduleForm.reference_repos
        .split(",")
        .map((s) => s.trim())
        .filter((s) => s.length > 0),
    [scheduleForm.reference_repos],
  );

  const setReferenceChips = (repos: string[]) => {
    onUpdateField("reference_repos", repos.join(", "));
  };

  return (
    <form onSubmit={onSaveSchedule} className="form-grid" style={{ marginTop: 0 }}>
      <label>
        Name
        <input
          value={scheduleForm.name}
          onChange={(e) => onUpdateField("name", e.target.value)}
          required
          placeholder="e.g. Daily docs update"
        />
      </label>

      <div className="row two-col">
        <label>
          Cron expression
          <input
            value={scheduleForm.cron_expression}
            onChange={(e) => onUpdateField("cron_expression", e.target.value)}
            required
            placeholder="0 0 * * * (midnight)"
          />
        </label>
        <label>
          Or preset
          <select
            value={
              Object.entries(CRON_PRESETS).find(
                ([, v]) => v === scheduleForm.cron_expression,
              )?.[0] ?? ""
            }
            onChange={(e) => {
              const preset = e.target.value;
              if (preset && CRON_PRESETS[preset]) {
                onUpdateField("cron_expression", CRON_PRESETS[preset]);
              }
            }}
          >
            <option value="">Custom</option>
            {Object.entries(CRON_PRESETS).map(([key, val]) => (
              <option key={key} value={key}>
                {key.replace(/_/g, " ")} ({val})
              </option>
            ))}
          </select>
        </label>
      </div>

      <label>
        Repo path (owner/repo)
        <RepoSuggestInput
          value={scheduleForm.repo_path}
          onChange={(val) => onUpdateField("repo_path", val)}
          suggestions={recentRepos}
          required
          placeholder="owner/repo"
          ariaLabel="Schedule repo path"
        />
      </label>

      <label>
        Prompt
        <textarea
          value={scheduleForm.prompt}
          onChange={(e) => onUpdateField("prompt", e.target.value)}
          required
          rows={4}
          placeholder="Update documentation..."
        />
      </label>

      <details className="advanced-settings">
        <summary>Advanced settings</summary>
        <div className="advanced-settings-body">
          <div className="row two-col">
            <label>
              Backend
              <select
                value={scheduleForm.backend}
                onChange={(e) => onUpdateField("backend", e.target.value as Backend)}
              >
                {BACKEND_OPTIONS.map((b) => (
                  <option key={b} value={b}>{backendDisplayName(b)}</option>
                ))}
              </select>
            </label>
            <label>
              Model
              <input
                value={scheduleForm.model}
                onChange={(e) => onUpdateField("model", e.target.value)}
                placeholder="claude-opus-4-6"
              />
            </label>
          </div>
          <div className="row two-col">
            <label>
              Max iterations
              <input
                type="number"
                min={1}
                value={scheduleForm.max_iterations}
                onChange={(e) =>
                  onUpdateField("max_iterations", Math.max(1, Number(e.target.value || 1)))
                }
              />
            </label>
            <label>
              PR number
              <input
                type="number"
                min={1}
                value={scheduleForm.pr_number}
                onChange={(e) => onUpdateField("pr_number", e.target.value)}
              />
            </label>
          </div>
          <label>
            Tools
            <input
              value={scheduleForm.tools}
              onChange={(e) => onUpdateField("tools", e.target.value)}
              placeholder="execution,web"
            />
          </label>
          <label>
            Skills
            <input
              value={scheduleForm.skills}
              onChange={(e) => onUpdateField("skills", e.target.value)}
              placeholder="execution,web,prd"
            />
          </label>
          <div className="row check-grid">
            <label className="check-row">
              <input
                type="checkbox"
                checked={scheduleForm.no_pr}
                onChange={(e) => onUpdateField("no_pr", e.target.checked)}
              />
              No PR
            </label>
            <label className="check-row">
              <input
                type="checkbox"
                checked={scheduleForm.enable_execution}
                onChange={(e) => onUpdateField("enable_execution", e.target.checked)}
              />
              Execution
            </label>
            <label className="check-row">
              <input
                type="checkbox"
                checked={scheduleForm.enable_web}
                onChange={(e) => onUpdateField("enable_web", e.target.checked)}
              />
              Web
            </label>
            <label className="check-row">
              <input
                type="checkbox"
                checked={scheduleForm.use_native_cli_auth}
                onChange={(e) => onUpdateField("use_native_cli_auth", e.target.checked)}
              />
              Native auth
            </label>
            <label className="check-row">
              <input
                type="checkbox"
                checked={scheduleForm.fix_ci}
                onChange={(e) => onUpdateField("fix_ci", e.target.checked)}
              />
              Fix CI
            </label>
            <label className="check-row">
              <input
                type="checkbox"
                checked={scheduleForm.enabled}
                onChange={(e) => onUpdateField("enabled", e.target.checked)}
              />
              Enabled
            </label>
          </div>
          <div className="row">
            <label>
              GitHub Token
              <input
                type="password"
                value={scheduleForm.github_token}
                onChange={(e) => onUpdateField("github_token", e.target.value)}
                placeholder="ghp_... (optional)"
              />
            </label>
          </div>
          <div className="row">
            <label>
              Reference Repos
              <RepoChipInput
                value={referenceChips}
                onChange={setReferenceChips}
                suggestions={recentRepos}
                placeholder="owner/repo (optional, read-only)"
                ariaLabel="Schedule reference repos"
              />
            </label>
          </div>
        </div>
      </details>

      <div style={{ display: "flex", gap: 8 }}>
        <button type="submit">
          {editingScheduleId ? "Update schedule" : "Create schedule"}
        </button>
        <button
          type="button"
          className="secondary"
          onClick={onCancelForm}
        >
          Cancel
        </button>
      </div>
    </form>
  );
}

export default function ScheduleCard({
  schedules,
  scheduleForm,
  editingScheduleId,
  showScheduleForm,
  scheduleError,
  onUpdateField,
  onNewSchedule,
  onEditSchedule,
  onSaveSchedule,
  onDeleteSchedule,
  onTriggerSchedule,
  onToggleSchedule,
  onCancelForm,
  onRefresh,
  recentRepos = [],
}: ScheduleCardProps) {
  const formFieldsProps = {
    scheduleForm,
    editingScheduleId,
    onUpdateField,
    onSaveSchedule,
    onCancelForm,
    recentRepos,
  };

  return (
    <section className="card compact-form" style={{ padding: "14px 16px" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
        <div>
          <h2 style={{ margin: 0, fontSize: "1.1rem" }}>
            Scheduled tasks{" "}
            <span className="status-pill run" style={{ fontSize: "0.6rem", verticalAlign: "middle" }}>
              cron
            </span>
          </h2>
          <p style={{ margin: "4px 0 0", color: "var(--muted)", fontSize: "0.84rem" }}>
            Create and manage recurring builds.
          </p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button type="button" onClick={onNewSchedule}>
            New schedule
          </button>
          <button type="button" className="secondary" onClick={() => void onRefresh()}>
            Refresh
          </button>
        </div>
      </div>

      {scheduleError && (
        <div style={{ padding: "8px 10px", marginBottom: 10, borderRadius: 8, background: "var(--danger-soft)", border: "1px solid var(--danger)", color: "#fca5a5", fontSize: "0.84rem" }}>
          {scheduleError}
        </div>
      )}

      {showScheduleForm && !editingScheduleId && (
        <div style={{ marginBottom: 14, paddingBottom: 14, borderBottom: "1px solid var(--border)" }}>
          <h3 style={{ margin: "0 0 10px", fontSize: "0.95rem" }}>New schedule</h3>
          <ScheduleFormFields {...formFieldsProps} />
        </div>
      )}

      {schedules.length === 0 && !showScheduleForm ? (
        <p className="empty-list">No scheduled tasks yet.</p>
      ) : (
        <div style={{ display: "grid", gap: 8 }}>
          {schedules.map((item) => (
            <div key={item.schedule_id} className="schedule-item">
              {editingScheduleId === item.schedule_id ? (
                <div style={{ padding: "4px 0" }}>
                  <ScheduleFormFields {...formFieldsProps} />
                </div>
              ) : (
                <>
                  <div className="schedule-item-header">
                    <strong>{item.name}</strong>
                    <span className={`status-pill ${item.enabled ? "ok" : "idle"}`}>
                      {item.enabled ? "enabled" : "disabled"}
                    </span>
                  </div>
                  <div className="schedule-item-meta">
                    <code>{item.cron_expression}</code> &middot; {item.repo_path} &middot;{" "}
                    {item.backend}
                    {item.next_run_at && (
                      <> &middot; next: {new Date(item.next_run_at).toLocaleString()}</>
                    )}
                  </div>
                  <div className="schedule-item-meta" style={{ fontSize: "0.72rem" }}>
                    {item.run_count} runs
                    {item.last_run_at && (
                      <> &middot; last: {new Date(item.last_run_at).toLocaleString()}</>
                    )}
                  </div>
                  <div className="schedule-item-actions">
                    <button
                      type="button"
                      className="secondary"
                      style={{ padding: "5px 10px", fontSize: "0.76rem" }}
                      onClick={() => void onEditSchedule(item.schedule_id)}
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      className="secondary"
                      style={{ padding: "5px 10px", fontSize: "0.76rem" }}
                      onClick={() => void onTriggerSchedule(item.schedule_id)}
                    >
                      Run now
                    </button>
                    <button
                      type="button"
                      className="secondary"
                      style={{ padding: "5px 10px", fontSize: "0.76rem" }}
                      onClick={() => void onToggleSchedule(item.schedule_id, !item.enabled)}
                    >
                      {item.enabled ? "Disable" : "Enable"}
                    </button>
                    <button
                      type="button"
                      style={{
                        padding: "5px 10px",
                        fontSize: "0.76rem",
                        background: "var(--danger-soft)",
                        border: "1px solid var(--danger)",
                        color: "#fca5a5",
                      }}
                      onClick={() => void onDeleteSchedule(item.schedule_id)}
                    >
                      Delete
                    </button>
                  </div>
                </>
              )}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
