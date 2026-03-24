import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";

import TaskListSidebar, { type TaskListSidebarProps } from "./TaskListSidebar";
import type { TaskHistoryItem } from "../types";

afterEach(cleanup);

const MOCK_TASK: TaskHistoryItem = {
  taskId: "abc-123-def-456",
  status: "SUCCESS",
  backend: "claudecodecli",
  repoPath: "owner/repo",
  lastUpdatedAt: new Date("2026-03-23T12:00:00Z").getTime(),
};

function defaultProps(overrides?: Partial<TaskListSidebarProps>): TaskListSidebarProps {
  return {
    mainView: "submission",
    showSubmissionOverlay: false,
    onNewSubmission: vi.fn(),
    onToggleSchedules: vi.fn(),
    taskHistory: [],
    selectedTaskId: null,
    onSelectTask: vi.fn(),
    onClearHistory: vi.fn(),
    ...overrides,
  };
}

describe("TaskListSidebar", () => {
  it("renders New Task and Scheduled tasks buttons", () => {
    render(<TaskListSidebar {...defaultProps()} />);
    expect(screen.getByText("New Task")).toBeDefined();
    expect(screen.getByText("Scheduled tasks")).toBeDefined();
  });

  it("calls onNewSubmission when clicking New Task", () => {
    const onNewSubmission = vi.fn();
    render(<TaskListSidebar {...defaultProps({ onNewSubmission })} />);
    fireEvent.click(screen.getByText("New Task"));
    expect(onNewSubmission).toHaveBeenCalledOnce();
  });

  it("calls onToggleSchedules when clicking Scheduled tasks", () => {
    const onToggleSchedules = vi.fn();
    render(<TaskListSidebar {...defaultProps({ onToggleSchedules })} />);
    fireEvent.click(screen.getByText("Scheduled tasks"));
    expect(onToggleSchedules).toHaveBeenCalledOnce();
  });

  it("marks New Task button active when overlay is open", () => {
    render(<TaskListSidebar {...defaultProps({ showSubmissionOverlay: true })} />);
    const btn = screen.getByText("New Task");
    expect(btn.className).toContain("active");
  });

  it("does not mark New Task active when overlay is closed", () => {
    render(<TaskListSidebar {...defaultProps({ showSubmissionOverlay: false })} />);
    const btn = screen.getByText("New Task");
    expect(btn.className).not.toContain("active");
  });

  it("marks Scheduled tasks button active when mainView is schedules", () => {
    render(<TaskListSidebar {...defaultProps({ mainView: "schedules" })} />);
    const btn = screen.getByText("Scheduled tasks");
    expect(btn.className).toContain("active");
  });

  it("shows empty message when no tasks exist", () => {
    render(<TaskListSidebar {...defaultProps()} />);
    expect(screen.getByText("No tasks submitted yet.")).toBeDefined();
  });

  it("disables Clear button when no tasks exist", () => {
    render(<TaskListSidebar {...defaultProps()} />);
    const clearBtn = screen.getByText("Clear");
    expect((clearBtn as HTMLButtonElement).disabled).toBe(true);
  });

  it("renders task list items with status pills", () => {
    render(<TaskListSidebar {...defaultProps({ taskHistory: [MOCK_TASK] })} />);
    expect(screen.getByText("SUCCESS")).toBeDefined();
    expect(screen.getByText(/owner\/repo/)).toBeDefined();
  });

  it("calls onSelectTask when clicking a task row", () => {
    const onSelectTask = vi.fn();
    render(<TaskListSidebar {...defaultProps({ taskHistory: [MOCK_TASK], onSelectTask })} />);
    fireEvent.click(screen.getByTitle("abc-123-def-456"));
    expect(onSelectTask).toHaveBeenCalledWith("abc-123-def-456");
  });

  it("marks selected task row as active", () => {
    render(<TaskListSidebar {...defaultProps({ taskHistory: [MOCK_TASK], selectedTaskId: "abc-123-def-456" })} />);
    const row = screen.getByTitle("abc-123-def-456");
    expect(row.className).toContain("active");
  });

  it("calls onClearHistory when clicking Clear", () => {
    const onClearHistory = vi.fn();
    render(<TaskListSidebar {...defaultProps({ taskHistory: [MOCK_TASK], onClearHistory })} />);
    fireEvent.click(screen.getByText("Clear"));
    expect(onClearHistory).toHaveBeenCalledOnce();
  });

  it("enables Clear button when tasks exist", () => {
    render(<TaskListSidebar {...defaultProps({ taskHistory: [MOCK_TASK] })} />);
    const clearBtn = screen.getByText("Clear");
    expect((clearBtn as HTMLButtonElement).disabled).toBe(false);
  });

  it("shows 'manual' when task has no repoPath", () => {
    const task: TaskHistoryItem = { ...MOCK_TASK, repoPath: undefined };
    render(<TaskListSidebar {...defaultProps({ taskHistory: [task] })} />);
    expect(screen.getByText(/manual/)).toBeDefined();
  });
});
