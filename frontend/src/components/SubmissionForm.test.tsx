import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";

import SubmissionForm from "./SubmissionForm";
import { INITIAL_FORM, BACKEND_OPTIONS, backendDisplayName } from "../App.utils";
import type { FormState } from "../types";

afterEach(cleanup);

function renderForm(overrides?: Partial<{
  form: FormState;
  onFieldChange: ReturnType<typeof vi.fn>;
  onSubmit: ReturnType<typeof vi.fn>;
}>) {
  const props = {
    form: overrides?.form ?? { ...INITIAL_FORM },
    onFieldChange: overrides?.onFieldChange ?? vi.fn(),
    onSubmit: overrides?.onSubmit ?? vi.fn(),
  };
  return { ...render(<SubmissionForm {...props} />), ...props };
}

describe("SubmissionForm", () => {
  it("renders repo path and prompt inputs", () => {
    renderForm();
    expect(screen.getByLabelText("Repository path")).toBeInTheDocument();
    expect(screen.getByLabelText("Task prompt")).toBeInTheDocument();
  });

  it("renders Run submit button", () => {
    renderForm();
    expect(screen.getByRole("button", { name: "Run" })).toBeInTheDocument();
  });

  it("displays form values from props", () => {
    const form = { ...INITIAL_FORM, repo_path: "my/repo", prompt: "do stuff" };
    renderForm({ form });
    expect(screen.getByLabelText("Repository path")).toHaveValue("my/repo");
    expect(screen.getByLabelText("Task prompt")).toHaveValue("do stuff");
  });

  it("calls onFieldChange when repo path changes", () => {
    const onFieldChange = vi.fn();
    renderForm({ onFieldChange });
    fireEvent.change(screen.getByLabelText("Repository path"), {
      target: { value: "new/repo" },
    });
    expect(onFieldChange).toHaveBeenCalledWith("repo_path", "new/repo");
  });

  it("calls onFieldChange when prompt changes", () => {
    const onFieldChange = vi.fn();
    renderForm({ onFieldChange });
    fireEvent.change(screen.getByLabelText("Task prompt"), {
      target: { value: "new prompt" },
    });
    expect(onFieldChange).toHaveBeenCalledWith("prompt", "new prompt");
  });

  it("calls onSubmit when form is submitted", () => {
    const onSubmit = vi.fn((e) => e.preventDefault());
    renderForm({ onSubmit });
    fireEvent.click(screen.getByRole("button", { name: "Run" }));
    expect(onSubmit).toHaveBeenCalledTimes(1);
  });

  it("renders Advanced details section (collapsed by default)", () => {
    renderForm();
    expect(screen.getByText("Advanced")).toBeInTheDocument();
  });

  it("renders all backend options in the select", () => {
    renderForm();
    const options = screen.getAllByRole("option");
    for (const backend of BACKEND_OPTIONS) {
      expect(options.find((o) => o.textContent === backendDisplayName(backend))).toBeTruthy();
    }
  });

  it("calls onFieldChange for backend select", () => {
    const onFieldChange = vi.fn();
    renderForm({ onFieldChange });
    const select = screen.getByDisplayValue(backendDisplayName(INITIAL_FORM.backend));
    fireEvent.change(select, { target: { value: "e2e" } });
    expect(onFieldChange).toHaveBeenCalledWith("backend", "e2e");
  });

  it("calls onFieldChange for checkbox toggles", () => {
    const onFieldChange = vi.fn();
    renderForm({ onFieldChange });
    const nopr = screen.getByLabelText("No PR");
    fireEvent.click(nopr);
    expect(onFieldChange).toHaveBeenCalledWith("no_pr", true);
  });

  it("calls onFieldChange for execution checkbox", () => {
    const onFieldChange = vi.fn();
    renderForm({ onFieldChange });
    fireEvent.click(screen.getByLabelText("Execution"));
    expect(onFieldChange).toHaveBeenCalledWith("enable_execution", true);
  });

  it("calls onFieldChange for web checkbox", () => {
    const onFieldChange = vi.fn();
    renderForm({ onFieldChange });
    fireEvent.click(screen.getByLabelText("Web"));
    expect(onFieldChange).toHaveBeenCalledWith("enable_web", true);
  });

  it("calls onFieldChange for native auth checkbox", () => {
    const onFieldChange = vi.fn();
    renderForm({ onFieldChange });
    fireEvent.click(screen.getByLabelText("Native auth"));
    expect(onFieldChange).toHaveBeenCalledWith("use_native_cli_auth", true);
  });

  it("calls onFieldChange for fix CI checkbox", () => {
    const onFieldChange = vi.fn();
    renderForm({ onFieldChange });
    fireEvent.click(screen.getByLabelText("Fix CI"));
    expect(onFieldChange).toHaveBeenCalledWith("fix_ci", true);
  });

  it("renders password input for GitHub token", () => {
    renderForm();
    const tokenInputs = screen.getAllByPlaceholderText("ghp_... (optional)");
    expect(tokenInputs.length).toBeGreaterThanOrEqual(1);
    expect(tokenInputs[0]).toHaveAttribute("type", "password");
  });

  it("renders reference repos chip input", () => {
    renderForm();
    expect(
      screen.getByLabelText("Reference repos")
    ).toBeInTheDocument();
  });

  it("renders max iterations input with form value", () => {
    const form = { ...INITIAL_FORM, max_iterations: 10 };
    renderForm({ form });
    const input = screen.getByDisplayValue("10");
    expect(input).toHaveAttribute("type", "number");
  });
});
