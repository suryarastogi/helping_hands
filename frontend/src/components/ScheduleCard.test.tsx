import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";

import ScheduleCard, { type ScheduleCardProps } from "./ScheduleCard";
import { BACKEND_OPTIONS, CRON_PRESETS, INITIAL_SCHEDULE_FORM } from "../App.utils";
import type { ScheduleItem } from "../types";

afterEach(cleanup);

const MOCK_SCHEDULE: ScheduleItem = {
  schedule_id: "sched-1",
  name: "Nightly Build",
  cron_expression: "0 0 * * *",
  repo_path: "owner/repo",
  prompt: "Update docs",
  backend: "claudecodecli",
  model: null,
  max_iterations: 6,
  pr_number: null,
  no_pr: false,
  enable_execution: false,
  enable_web: false,
  use_native_cli_auth: false,
  fix_ci: false,
  ci_check_wait_minutes: 3,
  github_token: null,
  reference_repos: [],
  tools: [],
  skills: [],
  enabled: true,
  created_at: "2026-03-23T00:00:00Z",
  last_run_at: "2026-03-23T01:00:00Z",
  last_run_task_id: "task-abc",
  run_count: 5,
  next_run_at: "2026-03-24T00:00:00Z",
};

function defaultProps(overrides?: Partial<ScheduleCardProps>): ScheduleCardProps {
  return {
    schedules: [],
    scheduleForm: { ...INITIAL_SCHEDULE_FORM },
    editingScheduleId: null,
    showScheduleForm: false,
    scheduleError: null,
    onUpdateField: vi.fn(),
    onNewSchedule: vi.fn(),
    onEditSchedule: vi.fn(),
    onSaveSchedule: vi.fn(),
    onDeleteSchedule: vi.fn(),
    onTriggerSchedule: vi.fn(),
    onToggleSchedule: vi.fn(),
    onCancelForm: vi.fn(),
    onRefresh: vi.fn(),
    backends: BACKEND_OPTIONS,
    ...overrides,
  };
}

