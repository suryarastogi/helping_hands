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
  | "at-factory"
  | "walking-to-desk"
  | "active"
  | "walking-to-exit"
  | "at-exit";

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

export type ScheduleType = "cron" | "interval";

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

export type DeskSlot = {
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
};

export type GrillPhase = "form" | "chatting" | "plan";
