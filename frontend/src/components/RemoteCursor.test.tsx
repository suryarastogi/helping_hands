import { describe, expect, it } from "vitest";
import { render } from "@testing-library/react";

import RemoteCursor from "./RemoteCursor";

describe("RemoteCursor component", () => {
  it("renders with correct position and aria-label", () => {
    const { container } = render(
      <RemoteCursor name="Alice" color="#e11d48" x={30} y={40} />
    );
    const cursor = container.querySelector(".remote-cursor")!;
    expect(cursor).toBeTruthy();
    expect(cursor.getAttribute("aria-label")).toBe("Alice's cursor");
    expect(cursor.style.left).toBe("30%");
    expect(cursor.style.top).toBe("40%");
  });

  it("renders the player name label", () => {
    const { container } = render(
      <RemoteCursor name="Bob" color="#2563eb" x={50} y={60} />
    );
    const label = container.querySelector(".remote-cursor-label")!;
    expect(label).toBeTruthy();
    expect(label.textContent).toBe("Bob");
    expect(label.style.backgroundColor).toBe("rgb(37, 99, 235)");
  });

  it("renders the SVG cursor arrow", () => {
    const { container } = render(
      <RemoteCursor name="Charlie" color="#16a34a" x={10} y={20} />
    );
    const svg = container.querySelector(".remote-cursor-arrow");
    expect(svg).toBeTruthy();
    const path = svg?.querySelector("path");
    expect(path?.getAttribute("fill")).toBe("#16a34a");
  });

  it("SVG arrow is aria-hidden to avoid redundant announcements", () => {
    const { container } = render(
      <RemoteCursor name="Alice" color="#e11d48" x={30} y={40} />
    );
    const svg = container.querySelector(".remote-cursor-arrow");
    expect(svg?.getAttribute("aria-hidden")).toBe("true");
  });
});
