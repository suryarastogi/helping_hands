/** Shared types for the helping-hands frontend. */

export type PlayerDirection = "down" | "up" | "left" | "right";

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
