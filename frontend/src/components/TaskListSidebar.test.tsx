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
    dashboardView: "classic",
    onDashboardViewChange: vi.fn(),
    mainView: "submission",
    onNewSubmission: vi.fn(),
    onShowSchedules: vi.fn(),
    taskHistory: [],
    selectedTaskId: null,
    onSelectTask: vi.fn(),
    onClearHistory: vi.fn(),
    ...overrides,
  };
}

describe("TaskListSidebar", () => {
  it("renders view toggle with classic and world buttons", () => {
    render(<TaskListSidebar {...defaultProps()} />);
    expect(screen.getByRole("tab", { name: "Classic view" })).toBeDefined();
    expect(screen.getByRole("tab", { name: "Hand world" })).toBeDefined();
  });

  it("marks classic view tab as active when dashboardView is classic", () => {
    render(<TaskListSidebar {...defaultProps({ dashboardView: "classic" })} />);
    const classicTab = screen.getByRole("tab", { name: "Classic view" });
    expect(classicTab.getAttribute("aria-selected")).toBe("true");
    expect(classicTab.className).toContain("active");
  });

  it("marks world view tab as active when dashboardView is world", () => {
    render(<TaskListSidebar {...defaultProps({ dashboardView: "world" })} />);
    const worldTab = screen.getByRole("tab", { name: "Hand world" });
    expect(worldTab.getAttribute("aria-selected")).toBe("true");
    expect(worldTab.className).toContain("active");
  });

  it("calls onDashboardViewChange when toggling views", () => {
    const onDashboardViewChange = vi.fn();
    render(<TaskListSidebar {...defaultProps({ onDashboardViewChange })} />);
    fireEvent.click(screen.getByRole("tab", { name: "Hand world" }));
    expect(onDashboardViewChange).toHaveBeenCalledWith("world");
  });

  it("renders New submission and Scheduled tasks buttons", () => {
    render(<TaskListSidebar {...defaultProps()} />);
    expect(screen.getByText("New submission")).toBeDefined();
    expect(screen.getByText("Scheduled tasks")).toBeDefined();
  });

  it("calls onNewSubmission when clicking New submission", () => {
    const onNewSubmission = vi.fn();
    render(<TaskListSidebar {...defaultProps({ onNewSubmission })} />);
    fireEvent.click(screen.getByText("New submission"));
    expect(onNewSubmission).toHaveBeenCalledOnce();
  });

  it("calls onShowSchedules when clicking Scheduled tasks", () => {
    const onShowSchedules = vi.fn();
    render(<TaskListSidebar {...defaultProps({ onShowSchedules })} />);
    fireEvent.click(screen.getByText("Scheduled tasks"));
    expect(onShowSchedules).toHaveBeenCalledOnce();
  });

  it("marks New submission button active in classic submission view", () => {
    render(<TaskListSidebar {...defaultProps({ dashboardView: "classic", mainView: "submission" })} />);
    const btn = screen.getByText("New submission");
    expect(btn.className).toContain("active");
  });

  it("does not mark New submission active in world view", () => {
    render(<TaskListSidebar {...defaultProps({ dashboardView: "world", mainView: "submission" })} />);
    const btn = screen.getByText("New submission");
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
