import type { DashboardView, MainView, TaskHistoryItem } from "../types";
import { shortTaskId, statusTone } from "../App.utils";

export type TaskListSidebarProps = {
  dashboardView: DashboardView;
  onDashboardViewChange: (view: DashboardView) => void;
  mainView: MainView;
  onNewSubmission: () => void;
  onShowSchedules: () => void;
  taskHistory: TaskHistoryItem[];
  selectedTaskId: string | null;
  onSelectTask: (taskId: string) => void;
  onClearHistory: () => void;
};

export default function TaskListSidebar({
  dashboardView,
  onDashboardViewChange,
  mainView,
  onNewSubmission,
  onShowSchedules,
  taskHistory,
  selectedTaskId,
  onSelectTask,
  onClearHistory,
}: TaskListSidebarProps) {
  return (
    <aside className="card task-list-card">
      <div className="view-toggle" role="tablist" aria-label="Dashboard view">
        <button
          type="button"
          role="tab"
          className={`view-toggle-btn${dashboardView === "classic" ? " active" : ""}`}
          aria-selected={dashboardView === "classic"}
          onClick={() => onDashboardViewChange("classic")}
        >
          Classic view
        </button>
        <button
          type="button"
          role="tab"
          className={`view-toggle-btn${dashboardView === "world" ? " active" : ""}`}
          aria-selected={dashboardView === "world"}
          onClick={() => onDashboardViewChange("world")}
        >
          Hand world
        </button>
      </div>
      <button
        type="button"
        className={`new-submission-button${
          dashboardView === "classic" && mainView === "submission" ? " active" : ""
        }`}
        onClick={onNewSubmission}
      >
        New submission
      </button>
      <button
        type="button"
        className={`new-submission-button${
          mainView === "schedules" ? " active" : ""
        }`}
        style={{ marginTop: 0 }}
        onClick={onShowSchedules}
      >
        Scheduled tasks
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
    </aside>
  );
}
