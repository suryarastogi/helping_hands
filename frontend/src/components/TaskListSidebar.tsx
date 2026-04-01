import type { MainView, TaskHistoryItem } from "../types";
import { shortTaskId, statusTone } from "../App.utils";

export type TaskListSidebarProps = {
  mainView: MainView;
  showSubmissionOverlay: boolean;
  onNewSubmission: () => void;
  onToggleSchedules: () => void;
  onStartTutorial: () => void;
  taskHistory: TaskHistoryItem[];
  selectedTaskId: string | null;
  onSelectTask: (taskId: string) => void;
  onClearHistory: () => void;
  collapsed: boolean;
  onToggleCollapsed: () => void;
};

export default function TaskListSidebar({
  mainView,
  showSubmissionOverlay,
  onNewSubmission,
  onToggleSchedules,
  onStartTutorial,
  taskHistory,
  selectedTaskId,
  onSelectTask,
  onClearHistory,
  collapsed,
  onToggleCollapsed,
}: TaskListSidebarProps) {
  return (
    <aside className={`card task-list-card${collapsed ? " collapsed" : ""}`}>
      <button
        type="button"
        className="sidebar-collapse-btn"
        onClick={onToggleCollapsed}
        aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        aria-expanded={!collapsed}
        title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
      >
        {collapsed ? "\u203A" : "\u2039"}
      </button>

      {collapsed ? (
        <div className="sidebar-collapsed-label">Tasks</div>
      ) : (
        <>
          <button
            type="button"
            className={`new-submission-button${showSubmissionOverlay ? " active" : ""}`}
            onClick={onNewSubmission}
          >
            New Task
          </button>
          <button
            type="button"
            className={`new-submission-button${
              mainView === "schedules" ? " active" : ""
            }`}
            style={{ marginTop: 0 }}
            onClick={onToggleSchedules}
          >
            Scheduled tasks
          </button>
          <button
            type="button"
            className="tutorial-button"
            onClick={onStartTutorial}
          >
            Tutorial
          </button>
          <div className="task-list-header">
            <h2>Submitted tasks</h2>
            <button
              type="button"
              className="text-button"
              disabled={taskHistory.length === 0}
              onClick={onClearHistory}
            >
              Clear
            </button>
          </div>
          {taskHistory.length === 0 ? (
            <p className="empty-list">No tasks submitted yet.</p>
          ) : (
            <ul className="task-list">
              {taskHistory.map((item) => (
                <li key={item.taskId}>
                  <button
                    type="button"
                    className={`task-row${selectedTaskId === item.taskId ? " active" : ""}`}
                    onClick={() => onSelectTask(item.taskId)}
                    title={item.taskId}
                  >
                    <span className="task-row-top">
                      <code>{shortTaskId(item.taskId)}</code>
                      <span className={`status-pill ${statusTone(item.status)}`}>
                        {item.status}
                      </span>
                    </span>
                    <span className="task-row-meta">
                      {item.backend} • {item.repoPath || "manual"} •{" "}
                      {new Date(item.lastUpdatedAt).toLocaleTimeString()}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </aside>
  );
}
