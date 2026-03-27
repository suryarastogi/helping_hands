import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render } from "@testing-library/react";

import RepoSuggestInput from "./RepoSuggestInput";

afterEach(cleanup);

function setup(overrides: Partial<Parameters<typeof RepoSuggestInput>[0]> = {}) {
  const onChange = vi.fn();
  const props = {
    value: "",
    onChange,
    suggestions: ["owner/repo-a", "owner/repo-b", "other/lib"],
    ...overrides,
  };
  const result = render(<RepoSuggestInput {...props} />);
  const input = result.getByRole("textbox", { name: overrides.ariaLabel ?? "Repository path" });
  return { ...result, input, onChange };
}

describe("RepoSuggestInput", () => {
  it("renders the input with default placeholder", () => {
    const { getByPlaceholderText } = setup();
    expect(getByPlaceholderText("owner/repo")).toBeTruthy();
  });

  it("renders with custom className and required attribute", () => {
    const { input } = setup({ className: "custom-cls", required: true });
    expect(input.classList.contains("custom-cls")).toBe(true);
    expect(input.hasAttribute("required")).toBe(true);
  });

  it("calls onChange when text is typed", () => {
    const { input, onChange } = setup();
    fireEvent.change(input, { target: { value: "a" } });
    expect(onChange).toHaveBeenCalledWith("a");
  });

  it("shows suggestion dropdown on focus", () => {
    const { input, container } = setup();
    fireEvent.focus(input);
    expect(container.querySelector(".repo-chip-dropdown")).toBeTruthy();
  });

  it("filters suggestions by current value", () => {
    const { container, getByRole } = setup({ value: "repo-a" });
    fireEvent.focus(getByRole("textbox"));
    const options = container.querySelectorAll(".repo-chip-option");
    expect(options.length).toBe(1);
    expect(options[0].textContent).toBe("owner/repo-a");
  });

  it("shows all suggestions when value is empty", () => {
    const { input, container } = setup({ value: "" });
    fireEvent.focus(input);
    const options = container.querySelectorAll(".repo-chip-option");
    expect(options.length).toBe(3);
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
    expect(onChange).toHaveBeenCalledWith("owner/repo-a");
  });

  it("does not select on Enter without highlight", () => {
    const { input, onChange } = setup();
    fireEvent.focus(input);
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onChange).not.toHaveBeenCalledWith("owner/repo-a");
  });

  it("closes dropdown on Escape", () => {
    const { input, container } = setup();
    fireEvent.focus(input);
    expect(container.querySelector(".repo-chip-dropdown")).toBeTruthy();
    fireEvent.keyDown(input, { key: "Escape" });
    expect(container.querySelector(".repo-chip-dropdown")).toBeFalsy();
  });

  it("selects suggestion on mouse click", () => {
    const { input, container, onChange } = setup();
    fireEvent.focus(input);
    const option = container.querySelector(".repo-chip-option")!;
    fireEvent.mouseDown(option);
    expect(onChange).toHaveBeenCalledWith("owner/repo-a");
  });

  it("hides dropdown after mouse selection", () => {
    const { input, container } = setup();
    fireEvent.focus(input);
    const option = container.querySelector(".repo-chip-option")!;
    fireEvent.mouseDown(option);
    expect(container.querySelector(".repo-chip-dropdown")).toBeFalsy();
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

  it("limits dropdown to 8 suggestions", () => {
    const manySuggestions = Array.from({ length: 12 }, (_, i) => `org/repo-${i}`);
    const { input, container } = setup({ suggestions: manySuggestions });
    fireEvent.focus(input);
    const options = container.querySelectorAll(".repo-chip-option");
    expect(options.length).toBe(8);
  });

  it("ArrowDown opens dropdown when closed", () => {
    const { input, container } = setup();
    fireEvent.keyDown(input, { key: "ArrowDown" });
    expect(container.querySelector(".repo-chip-dropdown")).toBeTruthy();
  });

  it("uses custom ariaLabel and placeholder", () => {
    const { getByPlaceholderText, getByRole } = setup({
      ariaLabel: "Custom label",
      placeholder: "custom placeholder",
    });
    expect(getByRole("textbox", { name: "Custom label" })).toBeTruthy();
    expect(getByPlaceholderText("custom placeholder")).toBeTruthy();
  });

  it("has autoComplete off", () => {
    const { input } = setup();
    expect(input.getAttribute("autocomplete")).toBe("off");
  });

  it("resets highlight index when typing", () => {
    const { input, container } = setup();
    fireEvent.focus(input);
    fireEvent.keyDown(input, { key: "ArrowDown" });
    expect(container.querySelector(".repo-chip-option.highlighted")).toBeTruthy();
    // Typing resets the highlight — onChange fires and showDropdown stays true
    fireEvent.change(input, { target: { value: "owner" } });
    expect(container.querySelector(".repo-chip-option.highlighted")).toBeFalsy();
  });
});
