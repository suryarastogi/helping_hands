const STATUS_COLOR: Record<string, string> = {
  active: "green",
  thinking: "green",
  suspended: "amber",
  error: "red",
  max_turns: "red",
  completed: "purple",
};

export default function SessionStatusDot({ status }: { status: string }) {
  const color = STATUS_COLOR[status] ?? "gray";
  return <span className={`session-status-dot status-dot-${color}`} />;
}
