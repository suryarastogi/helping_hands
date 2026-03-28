import { useState, useMemo } from "react";

export interface DiffFile {
  filename: string;
  status: string; // "modified" | "added" | "deleted" | "renamed"
  diff: string;
}

export interface DiffViewProps {
  files: DiffFile[];
  error: string | null;
  loading: boolean;
}

type LineType = "add" | "del" | "context" | "hunk" | "header";

interface DiffLine {
  type: LineType;
  content: string;
  oldNum: number | null;
  newNum: number | null;
}

function parseDiffLines(raw: string): DiffLine[] {
  const lines: DiffLine[] = [];
  let oldLine = 0;
  let newLine = 0;
  let inBody = false;

  for (const line of raw.split("\n")) {
    if (line.startsWith("@@")) {
      inBody = true;
      const match = line.match(/@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@/);
      if (match) {
        oldLine = parseInt(match[1], 10);
        newLine = parseInt(match[2], 10);
      }
      lines.push({ type: "hunk", content: line, oldNum: null, newNum: null });
      continue;
    }
    if (!inBody) {
      lines.push({ type: "header", content: line, oldNum: null, newNum: null });
      continue;
    }
    if (line.startsWith("+")) {
      lines.push({ type: "add", content: line.slice(1), oldNum: null, newNum: newLine });
      newLine++;
    } else if (line.startsWith("-")) {
      lines.push({ type: "del", content: line.slice(1), oldNum: oldLine, newNum: null });
      oldLine++;
    } else if (line.startsWith(" ") || line === "") {
      lines.push({ type: "context", content: line.slice(1), oldNum: oldLine, newNum: newLine });
      oldLine++;
      newLine++;
    }
  }
  return lines;
}

function statusBadge(status: string): string {
  switch (status) {
    case "added":
      return "A";
    case "deleted":
      return "D";
    case "renamed":
      return "R";
    default:
      return "M";
  }
}

function statusColor(status: string): string {
  switch (status) {
    case "added":
      return "#3fb950";
    case "deleted":
      return "#f85149";
    case "renamed":
      return "#d29922";
    default:
      return "#58a6ff";
  }
}

function FileDiff({ file }: { file: DiffFile }) {
  const [collapsed, setCollapsed] = useState(false);
  const lines = useMemo(() => parseDiffLines(file.diff), [file.diff]);

  const stats = useMemo(() => {
    let adds = 0;
    let dels = 0;
    for (const l of lines) {
      if (l.type === "add") adds++;
      if (l.type === "del") dels++;
    }
    return { adds, dels };
  }, [lines]);

  return (
    <div className="diff-file">
      <div
        className="diff-file-header"
        onClick={() => setCollapsed((c) => !c)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") setCollapsed((c) => !c);
        }}
      >
        <span className="diff-collapse-icon">{collapsed ? "▶" : "▼"}</span>
        <span
          className="diff-status-badge"
          style={{ color: statusColor(file.status) }}
        >
          {statusBadge(file.status)}
        </span>
        <span className="diff-filename">{file.filename}</span>
        <span className="diff-stats">
          {stats.adds > 0 && (
            <span className="diff-stat-add">+{stats.adds}</span>
          )}
          {stats.dels > 0 && (
            <span className="diff-stat-del">-{stats.dels}</span>
          )}
        </span>
      </div>
      {!collapsed && (
        <div className="diff-file-body">
          <table className="diff-table">
            <tbody>
              {lines
                .filter((l) => l.type !== "header")
                .map((line, i) => (
                  <tr key={i} className={`diff-line diff-line-${line.type}`}>
                    <td className="diff-line-num diff-line-num-old">
                      {line.oldNum ?? ""}
                    </td>
                    <td className="diff-line-num diff-line-num-new">
                      {line.newNum ?? ""}
                    </td>
                    <td className="diff-line-marker">
                      {line.type === "add"
                        ? "+"
                        : line.type === "del"
                          ? "-"
                          : line.type === "hunk"
                            ? "@@"
                            : " "}
                    </td>
                    <td className="diff-line-content">
                      <pre>{line.content}</pre>
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default function DiffView({ files, error, loading }: DiffViewProps) {
  if (loading && files.length === 0) {
    return (
      <div className="diff-view diff-loading">
        <span className="diff-spinner" />
        Loading diff...
      </div>
    );
  }

  if (error && files.length === 0) {
    return (
      <div className="diff-view diff-empty">
        <span className="diff-empty-msg">{error}</span>
      </div>
    );
  }

  if (files.length === 0) {
    return (
      <div className="diff-view diff-empty">
        <span className="diff-empty-msg">No uncommitted changes.</span>
      </div>
    );
  }

  const totalAdds = files.reduce((sum, f) => {
    let a = 0;
    for (const line of f.diff.split("\n")) {
      if (line.startsWith("+") && !line.startsWith("+++")) a++;
    }
    return sum + a;
  }, 0);
  const totalDels = files.reduce((sum, f) => {
    let d = 0;
    for (const line of f.diff.split("\n")) {
      if (line.startsWith("-") && !line.startsWith("---")) d++;
    }
    return sum + d;
  }, 0);

  return (
    <div className="diff-view">
      <div className="diff-summary">
        <span className="diff-file-count">
          {files.length} file{files.length !== 1 ? "s" : ""} changed
        </span>
        {totalAdds > 0 && (
          <span className="diff-stat-add">+{totalAdds}</span>
        )}
        {totalDels > 0 && (
          <span className="diff-stat-del">-{totalDels}</span>
        )}
        {loading && <span className="diff-spinner" title="Refreshing..." />}
      </div>
      {files.map((file) => (
        <FileDiff key={file.filename} file={file} />
      ))}
    </div>
  );
}
