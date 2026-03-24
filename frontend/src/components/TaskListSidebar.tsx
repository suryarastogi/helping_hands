import type { MainView, TaskHistoryItem } from "../types";
import { shortTaskId, statusTone } from "../App.utils";

export type TaskListSidebarProps = {
  mainView: MainView;
  showSubmissionOverlay: boolean;
  onNewSubmission: () => void;
  onShowSchedules: () => void;
  taskHistory: TaskHistoryItem[];
  selectedTaskId: string | null;
  onSelectTask: (taskId: string) => void;
  onClearHistory: () => void;
};

export default function TaskListSidebar({
  mainView,
  showSubmissionOverlay,
  onNewSubmission,
  onShowSchedules,
  taskHistory,
  selectedTaskId,
  onSelectTask,
  onClearHistory,
}: TaskListSidebarProps) {
  return (
    <aside className="card task-list-card">
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
