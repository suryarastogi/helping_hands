# v296: Extract TaskListSidebar Component

**Date:** 2026-03-23
**Theme:** Frontend code quality — component extraction

## Goal

Extract the `<aside className="card task-list-card">` block (~80 lines) from
`App.tsx` into a dedicated `TaskListSidebar` component. This is the left-hand
sidebar containing the view toggle, navigation buttons, and submitted task list.

## Steps

1. Create `frontend/src/components/TaskListSidebar.tsx` with typed props
2. Move the sidebar JSX from App.tsx into the new component
3. Create `frontend/src/components/TaskListSidebar.test.tsx` with render tests
4. Update `docs/FRONTEND.md` component listing
5. Run tests, lint, typecheck

## Props interface

```typescript
type TaskListSidebarProps = {
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
```

## Acceptance criteria

- App.tsx line count decreases by ~80 lines
- All existing frontend tests pass (398+)
- New component has ≥80% coverage
- FRONTEND.md updated
