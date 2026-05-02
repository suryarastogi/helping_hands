/** Shared types for the helping-hands frontend. */

export type PlayerDirection = "down" | "up" | "left" | "right";

export type WorldDecoration = {
  id: string;
  emoji: string;
  x: number;
  y: number;
  placedBy: string;
  color: string;
  placedAt: number;
};

export type ChatMessage = {
  id: string;
  playerName: string;
  playerColor: string;
  text: string;
  timestamp: number;
  /** True for system messages (join/leave notifications). */
  isSystem?: boolean;
};

export type WorkerVariant = "bot-alpha" | "bot-round" | "bot-heavy" | "goose";

export type CharacterStyle = {
  bodyColor: string;
  accentColor: string;
  skinColor: string;
  outlineColor: string;
  variant: WorkerVariant;
};

export type SceneWorkerPhase =
  | "at-gate"
  | "walking-to-plot"
  | "active"
  | "meditating"
  | "fading";

export type FloatingNumber = {
  id: number;
  taskId: string;
  value: number;
  createdAt: number;
};

// ---------------------------------------------------------------------------
// App-level types (extracted from App.tsx)
// ---------------------------------------------------------------------------

export type Backend =
  | "e2e"
  | "basic-langgraph"
  | "basic-atomic"
  | "basic-agent"
  | "codexcli"
  | "claudecodecli"
  | "docker-sandbox-claude"
  | "goose"
  | "geminicli"
  | "opencodecli"
  | "devincli";

export type BuildResponse = {
  task_id: string;
  status: string;
  backend: string;
};

export type TaskStatus = {
  task_id: string;
  status: string;
  result: Record<string, unknown> | null;
  /** True when the result is being served from the persistent snapshot rather
   * than a live workspace (workspace was cleaned up after task completion). */
  from_snapshot?: boolean;
};

export type CurrentTask = {
  task_id: string;
  status: string;
  backend?: string | null;
  repo_path?: string | null;
};

export type CurrentTasksResponse = {
  tasks: CurrentTask[];
  source: string;
};

export type WorkerCapacityResponse = {
  max_workers: number;
  source: string;
  workers: Record<string, number>;
};

export type QueueDepthResponse = {
  active: number;
  reserved: number;
  scheduled: number;
  broker_depth: number;
  source: string;
};

export type WorkerHealthSnapshot = {
  capacity: WorkerCapacityResponse | null;
  queue: QueueDepthResponse | null;
  inFlightTaskCount: number;
};

export type FormState = {
  repo_path: string;
  prompt: string;
  backend: Backend;
  model: string;
  max_iterations: number;
  pr_number: string;
  issue_number: string;
  create_issue: boolean;
  project_url: string;
  tools: string;
  no_pr: boolean;
  enable_execution: boolean;
  enable_web: boolean;
  use_native_cli_auth: boolean;
  fix_ci: boolean;
  fix_conflicts: boolean;
  master_rebase: boolean;
  ci_check_wait_minutes: number;
  github_token: string;
  reference_repos: string;
};

export type TaskHistoryItem = {
  taskId: string;
  status: string;
  backend: string;
  repoPath: string;
  createdAt: number;
  lastUpdatedAt: number;
};

export type TaskHistoryPatch = {
  taskId: string;
  status?: string;
  backend?: string;
  repoPath?: string;
};

export type ServerConfig = {
  in_docker: boolean;
  native_auth_default: boolean;
  enabled_backends?: string[];
  claude_native_cli_auth?: boolean;
  has_github_token?: boolean;
  default_repo?: string | null;
  grill_enabled?: boolean;
};

export type ServiceHealth = {
  redis: "ok" | "error";
  db: "ok" | "error" | "na";
  workers: "ok" | "error";
};

export type ServiceHealthState = {
  reachable: boolean;
  health: ServiceHealth | null;
};

export type ScheduleType = "cron" | "interval" | "watch_issues";

export type ScheduleItem = {
  schedule_id: string;
  name: string;
  schedule_type: ScheduleType;
  cron_expression: string;
  interval_seconds: number | null;
  repo_path: string;
  prompt: string;
  backend: string;
  model: string | null;
  max_iterations: number;
  pr_number: number | null;
  no_pr: boolean;
  enable_execution: boolean;
  enable_web: boolean;
  use_native_cli_auth: boolean;
  fix_ci: boolean;
  fix_conflicts: boolean;
  master_rebase: boolean;
  ci_check_wait_minutes: number;
  github_token: string | null;
  reference_repos: string[];
  tools: string[];
  watch_labels: string[];
  enabled: boolean;
  created_at: string;
  last_run_at: string | null;
  last_run_task_id: string | null;
  run_count: number;
  next_run_at: string | null;
};

