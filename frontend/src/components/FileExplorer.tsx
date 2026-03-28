import { useState, useMemo, useCallback, useEffect, useRef } from "react";

import { apiUrl } from "../App.utils";

// --- Types ---

export interface FileTreeEntry {
  path: string;
  name: string;
  type: "file" | "dir";
  status: string | null; // "modified" | "added" | "deleted" | "renamed" | null
}

interface FileContentData {
  content: string | null;
  diff: string | null;
  status: string | null;
  error: string | null;
}

export interface FileExplorerProps {
  taskId: string;
  tree: FileTreeEntry[];
  treeError: string | null;
  treeLoading: boolean;
}

// --- Tree building helpers ---

interface TreeNode {
  name: string;
  path: string;
  type: "file" | "dir";
  status: string | null;
  children: TreeNode[];
}

function buildTreeNodes(entries: FileTreeEntry[]): TreeNode[] {
  const root: TreeNode = { name: "", path: "", type: "dir", status: null, children: [] };
  const nodeMap = new Map<string, TreeNode>();
  nodeMap.set("", root);

  // Sort entries so dirs come before files, then alphabetically
  const sorted = [...entries].sort((a, b) => {
    if (a.type !== b.type) return a.type === "dir" ? -1 : 1;
    return a.path.localeCompare(b.path);
  });

  for (const entry of sorted) {
    const parts = entry.path.split("/");
    const parentPath = parts.slice(0, -1).join("/");
    const parent = nodeMap.get(parentPath) ?? root;

    const node: TreeNode = {
      name: entry.name,
      path: entry.path,
      type: entry.type,
      status: entry.status,
      children: [],
    };
    nodeMap.set(entry.path, node);
    parent.children.push(node);
  }

  return root.children;
}

function dirHasChanges(node: TreeNode): boolean {
  if (node.status) return true;
  return node.children.some(dirHasChanges);
}

// --- Status indicators ---

function statusIndicator(status: string | null): { icon: string; color: string } | null {
  switch (status) {
    case "modified":
      return { icon: "M", color: "#58a6ff" };
    case "added":
      return { icon: "+", color: "#3fb950" };
    case "deleted":
      return { icon: "-", color: "#f85149" };
    case "renamed":
      return { icon: "R", color: "#d29922" };
    default:
      return null;
  }
}

// --- Diff line parsing (reused from DiffView) ---

type LineType = "add" | "del" | "context" | "hunk" | "header";

interface DiffLine {
  type: LineType;
  content: string;
  lineNum: number | null;
}

function parseDiffForDisplay(raw: string): DiffLine[] {
  const lines: DiffLine[] = [];
  let newLine = 0;
  let inBody = false;

  for (const line of raw.split("\n")) {
    if (line.startsWith("@@")) {
      inBody = true;
      const match = line.match(/@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@/);
      if (match) newLine = parseInt(match[1], 10);
      lines.push({ type: "hunk", content: line, lineNum: null });
      continue;
    }
    if (!inBody) continue;
    if (line.startsWith("+")) {
      lines.push({ type: "add", content: line.slice(1), lineNum: newLine });
      newLine++;
    } else if (line.startsWith("-")) {
      lines.push({ type: "del", content: line.slice(1), lineNum: null });
    } else {
      lines.push({ type: "context", content: line.slice(1), lineNum: newLine });
      newLine++;
    }
  }
  return lines;
}

// --- File content viewer ---

