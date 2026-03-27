import { type FormEvent, useCallback, useState } from "react";

import type { Backend, ScheduleFormState, ScheduleItem } from "../types";
import { apiUrl, INITIAL_SCHEDULE_FORM, parseError } from "../App.utils";

export interface UseSchedulesReturn {
  schedules: ScheduleItem[];
  scheduleForm: ScheduleFormState;
  editingScheduleId: string | null;
  showScheduleForm: boolean;
  scheduleError: string | null;
  updateScheduleField: <K extends keyof ScheduleFormState>(
    key: K,
    value: ScheduleFormState[K],
  ) => void;
  loadSchedules: () => Promise<void>;
  openNewScheduleForm: () => void;
  openEditScheduleForm: (scheduleId: string) => Promise<void>;
  saveSchedule: (event: FormEvent) => Promise<void>;
  deleteSchedule: (scheduleId: string) => Promise<void>;
  triggerSchedule: (scheduleId: string) => Promise<void>;
  toggleSchedule: (scheduleId: string, enable: boolean) => Promise<void>;
  cancelScheduleForm: () => void;
}

export function useSchedules(): UseSchedulesReturn {
  const [schedules, setSchedules] = useState<ScheduleItem[]>([]);
  const [scheduleForm, setScheduleForm] = useState<ScheduleFormState>(INITIAL_SCHEDULE_FORM);
  const [editingScheduleId, setEditingScheduleId] = useState<string | null>(null);
  const [showScheduleForm, setShowScheduleForm] = useState(false);
  const [scheduleError, setScheduleError] = useState<string | null>(null);

  const updateScheduleField = <K extends keyof ScheduleFormState>(
    key: K,
    value: ScheduleFormState[K],
  ) => {
    setScheduleForm((current) => ({ ...current, [key]: value }));
  };

  const loadSchedules = useCallback(async () => {
    setScheduleError(null);
    try {
      const response = await fetch(apiUrl("/schedules"), { cache: "no-store" });
      if (!response.ok) {
        const detail = await parseError(response);
        throw new Error(detail);
      }
      const data = (await response.json()) as { schedules: ScheduleItem[]; total: number };
      setSchedules(data.schedules);
    } catch (error) {
      setScheduleError(String(error));
    }
  }, []);

  const openNewScheduleForm = () => {
    setEditingScheduleId(null);
    setScheduleForm(INITIAL_SCHEDULE_FORM);
    setShowScheduleForm(true);
    setScheduleError(null);
  };

  const openEditScheduleForm = async (scheduleId: string) => {
    setScheduleError(null);
    try {
      const response = await fetch(apiUrl(`/schedules/${scheduleId}`), { cache: "no-store" });
      if (!response.ok) {
        const detail = await parseError(response);
        throw new Error(detail);
      }
      const item = (await response.json()) as ScheduleItem;
      setScheduleForm({
        name: item.name,
        cron_expression: item.cron_expression,
        repo_path: item.repo_path,
        prompt: item.prompt,
        backend: item.backend as Backend,
        model: item.model ?? "",
        max_iterations: item.max_iterations,
        pr_number: item.pr_number != null ? String(item.pr_number) : "",
        issue_number: item.issue_number != null ? String(item.issue_number) : "",
        no_pr: item.no_pr,
        enable_execution: item.enable_execution,
        enable_web: item.enable_web,
        use_native_cli_auth: item.use_native_cli_auth,
        fix_ci: item.fix_ci ?? false,
        ci_check_wait_minutes: item.ci_check_wait_minutes ?? 3,
        github_token: item.github_token ?? "",
        reference_repos: (item.reference_repos ?? []).join(", "),
        tools: (item.tools ?? []).join(", "),
        skills: item.skills.join(", "),
        enabled: item.enabled,
      });
      setEditingScheduleId(scheduleId);
      setShowScheduleForm(false);
    } catch (error) {
      setScheduleError(String(error));
    }
  };

  const saveSchedule = async (event: FormEvent) => {
    event.preventDefault();
    setScheduleError(null);

    const name = scheduleForm.name.trim();
    const cronExpr = scheduleForm.cron_expression.trim();
    const schedRepoPath = scheduleForm.repo_path.trim();
    const schedPrompt = scheduleForm.prompt.trim();
    if (!name || !cronExpr || !schedRepoPath || !schedPrompt) {
      setScheduleError("Name, cron expression, repository path, and prompt are required.");
      return;
    }

    const body: Record<string, unknown> = {
      name,
      cron_expression: cronExpr,
      repo_path: schedRepoPath,
      prompt: schedPrompt,
      backend: scheduleForm.backend,
      max_iterations: scheduleForm.max_iterations,
      no_pr: scheduleForm.no_pr,
      enable_execution: scheduleForm.enable_execution,
      enable_web: scheduleForm.enable_web,
      use_native_cli_auth: scheduleForm.use_native_cli_auth,
      fix_ci: scheduleForm.fix_ci,
      ci_check_wait_minutes: scheduleForm.ci_check_wait_minutes,
      enabled: scheduleForm.enabled,
    };
    if (scheduleForm.github_token.trim()) {
      body.github_token = scheduleForm.github_token.trim();
    }
    if (scheduleForm.reference_repos.trim()) {
      body.reference_repos = scheduleForm.reference_repos.split(",").map((s: string) => s.trim()).filter((s: string) => s.length > 0);
    }
    if (scheduleForm.model.trim()) body.model = scheduleForm.model.trim();
    if (scheduleForm.pr_number.trim()) {
      const parsed = Number(scheduleForm.pr_number.trim());
      if (!Number.isNaN(parsed) && Number.isFinite(parsed)) {
        body.pr_number = parsed;
      }
    }
    if (scheduleForm.issue_number.trim()) {
      const parsed = Number(scheduleForm.issue_number.trim());
      if (!Number.isNaN(parsed) && Number.isFinite(parsed)) {
        body.issue_number = parsed;
      }
    }
    if (scheduleForm.tools.trim()) {
      body.tools = scheduleForm.tools
        .split(",")
        .map((s) => s.trim())
        .filter((s) => s.length > 0);
    }
    if (scheduleForm.skills.trim()) {
      body.skills = scheduleForm.skills
        .split(",")
        .map((s) => s.trim())
        .filter((s) => s.length > 0);
    }

    const isEdit = editingScheduleId !== null;
    const url = isEdit ? apiUrl(`/schedules/${editingScheduleId}`) : apiUrl("/schedules");
    const method = isEdit ? "PUT" : "POST";

    try {
      const response = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!response.ok) {
        const detail = await parseError(response);
        throw new Error(detail);
      }
      setShowScheduleForm(false);
      setEditingScheduleId(null);
      setScheduleForm(INITIAL_SCHEDULE_FORM);
      await loadSchedules();
    } catch (error) {
      setScheduleError(String(error));
    }
  };

  const deleteSchedule = async (scheduleId: string) => {
    if (!window.confirm("Delete this schedule? This cannot be undone.")) return;
    setScheduleError(null);
    try {
      const response = await fetch(apiUrl(`/schedules/${scheduleId}`), { method: "DELETE" });
      if (!response.ok && response.status !== 204) {
        const detail = await parseError(response);
        throw new Error(detail);
      }
      await loadSchedules();
    } catch (error) {
      setScheduleError(String(error));
    }
  };

  const triggerSchedule = async (scheduleId: string) => {
    if (!window.confirm("Run this schedule now?")) return;
    setScheduleError(null);
    try {
      const response = await fetch(apiUrl(`/schedules/${scheduleId}/trigger`), { method: "POST" });
      if (!response.ok) {
        const detail = await parseError(response);
        throw new Error(detail);
      }
      const data = (await response.json()) as { task_id: string; message: string };
      window.alert(`Triggered! Task ID: ${data.task_id}`);
      await loadSchedules();
    } catch (error) {
      setScheduleError(String(error));
    }
  };

  const toggleSchedule = async (scheduleId: string, enable: boolean) => {
    setScheduleError(null);
    const action = enable ? "enable" : "disable";
    try {
      const response = await fetch(apiUrl(`/schedules/${scheduleId}/${action}`), { method: "POST" });
      if (!response.ok) {
        const detail = await parseError(response);
        throw new Error(detail);
      }
      await loadSchedules();
    } catch (error) {
      setScheduleError(String(error));
    }
  };

  const cancelScheduleForm = () => {
    setShowScheduleForm(false);
    setEditingScheduleId(null);
    setScheduleForm(INITIAL_SCHEDULE_FORM);
    setScheduleError(null);
  };

  return {
    schedules,
    scheduleForm,
    editingScheduleId,
    showScheduleForm,
    scheduleError,
    updateScheduleField,
    loadSchedules,
    openNewScheduleForm,
    openEditScheduleForm,
    saveSchedule,
    deleteSchedule,
    triggerSchedule,
    toggleSchedule,
    cancelScheduleForm,
  };
}
