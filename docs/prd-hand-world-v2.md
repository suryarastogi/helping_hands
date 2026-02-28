# PRD: Hand World v2 — Richer Agent Visibility

**Status:** Draft
**Author:** Auto-generated
**Date:** 2026-02-28

---

## 1. Problem Statement

Hand World is a compelling "agent office" visualization that shows AI agents as animated sprites working at virtual desks. However, the current implementation surfaces only a thin slice of the runtime data that the system already collects. Users watching Hand World today can see *that* agents are busy, but not *what* they are doing, *how far* they have progressed, or *how well* things went. This gap limits Hand World's value as an operational dashboard and makes it feel more like a novelty screensaver than a useful monitoring tool.

### What users report wanting

- "Which repo is that agent working on?"
- "How many iterations has it completed?"
- "Did it finish successfully or fail?"
- "What files did it change?"
- "How long has it been running?"

All of this data already flows through the server — it just never reaches the UI.

---

## 2. Goals

| # | Goal | Success Metric |
|---|------|----------------|
| G1 | Surface iteration progress per agent in real time | Users can see "iteration 3/6" without leaving the world view |
| G2 | Display task context (repo, model, prompt) at a glance | Each desk shows repo name and model without requiring hover |
| G3 | Communicate task outcome visually | Workers visually reflect success/failure/interrupted states |
| G4 | Show elapsed time and duration | Running timer visible per desk; completed tasks show total duration |
| G5 | Provide drill-down without leaving the world | Clicking/interacting with a worker shows a details panel inside the world view |
| G6 | Surface tool activity in real time | Users can see when agents read files, run commands, or search the web |

---

## 3. Non-Goals

- Replacing the classic dashboard view. Hand World v2 augments monitoring — the classic table view remains the primary operational UI.
- Real-time log streaming within world view. Full log tailing stays in the classic view; the world shows summarized progress.
- Mobile-optimized layout. Hand World targets desktop browsers with ≥ 1280 px width.

---

## 4. Current State Analysis

### Data already captured by the backend

| Data Point | Backend Source | Currently Displayed in World? |
|------------|---------------|-------------------------------|
| Task ID | `/tasks/current` | Tooltip only |
| Backend name | `/tasks/current` → `backend` | Tooltip + sprite color |
| Status (PENDING → SUCCESS) | `/tasks/current` → `status` | Phase animation only |
| Repo path | `/tasks/current` → `repo_path` | Not shown |
| Celery worker name | `/tasks/current` → `worker` | Not shown |
| Model | Celery PROGRESS state → `model` | Not shown |
| Prompt | Celery PROGRESS state → `prompt` | Not shown |
| Iterations completed | Celery PROGRESS state → `iterations` | Not shown |
| Max iterations | Celery PROGRESS state → `max_iterations` | Not shown |
| Streaming updates | Celery PROGRESS state → `updates` | Not shown (classic view only) |
| PR status/URL | HandResponse metadata | Not shown |
| Tool executions | Stream content parsing | Not shown |
| Creation timestamp | `TaskHistoryItem.createdAt` | Not shown |
| Last update timestamp | `TaskHistoryItem.lastUpdatedAt` | Not shown |
| Skills enabled | Celery PROGRESS state → `skills` | Not shown |

### Takeaway

The server already pushes iteration counts, model names, repo paths, and streaming updates into Celery task state every 8 stream chunks. The frontend polls `/tasks/current` every 10 seconds but discards most of this data. **The primary work is frontend rendering**, not backend instrumentation.

---

## 5. Proposed Features

### 5.1 Desk Nameplates

**Priority: P0** — Minimal effort, high impact

Each occupied desk gets a small "nameplate" overlay directly below or above the desk sprite.

**Content:**
- **Line 1:** Repo short name (last segment of `repo_path`, e.g., `my-app`)
- **Line 2:** Model badge (e.g., `gpt-5.2` or `claude-opus-4.6`, abbreviated to fit)

**Design notes:**
- Font: 9 px monospace, max-width equal to desk width (truncate with ellipsis)
- Appears with a fade after the worker transitions from `arriving` → `active`
- Disappears during `leaving` phase

