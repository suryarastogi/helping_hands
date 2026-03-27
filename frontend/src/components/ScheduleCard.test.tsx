import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";

import ScheduleCard, { type ScheduleCardProps } from "./ScheduleCard";
import { BACKEND_OPTIONS, INITIAL_SCHEDULE_FORM } from "../App.utils";
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
  project_management: false,
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
});