function FileContentViewer({
  taskId,
  filePath,
  onClose,
}: {
  taskId: string;
  filePath: string;
  onClose: () => void;
}) {
  const [data, setData] = useState<FileContentData | null>(null);
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState<"source" | "diff">("source");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setData(null);
    (async () => {
      try {
        const res = await fetch(
          apiUrl(`/tasks/${taskId}/file/${encodeURIComponent(filePath)}?_=${Date.now()}`),
          { cache: "no-store" },
        );
        if (cancelled) return;
        if (!res.ok) {
          setData({ content: null, diff: null, status: null, error: `HTTP ${res.status}` });
          return;
        }
        const json = await res.json();
        if (cancelled) return;
        setData({
          content: json.content ?? null,
          diff: json.diff ?? null,
          status: json.status ?? null,
          error: json.error ?? null,
        });
        // Auto-switch to diff view if file has changes
        if (json.diff) setViewMode("diff");
        else setViewMode("source");
      } catch {
        if (!cancelled) setData({ content: null, diff: null, status: null, error: "Failed to fetch" });
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [taskId, filePath]);

  const diffLines = useMemo(
    () => (data?.diff ? parseDiffForDisplay(data.diff) : []),
    [data?.diff],
  );

  const si = statusIndicator(data?.status ?? null);

  return (
    <div className="fe-content-panel">
      <div className="fe-content-header">
        <div className="fe-content-header-left">
          {si && (
            <span className="fe-status-indicator" style={{ color: si.color }}>
              {si.icon}
            </span>
          )}
          <span className="fe-content-path" title={filePath}>{filePath}</span>
        </div>
        <div className="fe-content-header-right">
          {data?.diff && (
            <div className="fe-view-toggle" role="tablist">
              <button
                type="button"
                role="tab"
                className={`fe-view-btn${viewMode === "source" ? " active" : ""}`}
                aria-selected={viewMode === "source"}
                onClick={() => setViewMode("source")}
              >
                Source
              </button>
              <button
                type="button"
                role="tab"
                className={`fe-view-btn${viewMode === "diff" ? " active" : ""}`}
                aria-selected={viewMode === "diff"}
                onClick={() => setViewMode("diff")}
              >
                Diff
              </button>
            </div>
          )}
          <button type="button" className="fe-close-btn" onClick={onClose} title="Close file">
            &times;
          </button>
        </div>
      </div>
      <div className="fe-content-body">
        {loading && (
          <div className="fe-content-loading">
            <span className="diff-spinner" /> Loading...
          </div>
        )}
        {!loading && data?.error && (
          <div className="fe-content-error">{data.error}</div>
        )}
        {!loading && !data?.error && viewMode === "source" && data?.content != null && (
          <table className="fe-source-table">
            <tbody>
              {data.content.split("\n").map((line, i) => (
                  <tr key={i} className="fe-source-line">
                    <td className="fe-source-num">{i + 1}</td>
                    <td className="fe-source-content">
                      <pre>{line}</pre>
                    </td>
                  </tr>
              ))}
            </tbody>
          </table>
        )}
        {!loading && !data?.error && viewMode === "diff" && diffLines.length > 0 && (
          <table className="diff-table">
            <tbody>
              {diffLines.map((line, i) => (
                <tr key={i} className={`diff-line diff-line-${line.type}`}>
                  <td className="diff-line-num diff-line-num-new">
                    {line.lineNum ?? ""}
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
        )}
        {!loading && !data?.error && data?.content == null && !data?.diff && (
          <div className="fe-content-error">No content available</div>
        )}
      </div>
    </div>
  );
}

// --- Tree node component ---

function TreeNodeRow({
  node,
  depth,
  expandedDirs,
  toggleDir,
  selectedFile,
  onSelectFile,
}: {
  node: TreeNode;
  depth: number;
  expandedDirs: Set<string>;
  toggleDir: (path: string) => void;
  selectedFile: string | null;
  onSelectFile: (path: string) => void;
}) {
  const isExpanded = expandedDirs.has(node.path);
  const si = statusIndicator(node.status);
  const hasChanges = node.type === "dir" && dirHasChanges(node);
  const isSelected = node.type === "file" && selectedFile === node.path;

  return (
    <>
      <div
        className={`fe-tree-row${isSelected ? " selected" : ""}${node.type === "dir" ? " dir" : ""}`}
        style={{ paddingLeft: `${12 + depth * 16}px` }}
        onClick={() => {
          if (node.type === "dir") toggleDir(node.path);
          else onSelectFile(node.path);
        }}
        role="treeitem"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            if (node.type === "dir") toggleDir(node.path);
            else onSelectFile(node.path);
          }
        }}
        aria-expanded={node.type === "dir" ? isExpanded : undefined}
      >
        {node.type === "dir" ? (
          <span className="fe-tree-icon">{isExpanded ? "▼" : "▶"}</span>
        ) : (
          <span className="fe-tree-icon fe-tree-file-icon">📄</span>
        )}
        <span className={`fe-tree-name${hasChanges ? " has-changes" : ""}`}>
          {node.name}
          {node.type === "dir" && "/"}
        </span>
        {si && (
          <span className="fe-tree-status" style={{ color: si.color }}>
            {si.icon}
          </span>
        )}
      </div>
      {node.type === "dir" && isExpanded && (
        <>
          {sortTreeChildren(node.children).map((child) => (
            <TreeNodeRow
              key={child.path}
              node={child}
              depth={depth + 1}
              expandedDirs={expandedDirs}
              toggleDir={toggleDir}
              selectedFile={selectedFile}
              onSelectFile={onSelectFile}
            />
          ))}
        </>
      )}
    </>
  );
}

function sortTreeChildren(children: TreeNode[]): TreeNode[] {
  return [...children].sort((a, b) => {
    if (a.type !== b.type) return a.type === "dir" ? -1 : 1;
    return a.name.localeCompare(b.name);
  });
}

// --- Main FileExplorer component ---

export default function FileExplorer({ taskId, tree, treeError, treeLoading }: FileExplorerProps) {
  const [expandedDirs, setExpandedDirs] = useState<Set<string>>(new Set());
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [filterText, setFilterText] = useState("");
  const [changesOnly, setChangesOnly] = useState(false);
  const initialExpanded = useRef(false);

  const treeNodes = useMemo(() => buildTreeNodes(tree), [tree]);

  // Auto-expand first 2 levels on initial load
  useEffect(() => {
    if (initialExpanded.current || tree.length === 0) return;
    initialExpanded.current = true;
    const dirs = new Set<string>();
    for (const entry of tree) {
      if (entry.type === "dir") {
        const depth = entry.path.split("/").length;
        if (depth <= 2) dirs.add(entry.path);
      }
    }
    setExpandedDirs(dirs);
  }, [tree]);

  const toggleDir = useCallback((path: string) => {
    setExpandedDirs((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  }, []);

  const filteredNodes = useMemo(() => {
    if (!filterText && !changesOnly) return treeNodes;

    const lowerFilter = filterText.toLowerCase();

    function filterNode(node: TreeNode): TreeNode | null {
      if (node.type === "file") {
        if (changesOnly && !node.status) return null;
        if (lowerFilter && !node.path.toLowerCase().includes(lowerFilter)) return null;
        return node;
      }
      const filteredChildren = node.children
        .map(filterNode)
        .filter((n): n is TreeNode => n !== null);
      if (filteredChildren.length === 0) return null;
      return { ...node, children: filteredChildren };
    }

    return treeNodes
      .map(filterNode)
      .filter((n): n is TreeNode => n !== null);
  }, [treeNodes, filterText, changesOnly]);

  // Auto-expand filtered results
  const displayExpandedDirs = useMemo(() => {
    if (!filterText && !changesOnly) return expandedDirs;
    // When filtering, expand all dirs that survived
    const dirs = new Set(expandedDirs);
    function collectDirs(nodes: TreeNode[]) {
      for (const n of nodes) {
        if (n.type === "dir") {
          dirs.add(n.path);
          collectDirs(n.children);
        }
      }
    }
    collectDirs(filteredNodes);
    return dirs;
  }, [expandedDirs, filteredNodes, filterText, changesOnly]);

  const changedCount = useMemo(
    () => tree.filter((e) => e.type === "file" && e.status).length,
    [tree],
  );

  if (treeLoading && tree.length === 0) {
    return (
      <div className="fe-container fe-loading">
        <span className="diff-spinner" /> Loading file tree...
      </div>
    );
  }

  if (treeError && tree.length === 0) {
    return (
      <div className="fe-container fe-empty">
        <span>{treeError}</span>
      </div>
    );
  }

  return (
    <div className="fe-container">
      <div className="fe-tree-panel">
        <div className="fe-tree-toolbar">
          <input
            type="text"
            className="fe-tree-filter"
            placeholder="Filter files..."
            value={filterText}
            onChange={(e) => setFilterText(e.target.value)}
          />
          <button
            type="button"
            className={`fe-changes-btn${changesOnly ? " active" : ""}`}
            onClick={() => setChangesOnly((c) => !c)}
            title={changesOnly ? "Show all files" : "Show changed files only"}
          >
            {changedCount > 0 ? `${changedCount}` : "0"} changed
          </button>
        </div>
        <div className="fe-tree-list" role="tree">
          {filteredNodes.length === 0 ? (
            <div className="fe-tree-empty">
              {filterText || changesOnly ? "No matching files" : "Empty workspace"}
            </div>
          ) : (
            sortTreeChildren(filteredNodes).map((node) => (
              <TreeNodeRow
                key={node.path}
                node={node}
                depth={0}
                expandedDirs={displayExpandedDirs}
                toggleDir={toggleDir}
                selectedFile={selectedFile}
                onSelectFile={setSelectedFile}
              />
            ))
          )}
        </div>
      </div>
      <div className="fe-content-wrapper">
        {selectedFile ? (
          <FileContentViewer
            taskId={taskId}
            filePath={selectedFile}
            onClose={() => setSelectedFile(null)}
          />
        ) : (
          <div className="fe-content-placeholder">
            Select a file to view its contents
          </div>
        )}
      </div>
    </div>
  );
}