### 5.2 Iteration Progress Ring

**Priority: P0**

A thin circular progress indicator around each worker sprite (or beneath the desk) showing `current_iteration / max_iterations`.

**Behavior:**
- Ring fills proportionally: 2/6 → 33% filled
- Color: provider accent color
- Numeric label centered: `2/6`
- When status is `"satisfied"` before max_iterations, ring fills completely and turns green
- If max_iterations is unknown or not applicable (CLI hands), show a pulsing dot instead

**Data source:** Extend `/tasks/current` response to include `iterations` and `max_iterations` fields from Celery task PROGRESS state. These fields are already stored — they just need to be forwarded in the API response.

### 5.3 Elapsed Time Badge

**Priority: P1**

Each active desk shows a small running timer: `2m 34s`.

**Behavior:**
- Calculated client-side from `createdAt` timestamp (already tracked in `TaskHistoryItem`)
- Renders below the progress ring
- On completion, timer freezes and shows total elapsed time for 5 seconds before the worker leaves

### 5.4 Outcome Animations

**Priority: P1**

When a task transitions from active to a terminal state, the worker sprite plays a brief outcome animation before entering the `leaving` phase:

| Outcome | Animation | Duration |
|---------|-----------|----------|
| SUCCESS | Worker does a small "celebration" bounce; green checkmark appears above head | 1.5 s |
| FAILURE | Worker shows red X above head; sprite briefly turns red-tinted | 1.5 s |
| REVOKED / interrupted | Worker shows yellow caution icon; shrug animation | 1.0 s |

After the animation completes, the existing `leaving` slide-out plays.

### 5.5 Activity Pulse

**Priority: P1** — Surface tool activity

A small speech-bubble or status-line above the worker's head shows the latest activity in 1–2 words:

| Event | Bubble Text |
|-------|-------------|
| Reading a file | `reading utils.py` |
| Writing/editing a file | `editing app.tsx` |
| Running a command | `running tests` |
| Searching the web | `web search` |
| Thinking / generating | `thinking...` |
| Idle between iterations | `iteration 3 done` |

**Data source:** Parse the latest entry from the `updates` array in PROGRESS state. The existing `_UpdateCollector` already line-buffers chunks — heuristics on `@@READ`, `@@FILE`, `@@CMD`, `@@WEB_SEARCH` prefixes can classify the activity.

**Design notes:**
- Max width: 120 px, text truncated with ellipsis
- Fade-in/out on change, auto-hide after 4 seconds of no updates
- Position: floating above the worker sprite's head

### 5.6 Worker Detail Panel

**Priority: P2**

