# PRD: Hand World — Agent Visibility & Observability

**Author:** Auto-generated
**Date:** 2026-02-28
**Status:** Draft
**Area:** Frontend (Hand World view), Server API, Hand execution layer

---

## 1. Problem Statement

Hand World is a creative, gamified monitoring dashboard that represents running agents as animated robot sprites working at desks in a pixelated office. While the visual metaphor is engaging, the current implementation surfaces **very little actionable information** about what each agent is actually doing. Users can see *that* agents are running, but not *what* they're working on, *how far along* they are, or *how well* it's going.

### Current Limitations

| Gap | Detail |
|-----|--------|
| **No per-agent status detail** | Workers show as generic colored sprites with no visible task context |
| **No progress indication** | No way to tell if an agent is on iteration 1/5 or 5/5 |
| **No tool activity** | Users can't see when an agent reads a file, writes code, or runs a command |
| **No timing data** | No elapsed time, no estimated time remaining |
| **No token/cost tracking** | No visibility into API usage or cost per task |
| **Polling-only updates** | 10-second polling interval means stale state for up to 10s |
| **Minimal hover/click info** | Clicking a worker switches to raw output view — no in-world detail panel |
| **No diff/change summary** | Can't see what files an agent has modified without reading raw output |
| **No error visibility** | Failed or stuck agents look the same as healthy ones |

---

## 2. Goals

1. **Make each agent's current activity legible at a glance** without leaving the World view
2. **Surface progress, timing, and iteration state** visually on each worker sprite
3. **Show tool activity in real-time** (file reads, writes, command execution)
4. **Expose per-task cost and token usage** for budget-conscious users
5. **Reduce update latency** from 10s polling to near-real-time
6. **Highlight errors and stuck states** prominently so users can intervene

---

## 3. Proposed Features

### 3.1 Worker Status Badges & Micro-HUD

**Priority: P0**

Each worker sprite in the World view should display a small status region above or beside it:

```
  ┌─────────────────────────┐
  │  🤖  Claude (Sonnet)    │  ← backend + model label
  │  ████████░░  iter 3/5   │  ← progress bar + iteration
  │  📁 src/auth/login.ts   │  ← current file being worked on
  │  ⏱ 2m 14s               │  ← elapsed time
  └─────────────────────────┘
```

**Data sources (already available):**
- `backend` and `model` from Celery task meta
- `iterations` count from iterative hand metadata
- `max_iterations` from task config
- Elapsed time derivable from `createdAt` timestamp

**Data sources (need to add):**
- Current file being edited: parse from `@@FILE` / `@@READ` markers in streaming updates
- Current tool being executed: emit structured events from tool layer

### 3.2 Activity Feed Bubbles

**Priority: P0**

Show small speech-bubble or thought-bubble popups above workers as they perform actions:

- `"Reading README.md..."` — when agent reads a file
- `"Editing src/app.ts..."` — when agent writes a file
- `"Running tests..."` — when agent executes a command
- `"Searching web..."` — when agent uses web tools
- `"Creating PR..."` — during finalization
- `"Thinking..."` — during LLM inference with no tool use

Bubbles should:
- Auto-dismiss after 3–5 seconds
- Stack up to 2 max (most recent on top)
- Use icons matching the tool type
- Be togglable (some users may find them noisy)

**Implementation:** Requires structured event emission from the tool layer (`filesystem.py`, `command.py`, `web.py`) and a new event type in the streaming/progress protocol.

### 3.3 Worker State Coloring & Animation

**Priority: P1**

Enhance sprite visual state beyond the current binary active/inactive:

| State | Visual Treatment |
|-------|-----------------|
| **Queued/Pending** | Greyed out, no animation |
| **Starting (bootstrap)** | Slow pulse, loading indicator |
| **Active (LLM thinking)** | Standard bob animation |
| **Active (tool execution)** | Fast bob + tool icon overlay |
| **Writing files** | Typing animation on desk keyboard |
| **Finalizing (PR creation)** | Green glow, checkmark forming |
| **Completed** | Celebration animation, then leave |
| **Error/Failed** | Red tint, exclamation icon, stays at desk |
| **Interrupted** | Yellow tint, pause icon |
| **Stuck (idle > 60s)** | Sleep "Zzz" animation |

**Data sources:** Map from Celery task status (`PENDING`, `PROGRESS`, `SUCCESS`, `FAILURE`, `REVOKED`) plus new granular sub-states in progress metadata.

### 3.4 Worker Detail Panel (In-World Overlay)

**Priority: P1**

When a user clicks a worker (or presses Enter near one), show an **in-world overlay panel** instead of switching to the classic view. The panel should appear as a floating card anchored to the worker's desk:

