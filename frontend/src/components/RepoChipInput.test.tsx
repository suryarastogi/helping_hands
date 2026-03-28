import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render } from "@testing-library/react";

import RepoChipInput from "./RepoChipInput";

afterEach(cleanup);

function setup(overrides: Partial<Parameters<typeof RepoChipInput>[0]> = {}) {
  const onChange = vi.fn();
  const props = {
    value: [] as string[],
    onChange,
    suggestions: ["owner/repo-a", "owner/repo-b", "other/lib"],
    ...overrides,
  };
  const result = render(<RepoChipInput {...props} />);
  const input = result.getByRole("textbox", { name: overrides.ariaLabel ?? "Reference repos" });
  return { ...result, input, onChange };
}

/** Simulate typing into the chip input via fireEvent.change. */
function typeInInput(input: HTMLElement, text: string) {
  fireEvent.change(input, { target: { value: text } });
}

describe("RepoChipInput", () => {
  it("renders the input with placeholder when no chips", () => {
    const { getByPlaceholderText } = setup();
    expect(getByPlaceholderText("owner/repo")).toBeTruthy();
  });

  it("hides placeholder when chips are present", () => {
    const { input } = setup({ value: ["foo/bar"] });
    expect(input.getAttribute("placeholder")).toBe("");
  });

  it("renders existing chips with remove buttons", () => {
    const { container } = setup({ value: ["owner/repo-a", "other/lib"] });
    const chips = container.querySelectorAll(".repo-chip");
    expect(chips.length).toBe(2);
    expect(chips[0].textContent).toContain("owner/repo-a");
    expect(chips[1].textContent).toContain("other/lib");
  });

  it("adds a chip on Enter key", () => {
    const { input, onChange } = setup();
    typeInInput(input, "new/repo");
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onChange).toHaveBeenCalledWith(["new/repo"]);
  });

  it("adds a chip on Tab key", () => {
    const { input, onChange } = setup();
    typeInInput(input, "new/repo");
    fireEvent.keyDown(input, { key: "Tab" });
    expect(onChange).toHaveBeenCalledWith(["new/repo"]);
  });

  it("adds a chip on comma key", () => {
    const { input, onChange } = setup();
    typeInInput(input, "new/repo");
    fireEvent.keyDown(input, { key: "," });
    expect(onChange).toHaveBeenCalledWith(["new/repo"]);
  });

  it("does not add empty or whitespace-only chip", () => {
    const { input, onChange } = setup();
    typeInInput(input, "   ");
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onChange).not.toHaveBeenCalled();
  });

  it("does not add duplicate chip", () => {
    const { input, onChange } = setup({ value: ["owner/repo-a"] });
    typeInInput(input, "owner/repo-a");
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onChange).not.toHaveBeenCalled();
  });

  it("removes chip on × button click", () => {
    const { getByRole, onChange } = setup({ value: ["owner/repo-a", "other/lib"] });
    const removeBtn = getByRole("button", { name: "Remove owner/repo-a" });
    fireEvent.click(removeBtn);
    expect(onChange).toHaveBeenCalledWith(["other/lib"]);
  });

  it("removes last chip on Backspace when input is empty", () => {
    const { input, onChange } = setup({ value: ["owner/repo-a", "other/lib"] });
    fireEvent.keyDown(input, { key: "Backspace" });
    expect(onChange).toHaveBeenCalledWith(["owner/repo-a"]);
  });

  it("does not remove chip on Backspace when input has text", () => {
    const { input, onChange } = setup({ value: ["owner/repo-a"] });
    typeInInput(input, "x");
    fireEvent.keyDown(input, { key: "Backspace" });
    expect(onChange).not.toHaveBeenCalled();
  });

  it("shows suggestion dropdown on focus", () => {
    const { input, container } = setup();
    fireEvent.focus(input);
    expect(container.querySelector(".repo-chip-dropdown")).toBeTruthy();
  });

  it("filters suggestions by input text", () => {
    const { input, container } = setup();
    typeInInput(input, "repo-a");
    const options = container.querySelectorAll(".repo-chip-option");
    expect(options.length).toBe(1);
    expect(options[0].textContent).toBe("owner/repo-a");
  });

  it("excludes already-selected repos from suggestions", () => {
    const { input, container } = setup({ value: ["owner/repo-a"] });
    fireEvent.focus(input);
    const options = container.querySelectorAll(".repo-chip-option");
    const texts = Array.from(options).map((o) => o.textContent);
    expect(texts).not.toContain("owner/repo-a");
  });

  it("navigates suggestions with ArrowDown/ArrowUp", () => {
    const { input, container } = setup();
    fireEvent.focus(input);
    fireEvent.keyDown(input, { key: "ArrowDown" });
    let highlighted = container.querySelector(".repo-chip-option.highlighted");
    expect(highlighted?.textContent).toBe("owner/repo-a");

    fireEvent.keyDown(input, { key: "ArrowDown" });
    highlighted = container.querySelector(".repo-chip-option.highlighted");
    expect(highlighted?.textContent).toBe("owner/repo-b");

    fireEvent.keyDown(input, { key: "ArrowUp" });
    highlighted = container.querySelector(".repo-chip-option.highlighted");
    expect(highlighted?.textContent).toBe("owner/repo-a");
  });

  it("selects highlighted suggestion on Enter", () => {
    const { input, onChange } = setup();
    fireEvent.focus(input);
    fireEvent.keyDown(input, { key: "ArrowDown" });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onChange).toHaveBeenCalledWith(["owner/repo-a"]);
  });

  it("closes dropdown on Escape", () => {
    const { input, container } = setup();
    fireEvent.focus(input);
    expect(container.querySelector(".repo-chip-dropdown")).toBeTruthy();
    fireEvent.keyDown(input, { key: "Escape" });
    expect(container.querySelector(".repo-chip-dropdown")).toBeFalsy();
  });

  it("adds suggestion on mouse click", () => {
    const { input, container, onChange } = setup();
    fireEvent.focus(input);
    const option = container.querySelector(".repo-chip-option")!;
    fireEvent.mouseDown(option);
    expect(onChange).toHaveBeenCalledWith(["owner/repo-a"]);
  });

  it("highlights suggestion on mouse enter", () => {
    const { input, container } = setup();
    fireEvent.focus(input);
    const options = container.querySelectorAll(".repo-chip-option");
    fireEvent.mouseEnter(options[1]);
    expect(options[1].classList.contains("highlighted")).toBe(true);
  });

  it("closes dropdown on outside click", () => {
    const { input, container } = setup();
    fireEvent.focus(input);
    expect(container.querySelector(".repo-chip-dropdown")).toBeTruthy();
    fireEvent.mouseDown(document.body);
    expect(container.querySelector(".repo-chip-dropdown")).toBeFalsy();
  });

  it("focuses input when chip container is clicked", () => {
    const { input, container } = setup();
    const chipContainer = container.querySelector(".repo-chip-container")!;
    fireEvent.click(chipContainer);
    expect(document.activeElement).toBe(input);
  });

  it("limits dropdown to 8 suggestions", () => {
    const manySuggestions = Array.from({ length: 12 }, (_, i) => `org/repo-${i}`);
    const { input, container } = setup({ suggestions: manySuggestions });
    fireEvent.focus(input);
    const options = container.querySelectorAll(".repo-chip-option");
    expect(options.length).toBe(8);
  });

  it("lets Tab pass through when input is empty and no highlight", () => {
    const { input, onChange } = setup();
    fireEvent.keyDown(input, { key: "Tab" });
    expect(onChange).not.toHaveBeenCalled();
  });

  it("uses custom ariaLabel and placeholder", () => {
    const { getByPlaceholderText, getByRole } = setup({
      ariaLabel: "Custom label",
      placeholder: "custom placeholder",
    });
    expect(getByRole("textbox", { name: "Custom label" })).toBeTruthy();
    expect(getByPlaceholderText("custom placeholder")).toBeTruthy();
  });

  it("trims whitespace from chip values", () => {
    const { input, onChange } = setup();
    typeInInput(input, "  new/repo  ");
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onChange).toHaveBeenCalledWith(["new/repo"]);
  });

  it("clears input after adding a chip via suggestion", () => {
    const { input } = setup();
    typeInInput(input, "repo-a");
    fireEvent.keyDown(input, { key: "ArrowDown" });
    fireEvent.keyDown(input, { key: "Enter" });
    expect((input as HTMLInputElement).value).toBe("");
  });
});
