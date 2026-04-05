import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, fireEvent } from "@testing-library/react";

import DiffView from "./DiffView";

afterEach(cleanup);
import type { DiffFile } from "./DiffView";

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const SAMPLE_DIFF = [
  "diff --git a/foo.py b/foo.py",
  "index abc..def 100644",
  "--- a/foo.py",
  "+++ b/foo.py",
  "@@ -1,3 +1,4 @@",
  " import os",
  "-old_line",
  "+new_line",
  "+added_line",
  " unchanged",
].join("\n");

const modifiedFile: DiffFile = {
  filename: "foo.py",
  status: "modified",
  diff: SAMPLE_DIFF,
};

const addedFile: DiffFile = {
  filename: "bar.py",
  status: "added",
  diff: "@@ -0,0 +1,2 @@\n+line1\n+line2",
};

const deletedFile: DiffFile = {
  filename: "baz.py",
  status: "deleted",
  diff: "@@ -1,2 +0,0 @@\n-line1\n-line2",
};

const renamedFile: DiffFile = {
  filename: "qux.py",
  status: "renamed",
  diff: "@@ -1,1 +1,1 @@\n-old\n+new",
};

// ---------------------------------------------------------------------------
// Loading / Error / Empty states
// ---------------------------------------------------------------------------

describe("DiffView", () => {
  describe("loading state", () => {
    it("shows loading spinner when loading with no files", () => {
      const { container } = render(
        <DiffView files={[]} error={null} loading={true} />,
      );
      expect(container.querySelector(".diff-loading")).toBeTruthy();
      expect(container.textContent).toContain("Loading diff");
    });

    it("shows files with spinner when loading with existing files", () => {
      const { container } = render(
        <DiffView files={[modifiedFile]} error={null} loading={true} />,
      );
      // Should render the file, not the loading state
      expect(container.querySelector(".diff-loading")).toBeNull();
      expect(container.querySelector(".diff-spinner")).toBeTruthy();
      expect(container.textContent).toContain("foo.py");
    });
  });

  describe("error state", () => {
    it("shows error message when error with no files", () => {
      const { container } = render(
        <DiffView files={[]} error="Something broke" loading={false} />,
      );
      expect(container.querySelector(".diff-empty")).toBeTruthy();
      expect(container.textContent).toContain("Something broke");
    });

    it("shows files when error with existing files", () => {
      const { container } = render(
        <DiffView files={[modifiedFile]} error="Stale" loading={false} />,
      );
      expect(container.textContent).toContain("foo.py");
    });
  });

  describe("empty state", () => {
    it("shows no-changes message when no files and no error", () => {
      const { container } = render(
        <DiffView files={[]} error={null} loading={false} />,
      );
      expect(container.querySelector(".diff-empty")).toBeTruthy();
      expect(container.textContent).toContain("No uncommitted changes");
    });
  });

  // ---------------------------------------------------------------------------
  // File rendering & status badges
  // ---------------------------------------------------------------------------

  describe("file rendering", () => {
    it("renders file headers with filename and status badge", () => {
      const { container } = render(
        <DiffView files={[modifiedFile, addedFile, deletedFile, renamedFile]} error={null} loading={false} />,
      );
      const badges = container.querySelectorAll(".diff-status-badge");
      expect(badges).toHaveLength(4);
      expect(badges[0].textContent).toBe("M");
      expect(badges[1].textContent).toBe("A");
      expect(badges[2].textContent).toBe("D");
      expect(badges[3].textContent).toBe("R");
    });

    it("renders filenames in headers", () => {
      const { container } = render(
        <DiffView files={[modifiedFile, addedFile]} error={null} loading={false} />,
      );
      const filenames = container.querySelectorAll(".diff-filename");
      const names = Array.from(filenames).map((el) => el.textContent);
      expect(names).toContain("foo.py");
      expect(names).toContain("bar.py");
    });

    it("applies distinct colors per status", () => {
      const { container } = render(
        <DiffView files={[modifiedFile, addedFile, deletedFile, renamedFile]} error={null} loading={false} />,
      );
      const badges = container.querySelectorAll(".diff-status-badge");
      // modified = blue, added = green, deleted = red, renamed = yellow
      // Colors are rendered as rgb() values in the DOM
      expect(badges[0].getAttribute("style")).toContain("color:");
      expect(badges[1].getAttribute("style")).toContain("color:");
      expect(badges[2].getAttribute("style")).toContain("color:");
      expect(badges[3].getAttribute("style")).toContain("color:");
      // Each badge should have a different color
      const colors = Array.from(badges).map((b) => b.getAttribute("style"));
      const unique = new Set(colors);
      expect(unique.size).toBe(4);
    });
  });

  // ---------------------------------------------------------------------------
  // Diff line parsing
  // ---------------------------------------------------------------------------

  describe("diff parsing", () => {
    it("renders add/del/context lines with correct markers", () => {
      const { container } = render(
        <DiffView files={[modifiedFile]} error={null} loading={false} />,
      );
      const markers = container.querySelectorAll(".diff-line-marker");
      const markerTexts = Array.from(markers).map((m) => m.textContent?.trim());
      // hunk marker @@, context " ", del "-", add "+", add "+", context " "
      expect(markerTexts).toContain("@@");
      expect(markerTexts).toContain("+");
      expect(markerTexts).toContain("-");
    });

    it("renders line numbers for add/context lines", () => {
      const { container } = render(
        <DiffView files={[modifiedFile]} error={null} loading={false} />,
      );
      // New-line column should have numbers
      const newNums = container.querySelectorAll(".diff-line-num-new");
      const numTexts = Array.from(newNums)
        .map((n) => n.textContent?.trim())
        .filter(Boolean);
      expect(numTexts.length).toBeGreaterThan(0);
    });

    it("renders hunk header lines", () => {
      const { container } = render(
        <DiffView files={[modifiedFile]} error={null} loading={false} />,
      );
      const hunkLines = container.querySelectorAll(".diff-line-hunk");
      expect(hunkLines.length).toBeGreaterThanOrEqual(1);
    });

    it("does not render header lines in the table", () => {
      const { container } = render(
        <DiffView files={[modifiedFile]} error={null} loading={false} />,
      );
      // Header lines (diff --git, index, ---/+++) should be filtered out
      const headerLines = container.querySelectorAll(".diff-line-header");
      expect(headerLines).toHaveLength(0);
    });
  });

  // ---------------------------------------------------------------------------
  // Stats
  // ---------------------------------------------------------------------------

  describe("stats display", () => {
    it("shows per-file add/del stats", () => {
      const { container } = render(
        <DiffView files={[modifiedFile]} error={null} loading={false} />,
      );
      const addStats = container.querySelectorAll(".diff-stat-add");
      const delStats = container.querySelectorAll(".diff-stat-del");
      // Both summary and per-file stats
      expect(addStats.length).toBeGreaterThanOrEqual(1);
      expect(delStats.length).toBeGreaterThanOrEqual(1);
    });

    it("shows total summary for multiple files", () => {
      const { container } = render(
        <DiffView files={[modifiedFile, addedFile]} error={null} loading={false} />,
      );
      const summary = container.querySelector(".diff-summary")!;
      expect(summary.textContent).toContain("2 files changed");
    });

    it("uses singular for single file", () => {
      const { container } = render(
        <DiffView files={[modifiedFile]} error={null} loading={false} />,
      );
      const summary = container.querySelector(".diff-summary")!;
      expect(summary.textContent).toContain("1 file changed");
    });
  });

  // ---------------------------------------------------------------------------
  // Collapse toggle
  // ---------------------------------------------------------------------------

  describe("collapse toggle", () => {
    it("starts expanded (shows diff table)", () => {
      const { container } = render(
        <DiffView files={[modifiedFile]} error={null} loading={false} />,
      );
      expect(container.querySelector(".diff-file-body")).toBeTruthy();
      expect(container.querySelector(".diff-collapse-icon")!.textContent).toBe("▼");
    });

    it("collapses on header click", () => {
      const { container } = render(
        <DiffView files={[modifiedFile]} error={null} loading={false} />,
      );
      const header = container.querySelector(".diff-file-header")!;
      fireEvent.click(header);
      expect(container.querySelector(".diff-file-body")).toBeNull();
      expect(container.querySelector(".diff-collapse-icon")!.textContent).toBe("▶");
    });

    it("re-expands on second click", () => {
      const { container } = render(
        <DiffView files={[modifiedFile]} error={null} loading={false} />,
      );
      const header = container.querySelector(".diff-file-header")!;
      fireEvent.click(header);
      fireEvent.click(header);
      expect(container.querySelector(".diff-file-body")).toBeTruthy();
    });

    it("toggles via keyboard Enter", () => {
      const { container } = render(
        <DiffView files={[modifiedFile]} error={null} loading={false} />,
      );
      const header = container.querySelector(".diff-file-header")!;
      fireEvent.keyDown(header, { key: "Enter" });
      expect(container.querySelector(".diff-file-body")).toBeNull();
    });

    it("toggles via keyboard Space", () => {
      const { container } = render(
        <DiffView files={[modifiedFile]} error={null} loading={false} />,
      );
      const header = container.querySelector(".diff-file-header")!;
      fireEvent.keyDown(header, { key: " " });
      expect(container.querySelector(".diff-file-body")).toBeNull();
    });
  });
});