Clicking a worker sprite (or walking the player character into a desk's collision zone and pressing Enter/Space) opens a slide-in panel on the right side of the world view.

**Panel contents:**

```
┌──────────────────────────────────────┐
│  Task abc123                    [X]  │
│                                      │
│  Repo:       suryarastogi/my-app     │
│  Backend:    basic-langgraph         │
│  Model:      gpt-5.2                │
│  Status:     RUNNING                 │
│  Prompt:     "Add dark mode..."      │
│                                      │
│  Progress    ████████░░░░  3/6       │
│  Elapsed     4m 12s                  │
│  Skills      web, execution          │
│                                      │
│  Recent Activity                     │
│  ─────────────────                   │
│  • Edited src/theme.ts               │
│  • Read package.json                 │
│  • Ran `npm test` (exit 0)           │
│                                      │
│  [View Full Log]  [Cancel Task]      │
└──────────────────────────────────────┘
```

**Behavior:**
- "View Full Log" switches to classic view filtered to this task
- "Cancel Task" calls `POST /tasks/{task_id}/revoke`
- Panel auto-updates every poll cycle (10 s)

### 5.7 Office Status Bar

**Priority: P2**

A persistent horizontal bar at the top or bottom of the world view showing aggregate office status:

```
 Workers: 3/8 active  |  Success: 12  Failures: 2  |  Avg runtime: 4m 30s  |  Queue: 1 pending
```

**Data source:** Computed from `taskHistory` state + `/workers/capacity` endpoint.

### 5.8 Completed Task Graveyard / Trophy Wall

**Priority: P3** — Fun polish

A designated area in the office (right wall) showing small icons for recently completed tasks:
- Green trophy for successes
- Red X for failures
- Hover shows task ID + repo + duration
- Last 20 tasks displayed

---

## 6. API Changes Required

### 6.1 Extend `CurrentTask` model

```python
class CurrentTask(BaseModel):
    task_id: str
    status: str
    backend: str | None = None
    repo_path: str | None = None
    worker: str | None = None
    source: str
    # --- NEW FIELDS ---
    model: str | None = None
    prompt: str | None = None          # First 200 chars
    iterations: int | None = None
    max_iterations: int | None = None
    latest_update: str | None = None   # Last line from updates[]
    created_at: float | None = None    # Unix timestamp
    skills: list[str] | None = None
```

**Implementation:** The `_fetch_flower_current_tasks` and `_collect_celery_current_tasks` functions already parse `kwargs` from Celery task state. Extracting these additional fields requires reading from the task's `info` dict (PROGRESS state), which is already fetched for status determination.

### 6.2 New endpoint: `GET /tasks/{task_id}/activity`

Returns the last N parsed activity events for a task (file reads, writes, command runs).

```python
class ActivityEvent(BaseModel):
    type: str            # "read", "write", "command", "web_search", "web_browse"
    target: str          # filename, command, or URL
    timestamp: float
    status: str | None   # "success", "failure" for commands

class TaskActivityResponse(BaseModel):
    task_id: str
    events: list[ActivityEvent]
```

**Implementation:** Parse the `updates` list stored in Celery PROGRESS state. The `@@READ`, `@@FILE`, `@@CMD`, `@@WEB_SEARCH` markers are already in the stream content.

---

## 7. Frontend Changes Required

### 7.1 State Changes (`App.tsx`)

```typescript
// Extend TaskHistoryItem
type TaskHistoryItem = {
  taskId: string;
  status: string;
  backend: string;
  repoPath: string;
  createdAt: number;
  lastUpdatedAt: number;
  // --- NEW ---
  model: string | null;
  prompt: string | null;
  iterations: number | null;
  maxIterations: number | null;
  latestUpdate: string | null;
  skills: string[] | null;
};

// New state for selected worker panel
const [selectedWorkerId, setSelectedWorkerId] = useState<string | null>(null);
```

### 7.2 New Components

| Component | Purpose | Priority |
|-----------|---------|----------|
| `DeskNameplate` | Repo name + model label below desk | P0 |
| `ProgressRing` | SVG circular progress for iterations | P0 |
| `ElapsedTimer` | Client-side running clock | P1 |
| `ActivityBubble` | Floating activity text above worker | P1 |
| `OutcomeOverlay` | Success/failure/revoked animation | P1 |
| `WorkerDetailPanel` | Slide-in detail view | P2 |
| `OfficeStatusBar` | Aggregate stats bar | P2 |
| `TrophyWall` | Completed task icons | P3 |

### 7.3 Polling Frequency

Current: 10-second poll interval for `/tasks/current`.

**Recommendation:** Reduce to 5 seconds for Hand World view (activity bubbles and progress rings feel stale at 10 s). Alternatively, add a WebSocket channel for push-based updates (larger effort, P3).

---

## 8. Implementation Phases

### Phase 1 — Foundation (P0)

**Scope:** Desk Nameplates + Progress Ring
**Backend:** Extend `CurrentTask` with `model`, `iterations`, `max_iterations`, `repo_path` forwarding
**Frontend:** Two new overlay components rendered per-desk
**Estimated complexity:** Small — mostly wiring existing data through

### Phase 2 — Activity & Outcome (P1)

**Scope:** Elapsed Timer + Outcome Animations + Activity Pulse
**Backend:** Forward `latest_update` and `created_at` in `CurrentTask`
**Frontend:** Three new components, activity-parsing heuristic, animation sprites
**Estimated complexity:** Medium — activity parsing and animations require iteration

### Phase 3 — Drill-Down & Dashboard (P2)

**Scope:** Worker Detail Panel + Office Status Bar
**Backend:** New `/tasks/{task_id}/activity` endpoint
**Frontend:** Panel component with interaction handling (click + player proximity)
**Estimated complexity:** Medium — panel layout, player interaction detection, activity API

### Phase 4 — Polish & Delight (P3)

**Scope:** Trophy Wall + WebSocket push updates
**Backend:** WebSocket channel for task state changes
**Frontend:** Trophy rendering, WebSocket client, reduced polling
**Estimated complexity:** Large — WebSocket infrastructure is new plumbing

---

## 9. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Polling `/tasks/current` more frequently overloads Flower/Celery | Backend strain at scale | Cache Flower responses server-side with 3 s TTL; only increase poll rate in Hand World view |
| Activity parsing heuristics misclassify stream content | Wrong activity labels shown | Use explicit `@@` markers already in the stream; fall back to "working..." for unrecognized content |
| Too much visual clutter makes the world hard to read | UX regression | Gate overlays behind a "detail level" toggle (minimal / standard / verbose); default to standard |
| Large offices (20+ desks) make nameplates unreadable | Scaling issues | Scale font size with desk count; switch to icon-only mode above 16 desks |
| WebSocket channel (Phase 4) adds operational complexity | Harder deployment | Keep HTTP polling as fallback; WebSocket is purely additive |

---

## 10. Open Questions

1. **Player interaction model:** Should clicking a desk open the detail panel, or should the player character need to "walk up" to the desk? Walking up is more immersive but clicking is more practical.
2. **Sound effects:** Should outcome animations have optional sound effects (success chime, error buzz)? This could enhance the experience but may be annoying in an office setting.
3. **Multi-user presence:** If multiple users have Hand World open, should they see each other's player characters? This is a significant scope increase but could make Hand World feel more alive.
4. **Historical replay:** Should completed tasks be replayable in the world view (watching a time-lapse of agents working)? Interesting but very high effort.

---

## 11. Appendix: Data Flow Diagram

```
                   ┌─────────────────────────┐
                   │   Celery Worker          │
                   │                          │
                   │  build_feature() task    │
                   │    ↓                     │
                   │  hand.stream(prompt)     │
                   │    ↓                     │
                   │  _UpdateCollector.feed() │
                   │    ↓                     │
                   │  _update_progress()      │──── task.update_state(
                   │    (every 8 chunks)      │       meta={iterations,
                   │                          │             model, updates,
                   └──────────┬───────────────┘             max_iterations,
                              │                             prompt, ...})
                              ▼
                   ┌─────────────────────────┐
                   │   Celery Result Backend  │
                   │   (Redis / RabbitMQ)     │
                   └──────────┬───────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼                               ▼
   ┌──────────────────┐            ┌──────────────────┐
   │  Flower API      │            │  Celery Inspect  │
   │  /api/tasks      │            │  .active()       │
   └────────┬─────────┘            └────────┬─────────┘
            │                               │
            └───────────┬───────────────────┘
                        ▼
             ┌──────────────────────┐
             │  /tasks/current      │
             │  (extended response) │
             │                      │
             │  {task_id, status,   │
             │   backend, model,    │  ◄── NEW: iterations,
             │   repo_path,         │      max_iterations,
             │   iterations,        │      model, prompt,
             │   max_iterations,    │      latest_update
             │   latest_update,     │
             │   ...}               │
             └──────────┬───────────┘
                        │
                        ▼
             ┌──────────────────────┐
             │  Frontend (10s poll) │
             │                      │
             │  ┌────────────────┐  │
             │  │ Desk Nameplate │  │  ◄── repo + model
             │  ├────────────────┤  │
             │  │ Progress Ring  │  │  ◄── iterations / max
             │  ├────────────────┤  │
             │  │ Activity Bubble│  │  ◄── latest_update
             │  ├────────────────┤  │
             │  │ Elapsed Timer  │  │  ◄── created_at
             │  ├────────────────┤  │
             │  │ Outcome Anim   │  │  ◄── terminal status
             │  └────────────────┘  │
             └──────────────────────┘
```

---

*This PRD proposes incremental, phased improvements that transform Hand World from a fun animation into a genuinely useful agent monitoring dashboard — without requiring major backend changes, since the data infrastructure already exists.*