```
┌─────────────────────────────────────────┐
│  Agent: BasicLangGraphHand              │
│  Model: claude-sonnet-4-5              │
│  Repo:  myorg/my-app                    │
│  Prompt: "Add user authentication..."   │
│                                         │
│  Progress: ████████░░ 3/5 iterations    │
│  Elapsed:  4m 32s                       │
│  Tokens:   ~12,400 in / ~8,200 out      │
│                                         │
│  Files Modified:                        │
│    + src/auth/middleware.ts  (new)       │
│    ~ src/app.ts             (modified)  │
│    ~ package.json           (modified)  │
│                                         │
│  Recent Activity:                       │
│    • Wrote src/auth/middleware.ts        │
│    • Read src/app.ts                    │
│    • Running: npm test                  │
│                                         │
│  [View Full Output]  [Cancel Task]      │
└─────────────────────────────────────────┘
```

**Key data points:**
- Task configuration (backend, model, repo, prompt)
- Iteration progress (current / max)
- Elapsed wall-clock time
- Token usage (requires provider integration — see §3.7)
- Files modified (parse from streaming updates or add structured metadata)
- Recent activity log (last 5–10 tool actions)
- Action buttons (view raw output, cancel/interrupt task)

### 3.5 Office-Level Dashboard HUD

**Priority: P1**

The existing corner HUD should be expanded to show aggregate office statistics:

```
┌──────────────────────────┐
│  HAND WORLD              │
│  Active: 3/8 workers     │
│  Queued: 2 tasks         │
│  Completed today: 14     │
│  Total tokens: ~284K     │
│  PRs created: 6          │
│  Uptime: 4h 12m          │
└──────────────────────────┘
```

**Data sources:** Aggregate from `/tasks/current`, `/workers/capacity`, and task history (already stored in `localStorage`).

### 3.6 Real-Time Updates via Server-Sent Events (SSE)

**Priority: P1**

Replace the 10-second polling for `/tasks/current` with an SSE endpoint:

```
GET /tasks/stream
Content-Type: text/event-stream

event: task_update
data: {"task_id": "abc123", "status": "PROGRESS", "iteration": 3, ...}

event: task_complete
data: {"task_id": "abc123", "status": "SUCCESS", "pr_url": "..."}

event: worker_activity
data: {"task_id": "abc123", "action": "file_write", "path": "src/app.ts"}
```

Benefits:
- Near-instant UI updates (sub-second vs 10s)
- Lower server load (no repeated polling)
- Enables activity feed bubbles (§3.2) with real data
- SSE is simpler than WebSockets and works with existing HTTP infrastructure

**Implementation:** Add an SSE endpoint in FastAPI using `StreamingResponse`. Celery tasks publish events to a Redis pub/sub channel. The SSE endpoint subscribes and relays.

### 3.7 Token & Cost Tracking

**Priority: P2**

Track and surface per-task token usage and estimated cost:

**Backend changes:**
- Capture `usage` metadata from provider responses (most providers return `prompt_tokens`, `completion_tokens`)
- Accumulate per-iteration totals in `HandResponse.metadata`
- Include in Celery progress updates

**Frontend display:**
- Show in worker detail panel (§3.4)
- Show in office HUD as aggregate (§3.5)
- Show in task history for completed tasks

**Cost estimation:**
- Maintain a simple price table per model (configurable)
- Calculate estimated cost = tokens × price_per_token
- Display as `~$0.42` in the detail panel

### 3.8 Repo Change Summary

**Priority: P2**

After a task completes (or during execution), show a summary of repository changes:

- Files added / modified / deleted with line counts
- Mini-diff preview (first few lines of each change)
- Link to PR if created

**Implementation:** Run `git diff --stat` equivalent after each iteration in the hand execution loop. Capture output in metadata. For the World view, display as a tooltip or in the detail panel.

### 3.9 Multi-Room / Zone Layout

**Priority: P3**

As the number of concurrent workers grows, organize the office into themed zones:

- **CLI Zone** — desks for Claude Code, Codex, Goose, Gemini CLI hands
- **Agent Zone** — desks for LangGraph, Atomic agent hands
- **E2E Zone** — desks for E2E integration hands
- **Queue Area** — waiting area for pending tasks

Each zone could have distinct visual styling (wall color, decorations) matching the backend provider's brand.

### 3.10 Sound & Notification System

**Priority: P3**

Optional audio/visual notifications:

- Subtle keyboard typing sounds when agents write files
- Completion chime when a task finishes
- Alert sound on task failure
- Browser notification for task completion (when tab is in background)

Sounds should be **off by default** with a toggle in the HUD.

---

## 4. Data Model Changes

### 4.1 New: Structured Activity Events

Add a new event type to the streaming protocol:

```python
@dataclass
class HandActivityEvent:
    """Structured event emitted during hand execution."""
    timestamp: float
    event_type: str  # "tool_start", "tool_end", "iteration_start",
                     # "iteration_end", "file_write", "file_read",
                     # "command_exec", "web_search", "pr_create"
    detail: dict[str, Any]
    # e.g. {"tool": "filesystem", "action": "write", "path": "src/app.ts"}
```

Emit from:
- `filesystem.py` — on read/write operations
- `command.py` — on command execution start/end
- `web.py` — on web search/fetch
- `iterative.py` — on iteration boundaries
- `base.py` — on PR finalization steps