describe("ScheduleCard", () => {
  it("renders heading and cron pill", () => {
    render(<ScheduleCard {...defaultProps()} />);
    expect(screen.getByText("Scheduled tasks")).toBeInTheDocument();
    expect(screen.getByText("cron")).toBeInTheDocument();
  });

  it("shows empty message when no schedules and form hidden", () => {
    render(<ScheduleCard {...defaultProps()} />);
    expect(screen.getByText("No scheduled tasks yet.")).toBeInTheDocument();
  });

  it("renders schedule items", () => {
    render(<ScheduleCard {...defaultProps({ schedules: [MOCK_SCHEDULE] })} />);
    expect(screen.getByText("Nightly Build")).toBeInTheDocument();
    expect(screen.getByText("enabled")).toBeInTheDocument();
    expect(screen.getByText("0 0 * * *")).toBeInTheDocument();
    expect(screen.getByText(/5 runs/)).toBeInTheDocument();
  });

  it("renders disabled pill for disabled schedule", () => {
    const disabled = { ...MOCK_SCHEDULE, enabled: false };
    render(<ScheduleCard {...defaultProps({ schedules: [disabled] })} />);
    expect(screen.getByText("disabled")).toBeInTheDocument();
  });

  it("calls onNewSchedule when New schedule button clicked", () => {
    const onNewSchedule = vi.fn();
    render(<ScheduleCard {...defaultProps({ onNewSchedule })} />);
    fireEvent.click(screen.getByRole("button", { name: "New schedule" }));
    expect(onNewSchedule).toHaveBeenCalledOnce();
  });

  it("calls onRefresh when Refresh button clicked", () => {
    const onRefresh = vi.fn().mockResolvedValue(undefined);
    render(<ScheduleCard {...defaultProps({ onRefresh })} />);
    fireEvent.click(screen.getByRole("button", { name: "Refresh" }));
    expect(onRefresh).toHaveBeenCalledOnce();
  });

  it("displays error message when scheduleError is set", () => {
    render(<ScheduleCard {...defaultProps({ scheduleError: "Network error" })} />);
    expect(screen.getByText("Network error")).toBeInTheDocument();
  });

  it("shows new schedule form when showScheduleForm is true", () => {
    render(<ScheduleCard {...defaultProps({ showScheduleForm: true })} />);
    expect(screen.getByText("New schedule", { selector: "h3" })).toBeInTheDocument();
    expect(screen.getByText("Create schedule")).toBeInTheDocument();
  });

  it("shows Update schedule button when editing", () => {
    render(
      <ScheduleCard
        {...defaultProps({
          schedules: [MOCK_SCHEDULE],
          editingScheduleId: "sched-1",
        })}
      />,
    );
    expect(screen.getByText("Update schedule")).toBeInTheDocument();
  });

  it("calls onSaveSchedule on form submit", () => {
    const onSaveSchedule = vi.fn().mockImplementation((e: Event) => e.preventDefault());
    render(
      <ScheduleCard
        {...defaultProps({
          showScheduleForm: true,
          scheduleForm: {
            ...INITIAL_SCHEDULE_FORM,
            name: "Test",
            cron_expression: "0 0 * * *",
            repo_path: "o/r",
            prompt: "do it",
          },
          onSaveSchedule,
        })}
      />,
    );
    fireEvent.click(screen.getByText("Create schedule"));
    expect(onSaveSchedule).toHaveBeenCalledOnce();
  });

  it("calls onCancelForm when Cancel clicked in new form", () => {
    const onCancelForm = vi.fn();
    render(<ScheduleCard {...defaultProps({ showScheduleForm: true, onCancelForm })} />);
    fireEvent.click(screen.getByText("Cancel"));
    expect(onCancelForm).toHaveBeenCalledOnce();
  });

  it("calls onDeleteSchedule when Delete clicked", () => {
    const onDeleteSchedule = vi.fn().mockResolvedValue(undefined);
    render(<ScheduleCard {...defaultProps({ schedules: [MOCK_SCHEDULE], onDeleteSchedule })} />);
    fireEvent.click(screen.getByText("Delete"));
    expect(onDeleteSchedule).toHaveBeenCalledWith("sched-1");
  });

  it("calls onTriggerSchedule when Run now clicked", () => {
    const onTriggerSchedule = vi.fn().mockResolvedValue(undefined);
    render(<ScheduleCard {...defaultProps({ schedules: [MOCK_SCHEDULE], onTriggerSchedule })} />);
    fireEvent.click(screen.getByText("Run now"));
    expect(onTriggerSchedule).toHaveBeenCalledWith("sched-1");
  });

  it("calls onToggleSchedule with false when Disable clicked", () => {
    const onToggleSchedule = vi.fn().mockResolvedValue(undefined);
    render(<ScheduleCard {...defaultProps({ schedules: [MOCK_SCHEDULE], onToggleSchedule })} />);
    fireEvent.click(screen.getByText("Disable"));
    expect(onToggleSchedule).toHaveBeenCalledWith("sched-1", false);
  });

  it("calls onToggleSchedule with true when Enable clicked", () => {
    const onToggleSchedule = vi.fn().mockResolvedValue(undefined);
    const disabled = { ...MOCK_SCHEDULE, enabled: false };
    render(<ScheduleCard {...defaultProps({ schedules: [disabled], onToggleSchedule })} />);
    fireEvent.click(screen.getByText("Enable"));
    expect(onToggleSchedule).toHaveBeenCalledWith("sched-1", true);
  });

  it("calls onEditSchedule when Edit clicked", () => {
    const onEditSchedule = vi.fn().mockResolvedValue(undefined);
    render(<ScheduleCard {...defaultProps({ schedules: [MOCK_SCHEDULE], onEditSchedule })} />);
    fireEvent.click(screen.getByText("Edit"));
    expect(onEditSchedule).toHaveBeenCalledWith("sched-1");
  });

  it("calls onUpdateField when name input changes in form", () => {
    const onUpdateField = vi.fn();
    render(<ScheduleCard {...defaultProps({ showScheduleForm: true, onUpdateField })} />);
    fireEvent.change(screen.getByPlaceholderText("e.g. Daily docs update"), {
      target: { value: "My Schedule" },
    });
    expect(onUpdateField).toHaveBeenCalledWith("name", "My Schedule");
  });

  it("renders next run time when available", () => {
    render(<ScheduleCard {...defaultProps({ schedules: [MOCK_SCHEDULE] })} />);
    expect(screen.getByText(/next:/)).toBeInTheDocument();
  });

  it("renders last run time when available", () => {
    render(<ScheduleCard {...defaultProps({ schedules: [MOCK_SCHEDULE] })} />);
    expect(screen.getByText(/last:/)).toBeInTheDocument();
  });

  it("does not show new form heading when showScheduleForm is false", () => {
    render(<ScheduleCard {...defaultProps({ showScheduleForm: false })} />);
    expect(screen.queryByText("New schedule", { selector: "h3" })).not.toBeInTheDocument();
  });

  // --- Cron expression & preset select ---

  it("calls onUpdateField with cron_expression when cron input changes", () => {
    const onUpdateField = vi.fn();
    render(<ScheduleCard {...defaultProps({ showScheduleForm: true, onUpdateField })} />);
    fireEvent.change(screen.getByPlaceholderText("0 0 * * * (midnight)"), {
      target: { value: "*/5 * * * *" },
    });
    expect(onUpdateField).toHaveBeenCalledWith("cron_expression", "*/5 * * * *");
  });

  it("selects cron preset and updates cron_expression", () => {
    const onUpdateField = vi.fn();
    render(<ScheduleCard {...defaultProps({ showScheduleForm: true, onUpdateField })} />);
    const presetSelect = screen.getByRole("combobox", { name: /preset/i });
    fireEvent.change(presetSelect, { target: { value: "hourly" } });
    expect(onUpdateField).toHaveBeenCalledWith("cron_expression", CRON_PRESETS["hourly"]);
  });

  it("shows Custom option when cron_expression does not match any preset", () => {
    render(
      <ScheduleCard
        {...defaultProps({
          showScheduleForm: true,
          scheduleForm: { ...INITIAL_SCHEDULE_FORM, cron_expression: "5 4 * * *" },
        })}
      />,
    );
    const presetSelect = screen.getByRole("combobox", { name: /preset/i }) as HTMLSelectElement;
    expect(presetSelect.value).toBe("");
  });

  it("shows matching preset when cron_expression matches a preset value", () => {
    render(
      <ScheduleCard
        {...defaultProps({
          showScheduleForm: true,
          scheduleForm: { ...INITIAL_SCHEDULE_FORM, cron_expression: "0 0 * * *" },
        })}
      />,
    );
    const presetSelect = screen.getByRole("combobox", { name: /preset/i }) as HTMLSelectElement;
    expect(presetSelect.value).toBe("daily");
  });

  it("does not call onUpdateField when empty preset option selected", () => {
    const onUpdateField = vi.fn();
    render(<ScheduleCard {...defaultProps({ showScheduleForm: true, onUpdateField })} />);
    const presetSelect = screen.getByRole("combobox", { name: /preset/i });
    fireEvent.change(presetSelect, { target: { value: "" } });
    expect(onUpdateField).not.toHaveBeenCalled();
  });

  // --- Form field onChange handlers ---

  it("calls onUpdateField when prompt textarea changes", () => {
    const onUpdateField = vi.fn();
    render(<ScheduleCard {...defaultProps({ showScheduleForm: true, onUpdateField })} />);
    fireEvent.change(screen.getByPlaceholderText("Update documentation..."), {
      target: { value: "Fix all bugs" },
    });
    expect(onUpdateField).toHaveBeenCalledWith("prompt", "Fix all bugs");
  });

  it("calls onUpdateField when backend select changes", () => {
    const onUpdateField = vi.fn();
    render(<ScheduleCard {...defaultProps({ showScheduleForm: true, onUpdateField })} />);
    // Open advanced settings first
    fireEvent.click(screen.getByText("Advanced settings"));
    const backendSelect = screen.getByDisplayValue("claudecodecli");
    fireEvent.change(backendSelect, { target: { value: "e2e" } });
    expect(onUpdateField).toHaveBeenCalledWith("backend", "e2e");
  });

  it("calls onUpdateField when model input changes", () => {
    const onUpdateField = vi.fn();
    render(<ScheduleCard {...defaultProps({ showScheduleForm: true, onUpdateField })} />);
    fireEvent.click(screen.getByText("Advanced settings"));
    const modelInput = screen.getByPlaceholderText("claude-opus-4-6");
    fireEvent.change(modelInput, { target: { value: "gpt-5.2" } });
    expect(onUpdateField).toHaveBeenCalledWith("model", "gpt-5.2");
  });

  it("calls onUpdateField with clamped max_iterations", () => {
    const onUpdateField = vi.fn();
    render(<ScheduleCard {...defaultProps({ showScheduleForm: true, onUpdateField })} />);
    fireEvent.click(screen.getByText("Advanced settings"));
    const iterInput = screen.getByDisplayValue("6");
    fireEvent.change(iterInput, { target: { value: "0" } });
    expect(onUpdateField).toHaveBeenCalledWith("max_iterations", 1);
  });

  it("calls onUpdateField with valid max_iterations value", () => {
    const onUpdateField = vi.fn();
    render(<ScheduleCard {...defaultProps({ showScheduleForm: true, onUpdateField })} />);
    fireEvent.click(screen.getByText("Advanced settings"));
    const iterInput = screen.getByDisplayValue("6");
    fireEvent.change(iterInput, { target: { value: "10" } });
    expect(onUpdateField).toHaveBeenCalledWith("max_iterations", 10);
  });

  it("calls onUpdateField when PR number input changes", () => {
    const onUpdateField = vi.fn();
    render(<ScheduleCard {...defaultProps({ showScheduleForm: true, onUpdateField })} />);
    fireEvent.click(screen.getByText("Advanced settings"));
    const prInput = screen.getByRole("spinbutton", { name: /pr number/i });
    fireEvent.change(prInput, { target: { value: "42" } });
    expect(onUpdateField).toHaveBeenCalledWith("pr_number", "42");
  });

  it("calls onUpdateField when tools input changes", () => {
    const onUpdateField = vi.fn();
    render(<ScheduleCard {...defaultProps({ showScheduleForm: true, onUpdateField })} />);
    fireEvent.click(screen.getByText("Advanced settings"));
    fireEvent.change(screen.getByPlaceholderText("execution,web"), {
      target: { value: "execution" },
    });
    expect(onUpdateField).toHaveBeenCalledWith("tools", "execution");
  });

  it("calls onUpdateField when skills input changes", () => {
    const onUpdateField = vi.fn();
    render(<ScheduleCard {...defaultProps({ showScheduleForm: true, onUpdateField })} />);
    fireEvent.click(screen.getByText("Advanced settings"));
    fireEvent.change(screen.getByPlaceholderText("execution,web,prd"), {
      target: { value: "prd" },
    });
    expect(onUpdateField).toHaveBeenCalledWith("skills", "prd");
  });

  it("calls onUpdateField when github token input changes", () => {
    const onUpdateField = vi.fn();
    render(<ScheduleCard {...defaultProps({ showScheduleForm: true, onUpdateField })} />);
    fireEvent.click(screen.getByText("Advanced settings"));
    fireEvent.change(screen.getByPlaceholderText("ghp_... (optional)"), {
      target: { value: "ghp_abc123" },
    });
    expect(onUpdateField).toHaveBeenCalledWith("github_token", "ghp_abc123");
  });

  // --- Checkbox toggles ---

  it("calls onUpdateField with no_pr when No PR checkbox toggled", () => {
    const onUpdateField = vi.fn();
    render(<ScheduleCard {...defaultProps({ showScheduleForm: true, onUpdateField })} />);
    fireEvent.click(screen.getByText("Advanced settings"));
    fireEvent.click(screen.getByRole("checkbox", { name: /no pr/i }));
    expect(onUpdateField).toHaveBeenCalledWith("no_pr", true);
  });

  it("calls onUpdateField with enable_execution when Execution checkbox toggled", () => {
    const onUpdateField = vi.fn();
    render(<ScheduleCard {...defaultProps({ showScheduleForm: true, onUpdateField })} />);
    fireEvent.click(screen.getByText("Advanced settings"));
    fireEvent.click(screen.getByRole("checkbox", { name: /execution/i }));
    expect(onUpdateField).toHaveBeenCalledWith("enable_execution", true);
  });

  it("calls onUpdateField with enable_web when Web checkbox toggled", () => {
    const onUpdateField = vi.fn();
    render(<ScheduleCard {...defaultProps({ showScheduleForm: true, onUpdateField })} />);
    fireEvent.click(screen.getByText("Advanced settings"));
    fireEvent.click(screen.getByRole("checkbox", { name: /^web$/i }));
    expect(onUpdateField).toHaveBeenCalledWith("enable_web", true);
  });

  it("calls onUpdateField with fix_ci when Fix CI checkbox toggled", () => {
    const onUpdateField = vi.fn();
    render(<ScheduleCard {...defaultProps({ showScheduleForm: true, onUpdateField })} />);
    fireEvent.click(screen.getByText("Advanced settings"));
    fireEvent.click(screen.getByRole("checkbox", { name: /fix ci/i }));
    expect(onUpdateField).toHaveBeenCalledWith("fix_ci", true);
  });

  it("calls onUpdateField with enabled when Enabled checkbox toggled", () => {
    const onUpdateField = vi.fn();
    render(<ScheduleCard {...defaultProps({ showScheduleForm: true, onUpdateField })} />);
    fireEvent.click(screen.getByText("Advanced settings"));
    fireEvent.click(screen.getByRole("checkbox", { name: /^enabled$/i }));
    // Initial form has enabled: true, so toggling it should call with false
    expect(onUpdateField).toHaveBeenCalledWith("enabled", false);
  });

  // --- Advanced settings details toggle ---

  it("renders advanced fields inside a details/summary element", () => {
    render(<ScheduleCard {...defaultProps({ showScheduleForm: true })} />);
    const details = screen.getByText("Advanced settings").closest("details");
    expect(details).toBeInTheDocument();
  });

  // --- Schedule item edge cases ---

  it("omits next run time when next_run_at is null", () => {
    const schedule = { ...MOCK_SCHEDULE, next_run_at: null };
    render(<ScheduleCard {...defaultProps({ schedules: [schedule] })} />);
    expect(screen.queryByText(/next:/)).not.toBeInTheDocument();
  });

  it("omits last run time when last_run_at is null", () => {
    const schedule = { ...MOCK_SCHEDULE, last_run_at: null };
    render(<ScheduleCard {...defaultProps({ schedules: [schedule] })} />);
    expect(screen.queryByText(/last:/)).not.toBeInTheDocument();
  });

  it("renders multiple schedule items", () => {
    const second: ScheduleItem = {
      ...MOCK_SCHEDULE,
      schedule_id: "sched-2",
      name: "Weekly Deploy",
      cron_expression: "0 0 * * 0",
      enabled: false,
    };
    render(<ScheduleCard {...defaultProps({ schedules: [MOCK_SCHEDULE, second] })} />);
    expect(screen.getByText("Nightly Build")).toBeInTheDocument();
    expect(screen.getByText("Weekly Deploy")).toBeInTheDocument();
    expect(screen.getByText("enabled")).toBeInTheDocument();
    expect(screen.getByText("disabled")).toBeInTheDocument();
  });

  it("hides empty message when schedules exist", () => {
    render(<ScheduleCard {...defaultProps({ schedules: [MOCK_SCHEDULE] })} />);
    expect(screen.queryByText("No scheduled tasks yet.")).not.toBeInTheDocument();
  });

  // --- Reference repos chip integration ---

  it("parses reference_repos string into chips in the form", () => {
    const onUpdateField = vi.fn();
    render(
      <ScheduleCard
        {...defaultProps({
          showScheduleForm: true,
          scheduleForm: {
            ...INITIAL_SCHEDULE_FORM,
            reference_repos: "org/repo-a, org/repo-b",
          },
          onUpdateField,
        })}
      />,
    );
    fireEvent.click(screen.getByText("Advanced settings"));
    // Chips should be rendered for each parsed repo
    expect(screen.getByText("org/repo-a")).toBeInTheDocument();
    expect(screen.getByText("org/repo-b")).toBeInTheDocument();
  });

  it("renders empty chips when reference_repos is empty string", () => {
    render(
      <ScheduleCard
        {...defaultProps({
          showScheduleForm: true,
          scheduleForm: { ...INITIAL_SCHEDULE_FORM, reference_repos: "" },
        })}
      />,
    );
    fireEvent.click(screen.getByText("Advanced settings"));
    // No chip elements should appear (empty string → no chips)
    const chipInput = screen.getByLabelText("Schedule reference repos");
    expect(chipInput).toBeInTheDocument();
  });
});
