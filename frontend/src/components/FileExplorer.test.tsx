import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, fireEvent, waitFor } from "@testing-library/react";

import FileExplorer from "./FileExplorer";
import type { FileTreeEntry } from "./FileExplorer";

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const TREE_ENTRIES: FileTreeEntry[] = [
  { path: "src", name: "src", type: "dir", status: null },
  { path: "src/main.py", name: "main.py", type: "file", status: "modified" },
  { path: "src/utils.py", name: "utils.py", type: "file", status: null },
  { path: "tests", name: "tests", type: "dir", status: null },
  { path: "tests/test_main.py", name: "test_main.py", type: "file", status: "added" },
  { path: "README.md", name: "README.md", type: "file", status: null },
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Query tree node names from within a container. */
function getTreeNames(container: HTMLElement): string[] {
  return Array.from(container.querySelectorAll(".fe-tree-name")).map(
    (el) => el.textContent ?? "",
  );
}

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("../App.utils", () => ({
  apiUrl: (path: string) => `http://test${path}`,
}));

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

// ---------------------------------------------------------------------------
// Loading / Error / Empty states
// ---------------------------------------------------------------------------

describe("FileExplorer", () => {
  describe("loading state", () => {
    it("shows loading spinner when loading with no tree", () => {
      const { container } = render(
        <FileExplorer taskId="t1" tree={[]} treeError={null} treeLoading={true} />,
      );
      expect(container.querySelector(".fe-loading")).toBeTruthy();
      expect(container.textContent).toContain("Loading file tree");
    });

    it("renders tree when loading with existing entries", () => {
      const { container } = render(
        <FileExplorer taskId="t1" tree={TREE_ENTRIES} treeError={null} treeLoading={true} />,
      );
      expect(container.querySelector(".fe-loading")).toBeNull();
      expect(container.querySelector(".fe-tree-list")).toBeTruthy();
    });
  });

  describe("error state", () => {
    it("shows error when error with no tree", () => {
      const { container } = render(
        <FileExplorer taskId="t1" tree={[]} treeError="Fetch failed" treeLoading={false} />,
      );
      expect(container.querySelector(".fe-empty")).toBeTruthy();
      expect(container.textContent).toContain("Fetch failed");
    });
  });

  describe("empty workspace", () => {
    it("shows empty message when tree is empty", () => {
      const { container } = render(
        <FileExplorer taskId="t1" tree={[]} treeError={null} treeLoading={false} />,
      );
      expect(container.textContent).toContain("Empty workspace");
    });
  });

  // ---------------------------------------------------------------------------
  // Tree rendering
  // ---------------------------------------------------------------------------

  describe("tree rendering", () => {
    it("renders directories and files", () => {
      const { container } = render(
        <FileExplorer taskId="t1" tree={TREE_ENTRIES} treeError={null} treeLoading={false} />,
      );
      const names = getTreeNames(container);
      expect(names).toContain("src/");
      expect(names).toContain("tests/");
      expect(names).toContain("README.md");
    });

    it("shows status indicators on modified files", () => {
      const { container } = render(
        <FileExplorer taskId="t1" tree={TREE_ENTRIES} treeError={null} treeLoading={false} />,
      );
      const statusIcons = container.querySelectorAll(".fe-tree-status");
      // main.py = M, test_main.py = +
      expect(statusIcons.length).toBeGreaterThanOrEqual(2);
    });

    it("shows changed file count in the changes button", () => {
      const { container } = render(
        <FileExplorer taskId="t1" tree={TREE_ENTRIES} treeError={null} treeLoading={false} />,
      );
      const changesBtn = container.querySelector(".fe-changes-btn")!;
      expect(changesBtn.textContent).toContain("2");
    });
  });

  // ---------------------------------------------------------------------------
  // Directory toggle
  // ---------------------------------------------------------------------------

  describe("directory toggle", () => {
    it("auto-expands first 2 levels on initial load", () => {
      const { container } = render(
        <FileExplorer taskId="t1" tree={TREE_ENTRIES} treeError={null} treeLoading={false} />,
      );
      const names = getTreeNames(container);
      expect(names).toContain("main.py");
      expect(names).toContain("utils.py");
      expect(names).toContain("test_main.py");
    });

    it("collapses a directory on click", () => {
      const { container } = render(
        <FileExplorer taskId="t1" tree={TREE_ENTRIES} treeError={null} treeLoading={false} />,
      );
      // Find the src/ dir row and click it
      const dirRows = container.querySelectorAll(".fe-tree-row.dir");
      const srcRow = Array.from(dirRows).find((r) =>
        r.querySelector(".fe-tree-name")?.textContent === "src/",
      )!;
      fireEvent.click(srcRow);
      // Children should be hidden
      const names = getTreeNames(container);
      expect(names).not.toContain("main.py");
      expect(names).not.toContain("utils.py");
      // Other dirs still visible
      expect(names).toContain("test_main.py");
    });

    it("re-expands a directory on second click", () => {
      const { container } = render(
        <FileExplorer taskId="t1" tree={TREE_ENTRIES} treeError={null} treeLoading={false} />,
      );
      const dirRows = container.querySelectorAll(".fe-tree-row.dir");
      const srcRow = Array.from(dirRows).find((r) =>
        r.querySelector(".fe-tree-name")?.textContent === "src/",
      )!;
      fireEvent.click(srcRow);
      fireEvent.click(srcRow);
      expect(getTreeNames(container)).toContain("main.py");
    });

    it("toggles directory via keyboard Enter", () => {
      const { container } = render(
        <FileExplorer taskId="t1" tree={TREE_ENTRIES} treeError={null} treeLoading={false} />,
      );
      const dirRows = container.querySelectorAll(".fe-tree-row.dir");
      const srcRow = Array.from(dirRows).find((r) =>
        r.querySelector(".fe-tree-name")?.textContent === "src/",
      )!;
      fireEvent.keyDown(srcRow, { key: "Enter" });
      expect(getTreeNames(container)).not.toContain("main.py");
    });
  });

  // ---------------------------------------------------------------------------
  // File selection
  // ---------------------------------------------------------------------------

  describe("file selection", () => {
    it("shows placeholder when no file selected", () => {
      const { container } = render(
        <FileExplorer taskId="t1" tree={TREE_ENTRIES} treeError={null} treeLoading={false} />,
      );
      expect(container.querySelector(".fe-content-placeholder")).toBeTruthy();
    });

    it("opens file content viewer on file click", async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ content: "hello world", diff: null, status: null, error: null }),
      });
      vi.stubGlobal("fetch", mockFetch);

      const { container } = render(
        <FileExplorer taskId="t1" tree={TREE_ENTRIES} treeError={null} treeLoading={false} />,
      );

      // Click the README.md file row
      const fileRows = container.querySelectorAll(".fe-tree-row:not(.dir)");
      const readmeRow = Array.from(fileRows).find((r) =>
        r.querySelector(".fe-tree-name")?.textContent === "README.md",
      )!;
      fireEvent.click(readmeRow);

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalled();
      });
    });

    it("selects file via keyboard Enter", async () => {
      vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ content: "code", diff: null, status: null, error: null }),
      }));

      const { container } = render(
        <FileExplorer taskId="t1" tree={TREE_ENTRIES} treeError={null} treeLoading={false} />,
      );

      const fileRows = container.querySelectorAll(".fe-tree-row:not(.dir)");
      const readmeRow = Array.from(fileRows).find((r) =>
        r.querySelector(".fe-tree-name")?.textContent === "README.md",
      )!;
      fireEvent.keyDown(readmeRow, { key: "Enter" });

      await waitFor(() => {
        expect(container.querySelector(".fe-content-placeholder")).toBeNull();
      });
    });
  });

  // ---------------------------------------------------------------------------
  // File content viewer
  // ---------------------------------------------------------------------------

  describe("file content viewer", () => {
    /** Helper to click the README.md file row. */
    function clickReadme(container: HTMLElement) {
      const fileRows = container.querySelectorAll(".fe-tree-row:not(.dir)");
      const readmeRow = Array.from(fileRows).find((r) =>
        r.querySelector(".fe-tree-name")?.textContent === "README.md",
      )!;
      fireEvent.click(readmeRow);
    }

    it("shows source content after fetch", async () => {
      vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ content: "print('hello')", diff: null, status: null, error: null }),
      }));

      const { container } = render(
        <FileExplorer taskId="t1" tree={TREE_ENTRIES} treeError={null} treeLoading={false} />,
      );
      clickReadme(container);

      await waitFor(() => {
        expect(container.querySelector(".fe-source-table")).toBeTruthy();
        expect(container.textContent).toContain("print('hello')");
      });
    });

    it("shows error on fetch failure", async () => {
      vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
      }));

      const { container } = render(
        <FileExplorer taskId="t1" tree={TREE_ENTRIES} treeError={null} treeLoading={false} />,
      );
      clickReadme(container);

      await waitFor(() => {
        expect(container.querySelector(".fe-content-error")?.textContent).toBe("HTTP 500");
      });
    });

    it("shows error on network exception", async () => {
      vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("network")));

      const { container } = render(
        <FileExplorer taskId="t1" tree={TREE_ENTRIES} treeError={null} treeLoading={false} />,
      );
      clickReadme(container);

      await waitFor(() => {
        expect(container.querySelector(".fe-content-error")?.textContent).toBe("Failed to fetch");
      });
    });

    it("shows diff view when file has diff", async () => {
      vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({
          content: "new_line",
          diff: "@@ -1,1 +1,1 @@\n-old\n+new",
          status: "modified",
          error: null,
        }),
      }));

      const { container } = render(
        <FileExplorer taskId="t1" tree={TREE_ENTRIES} treeError={null} treeLoading={false} />,
      );
      clickReadme(container);

      await waitFor(() => {
        const diffTab = container.querySelector('[aria-selected="true"]');
        expect(diffTab?.textContent).toBe("Diff");
      });
    });

    it("shows view toggle between source and diff", async () => {
      vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({
          content: "line1",
          diff: "@@ -1,1 +1,1 @@\n-old\n+new",
          status: "modified",
          error: null,
        }),
      }));

      const { container } = render(
        <FileExplorer taskId="t1" tree={TREE_ENTRIES} treeError={null} treeLoading={false} />,
      );
      clickReadme(container);

      await waitFor(() => {
        expect(container.querySelector(".fe-view-toggle")).toBeTruthy();
      });

      // Switch to source view
      const sourceBtn = container.querySelector('.fe-view-btn:not(.active)')!;
      fireEvent.click(sourceBtn);
      await waitFor(() => {
        expect(container.querySelector(".fe-source-table")).toBeTruthy();
      });
    });

    it("closes file viewer on close button", async () => {
      vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ content: "code", diff: null, status: null, error: null }),
      }));

      const { container } = render(
        <FileExplorer taskId="t1" tree={TREE_ENTRIES} treeError={null} treeLoading={false} />,
      );
      clickReadme(container);

      await waitFor(() => {
        expect(container.querySelector(".fe-close-btn")).toBeTruthy();
      });

      fireEvent.click(container.querySelector(".fe-close-btn")!);
      expect(container.querySelector(".fe-content-placeholder")).toBeTruthy();
    });

    it("shows no-content message when both content and diff are null", async () => {
      vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ content: null, diff: null, status: null, error: null }),
      }));

      const { container } = render(
        <FileExplorer taskId="t1" tree={TREE_ENTRIES} treeError={null} treeLoading={false} />,
      );
      clickReadme(container);

      await waitFor(() => {
        expect(container.querySelector(".fe-content-error")?.textContent).toBe("No content available");
      });
    });
  });

  // ---------------------------------------------------------------------------
  // Filter
  // ---------------------------------------------------------------------------

  describe("filter", () => {
    it("filters files by text input", () => {
      const { container } = render(
        <FileExplorer taskId="t1" tree={TREE_ENTRIES} treeError={null} treeLoading={false} />,
      );
      const filterInput = container.querySelector(".fe-tree-filter")!;
      fireEvent.change(filterInput, { target: { value: "main" } });

      const names = getTreeNames(container);
      expect(names).toContain("main.py");
      expect(names).toContain("test_main.py");
      expect(names).not.toContain("README.md");
      expect(names).not.toContain("utils.py");
    });

    it("shows no matching files message", () => {
      const { container } = render(
        <FileExplorer taskId="t1" tree={TREE_ENTRIES} treeError={null} treeLoading={false} />,
      );
      const filterInput = container.querySelector(".fe-tree-filter")!;
      fireEvent.change(filterInput, { target: { value: "nonexistent" } });

      expect(container.querySelector(".fe-tree-empty")?.textContent).toBe("No matching files");
    });

    it("is case-insensitive", () => {
      const { container } = render(
        <FileExplorer taskId="t1" tree={TREE_ENTRIES} treeError={null} treeLoading={false} />,
      );
      const filterInput = container.querySelector(".fe-tree-filter")!;
      fireEvent.change(filterInput, { target: { value: "README" } });

      expect(getTreeNames(container)).toContain("README.md");
    });
  });

  // ---------------------------------------------------------------------------
  // Changes-only toggle
  // ---------------------------------------------------------------------------

  describe("changes-only toggle", () => {
    it("shows only changed files when active", () => {
      const { container } = render(
        <FileExplorer taskId="t1" tree={TREE_ENTRIES} treeError={null} treeLoading={false} />,
      );
      const changesBtn = container.querySelector(".fe-changes-btn")!;
      fireEvent.click(changesBtn);

      const names = getTreeNames(container);
      expect(names).toContain("main.py");
      expect(names).toContain("test_main.py");
      expect(names).not.toContain("utils.py");
      expect(names).not.toContain("README.md");
    });

    it("toggles back to show all files", () => {
      const { container } = render(
        <FileExplorer taskId="t1" tree={TREE_ENTRIES} treeError={null} treeLoading={false} />,
      );
      const changesBtn = container.querySelector(".fe-changes-btn")!;
      fireEvent.click(changesBtn);
      fireEvent.click(changesBtn);

      const names = getTreeNames(container);
      expect(names).toContain("README.md");
      expect(names).toContain("utils.py");
    });
  });
});