export type ScheduleFormState = {
  name: string;
  schedule_type: ScheduleType;
  cron_expression: string;
  interval_seconds: number;
  repo_path: string;
  prompt: string;
  backend: Backend;
  model: string;
  max_iterations: number;
  pr_number: string;
  no_pr: boolean;
  enable_execution: boolean;
  enable_web: boolean;
  use_native_cli_auth: boolean;
  fix_ci: boolean;
  fix_conflicts: boolean;
  master_rebase: boolean;
  ci_check_wait_minutes: number;
  github_token: string;
  reference_repos: string;
  tools: string;
  watch_labels: string;
  enabled: boolean;
};

export type ClaudeUsageLevel = {
  name: string;
  percent_used: number;
  detail: string;
};

export type ClaudeUsageResponse = {
  levels: ClaudeUsageLevel[];
  error: string | null;
  fetched_at: string;
};

export type OutputTab = "updates" | "raw" | "payload";
export type PrefixFilterMode = "show" | "hide" | "only";
export type MainView = "submission" | "monitor" | "schedules";

export type SceneWorker = {
  taskId: string;
  slot: number;
  phase: SceneWorkerPhase;
  phaseChangedAt: number;
};

export type PlayerPosition = {
  x: number;
  y: number;
};

export type CursorPosition = {
  x: number;
  y: number;
};

export type InputItem = {
  label: string;
  value: string;
};

export type PlotSlot = {
  id: string;
  left: number;
  top: number;
};

export type AccumulatedUsage = {
  totalCost: number;
  totalSeconds: number;
  totalIn: number;
  totalOut: number;
  count: number;
};

// ---------------------------------------------------------------------------
// Grill Me — interactive AI interview sessions
// ---------------------------------------------------------------------------

export type GrillStartResponse = {
  session_id: string;
  status: string;
};

export type GrillMessage = {
  id: string;
  role: "assistant" | "system" | "user";
  content: string;
  type: "message" | "plan" | "error" | "timeout";
  timestamp: number;
};

export type GrillPollResponse = {
  session_id: string;
  status: string;
  messages: GrillMessage[];
};

export type GrillFormState = {
  repo_path: string;
  prompt: string;
  model: string;
  github_token: string;
  reference_repos: string;
  backend: string;
};

export type GrillPhase = "form" | "chatting" | "plan";

export type GrillSessionSummary = {
  session_id: string;
  status: string;
  repo_path: string;
  prompt: string;
  model: string;
  backend: string;
  turn_count: number;
};

export type GrillResumableListResponse = {
  sessions: GrillSessionSummary[];
  total: number;
};

// ---------------------------------------------------------------------------
// Multiplayer Grill Me
// ---------------------------------------------------------------------------

export type MGrillCreateResponse = {
  session_id: string;
  status: string;
};

export type MGrillMessage = {
  id: string;
  role: "assistant" | "system" | "user";
  content: string;
  type: "message" | "plan" | "error" | "timeout";
  author_player_id: string | null;
  author_name: string | null;
  timestamp: number;
};

export type MGrillPendingEntry = {
  pending_id: string;
  player_id: string;
  name: string;
  content: string;
  timestamp: number;
};

export type MGrillPollResponse = {
  session_id: string;
  status: string;
  creator_name: string;
  creator_token_hash: string | null;
  creator_player_id: string | null;
  creator_last_seen_ts: number;
  is_creator: boolean;
  can_act_as_creator: boolean;
  repo_path: string;
  prompt: string;
  model: string | null;
  backend: string;
  turn_count: number;
  participant_count: number;
  submitted_task_id: string | null;
};

export type MGrillSessionSummary = {
  session_id: string;
  status: string;
  creator_name: string;
  repo_path: string;
  prompt: string;
  turn_count: number;
  created_at: number;
  last_activity_ts: number;
  participant_count: number;
  has_final_plan: boolean;
};

export type MGrillListResponse = {
  sessions: MGrillSessionSummary[];
  total: number;
};

export type MGrillCreateForm = {
  repo_path: string;
  prompt: string;
  model: string;
  backend: string;
  reference_repos: string;
};

// ---------------------------------------------------------------------------
// Task Templates
// ---------------------------------------------------------------------------

export type TaskTemplate = {
  template_id: string;
  name: string;
  description: string;
  owner_token_hash: string | null;
  created_at: string;
  updated_at: string;
  repo_path: string | null;
  prompt: string | null;
  backend: string | null;
  model: string | null;
  max_iterations: number | null;
  pr_number: number | null;
  issue_number: number | null;
  create_issue: boolean | null;
  project_url: string | null;
  no_pr: boolean | null;
  enable_execution: boolean | null;
  enable_web: boolean | null;
  use_native_cli_auth: boolean | null;
  fix_ci: boolean | null;
  fix_conflicts: boolean | null;
  master_rebase: boolean | null;
  ci_check_wait_minutes: number | null;
  reference_repos: string[] | null;
  tools: string[] | null;
};

export type TemplateFormState = {
  name: string;
  description: string;
};