### 4.2 Extended Progress Metadata

Add to Celery `_update_progress()` calls:

```python
meta = {
    # ... existing fields ...
    "current_iteration": int,
    "max_iterations": int,
    "elapsed_seconds": float,
    "tokens_in": int,
    "tokens_out": int,
    "files_modified": list[str],
    "recent_activity": list[dict],  # Last 10 HandActivityEvents
    "sub_stage": str,  # "thinking", "tool_exec", "file_write", "finalizing"
}
```

### 4.3 New API Endpoint: Task Activity Stream

```
GET /tasks/{task_id}/activity
Content-Type: text/event-stream
```

Streams `HandActivityEvent` objects in real-time for a specific task.

---

## 5. Technical Architecture

### Event Pipeline

```
Hand execution (iterative/cli/e2e)
    │
    ├── Tool layer emits HandActivityEvent
    │       │
    │       ▼
    │   Redis Pub/Sub channel: "hand:activity:{task_id}"
    │       │
    │       ▼
    │   SSE endpoint subscribes and relays to frontend
    │
    ├── Celery _update_progress() includes summary metadata
    │       │
    │       ▼
    │   /tasks/{task_id} REST endpoint (existing)
    │
    └── HandResponse.metadata includes execution summary
```

### Frontend State Management

Extend `SceneWorker` type:

```typescript
type SceneWorker = {
  // ... existing fields ...
  currentIteration: number;
  maxIterations: number;
  elapsedSeconds: number;
  currentFile: string | null;
  subStage: "thinking" | "tool_exec" | "file_write" | "finalizing";
  recentActivity: ActivityEvent[];
  tokensIn: number;
  tokensOut: number;
  filesModified: string[];
  error: string | null;
};
```

---

## 6. Implementation Phases

### Phase 1: Foundation (P0) — ~1–2 weeks
1. Add `current_iteration`, `max_iterations`, `elapsed_seconds`, `sub_stage` to Celery progress metadata
2. Parse iteration/file info from existing streaming updates on the frontend
3. Implement worker status badges with progress bar and iteration count
4. Add elapsed time display per worker
5. Implement basic activity bubbles using parsed update strings

### Phase 2: Rich Context (P1) — ~2–3 weeks
1. Define `HandActivityEvent` dataclass and emit from tool layer
2. Add Redis pub/sub event pipeline
3. Implement SSE endpoint (`/tasks/stream`)
4. Build worker detail panel overlay in World view
5. Enhance sprite state coloring and animations
6. Expand office-level HUD with aggregate stats
7. Migrate frontend from polling to SSE for task updates

### Phase 3: Analytics (P2) — ~1–2 weeks
1. Integrate token usage capture from AI provider responses
2. Add cost estimation logic with configurable price table
3. Implement repo change summary (git diff stats)
4. Surface token/cost in detail panel and HUD
5. Add historical cost tracking to task history

### Phase 4: Polish (P3) — ~1 week
1. Multi-room zone layout
2. Optional sound effects
3. Browser notifications for background tab
4. Per-zone visual theming

---

## 7. Success Metrics

| Metric | Target |
|--------|--------|
| **Time to understand agent status** | < 2 seconds (glance at World view) |
| **Information available without clicking** | Backend, model, iteration progress, elapsed time, current activity |
| **Update latency** | < 1 second (via SSE, down from 10s polling) |
| **User satisfaction** | Qualitative — users report feeling "in control" of agent fleet |

---

## 8. Open Questions

1. **Token tracking feasibility**: Not all providers expose token counts consistently (especially CLI hands that wrap external processes). Should we estimate or show "N/A"?
2. **Event volume**: High-frequency tool events could overwhelm the UI and Redis. Should we rate-limit to 1 event/second per task?
3. **Mobile/responsive**: The World view is desktop-oriented. Should the detail panel adapt for smaller screens, or should mobile users use the classic view?
4. **Persistence**: Should activity events be stored (e.g., in the DB) for post-mortem analysis, or are they ephemeral stream-only?
5. **Multi-user**: If multiple users watch the same office, should they see each other's player characters?

---

## 9. Dependencies

- **Redis pub/sub**: Already available (used for Celery broker)
- **SSE support in FastAPI**: Native via `StreamingResponse` — no new dependencies
- **Provider token usage**: Requires changes per provider in `src/helping_hands/lib/ai_providers/`
- **Git diff stats**: Requires `git` CLI availability in worker environments (already present)

---

## 10. Risks

| Risk | Mitigation |
|------|------------|
| Event overhead slows hand execution | Use async event emission, fire-and-forget to Redis |
| Redis pub/sub message loss | Events are informational, not critical — acceptable |
| CLI hands have limited observability | Show "CLI mode — limited telemetry" badge, parse stdout best-effort |
| Token cost estimates are inaccurate | Label as "estimated", allow user override of price table |
| World view performance with many workers | Virtual viewport, limit visible workers to ~16 |
