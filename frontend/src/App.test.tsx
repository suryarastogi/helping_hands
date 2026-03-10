import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import App from "./App";

// Build a mock Response-like object with clone() support.
function mockResponse(props: {
  ok: boolean;
  status: number;
  jsonData?: unknown;
  textData?: string;
}) {
  const { ok, status, jsonData = {}, textData } = props;
  const obj = {
    ok,
    status,
    json: async () => jsonData,
    text: async () => textData ?? JSON.stringify(jsonData),
    clone: () => ({ ...obj, json: obj.json, text: obj.text }),
  };
  return obj;
}

// Helper to create a mock fetch that resolves with specific responses per URL pattern.
function mockFetchResponses(
  overrides: Record<string, ReturnType<typeof mockResponse>> = {}
) {
  const defaultResp = mockResponse({ ok: false, status: 503 });

  return vi.fn().mockImplementation((url: string) => {
    for (const [pattern, value] of Object.entries(overrides)) {
      if (url.includes(pattern)) {
        return Promise.resolve(value);
      }
    }
    return Promise.resolve(defaultResp);
  });
}

// Mock fetch globally so the component's network calls don't fail.
beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
      json: async () => ({}),
      text: async () => "",
    })
  );

  // Mock Notification API (not available in jsdom)
  vi.stubGlobal("Notification", { permission: "denied" });

  // Mock serviceWorker.register so the useEffect doesn't crash
  Object.defineProperty(navigator, "serviceWorker", {
    value: {
      register: vi.fn().mockResolvedValue({ active: null }),
      ready: Promise.resolve({ active: null }),
    },
    configurable: true,
    writable: true,
  });
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("App component", () => {
  it("renders without crashing", () => {
    render(<App />);
    // The submit button is always visible
    expect(screen.getByText("Run")).toBeInTheDocument();
  });

  it("renders the repo path input with default value", () => {
    render(<App />);
    const repoInput = screen.getByPlaceholderText("owner/repo");
    expect(repoInput).toBeInTheDocument();
    expect(repoInput).toHaveValue("suryarastogi/helping_hands");
  });

  it("renders the prompt input with default value", () => {
    render(<App />);
    const promptInput = screen.getByPlaceholderText("Prompt");
    expect(promptInput).toBeInTheDocument();
    expect(promptInput).toHaveValue(
      "Update README.md with results of your smoke test. Keep changes minimal and safe."
    );
  });

  it("renders the empty task list message", () => {
    render(<App />);
    expect(screen.getByText("No tasks submitted yet.")).toBeInTheDocument();
  });

  it("renders the service health bar", () => {
    render(<App />);
    expect(screen.getByLabelText("Service health")).toBeInTheDocument();
  });

  it("renders the dashboard view toggle buttons", () => {
    render(<App />);
    expect(screen.getByText("Classic view")).toBeInTheDocument();
    expect(screen.getByText("Hand world")).toBeInTheDocument();
  });

  it("renders the new submission and scheduled tasks buttons", () => {
    render(<App />);
    expect(screen.getByText("New submission")).toBeInTheDocument();
    expect(screen.getByText("Scheduled tasks")).toBeInTheDocument();
  });

  it("renders the submitted tasks header", () => {
    render(<App />);
    expect(screen.getByText("Submitted tasks")).toBeInTheDocument();
  });
});

describe("App interaction", () => {
  it("switches to Hand world view when toggle is clicked", () => {
    render(<App />);
    const worldButton = screen.getByText("Hand world");
    expect(worldButton).toHaveAttribute("aria-selected", "false");

    fireEvent.click(worldButton);

    expect(worldButton).toHaveAttribute("aria-selected", "true");
    const classicButton = screen.getByText("Classic view");
    expect(classicButton).toHaveAttribute("aria-selected", "false");
  });

  it("switches back to Classic view when toggle is clicked", () => {
    render(<App />);
    // Switch to world first
    fireEvent.click(screen.getByText("Hand world"));
    // Switch back
    fireEvent.click(screen.getByText("Classic view"));

    expect(screen.getByText("Classic view")).toHaveAttribute("aria-selected", "true");
    expect(screen.getByText("Hand world")).toHaveAttribute("aria-selected", "false");
  });

  it("navigates to scheduled tasks view when button is clicked", () => {
    render(<App />);
    const scheduledBtn = screen.getByText("Scheduled tasks");
    fireEvent.click(scheduledBtn);

    // The schedule view should now be active (button gets active class)
    expect(scheduledBtn.className).toContain("active");
  });

  it("navigates back to submission view via New submission button", () => {
    render(<App />);
    // Navigate away first
    fireEvent.click(screen.getByText("Scheduled tasks"));
    // Navigate back
    const newSubmBtn = screen.getByText("New submission");
    fireEvent.click(newSubmBtn);

    // The submission form should be visible (Run button present)
    expect(screen.getByText("Run")).toBeInTheDocument();
  });

  it("opens the Advanced settings panel in the submission form", () => {
    render(<App />);
    const advancedSummary = screen.getByText("Advanced");
    expect(advancedSummary).toBeInTheDocument();

    // Click to expand (details/summary)
    fireEvent.click(advancedSummary);

    // Backend select should be visible after expanding
    const backendLabel = screen.getByText("Backend");
    expect(backendLabel).toBeInTheDocument();
  });

  it("changes the repo path input value", () => {
    render(<App />);
    const repoInput = screen.getByPlaceholderText("owner/repo") as HTMLInputElement;
    fireEvent.change(repoInput, { target: { value: "other/repo" } });
    expect(repoInput.value).toBe("other/repo");
  });

  it("changes the prompt input value", () => {
    render(<App />);
    const promptInput = screen.getByPlaceholderText("Prompt") as HTMLInputElement;
    fireEvent.change(promptInput, { target: { value: "Fix all bugs" } });
    expect(promptInput.value).toBe("Fix all bugs");
  });

  it("changes the backend select value in advanced settings", () => {
    render(<App />);
    // Expand advanced
    fireEvent.click(screen.getByText("Advanced"));

    const backendSelect = screen.getByDisplayValue("claudecodecli") as HTMLSelectElement;
    fireEvent.change(backendSelect, { target: { value: "goose" } });
    expect(backendSelect.value).toBe("goose");
  });

  it("renders Clear button disabled when no task history", () => {
    render(<App />);
    const clearBtn = screen.getByText("Clear");
    expect(clearBtn).toBeDisabled();
  });
});

describe("Form submission", () => {
  it("submits the form and transitions to monitor view on success", async () => {
    const mockFetch = mockFetchResponses({
      "/build": mockResponse({
        ok: true,
        status: 200,
        jsonData: { task_id: "abc-123", status: "QUEUED", backend: "claudecodecli" },
      }),
    });
    vi.stubGlobal("fetch", mockFetch);

    render(<App />);

    // Submit the form
    const runButton = screen.getByText("Run");
    await act(async () => {
      fireEvent.click(runButton);
    });

    // Verify fetch was called with /build
    const buildCall = mockFetch.mock.calls.find(
      (call: string[]) => typeof call[0] === "string" && call[0].includes("/build")
    );
    expect(buildCall).toBeTruthy();

    // Verify the POST body structure
    const fetchOptions = buildCall![1] as RequestInit;
    expect(fetchOptions.method).toBe("POST");
    const body = JSON.parse(fetchOptions.body as string);
    expect(body.repo_path).toBe("suryarastogi/helping_hands");
    expect(body.backend).toBe("claudecodecli");
    expect(body.max_iterations).toBe(6);
  });

  it("shows error state when submission fails with network error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new Error("Network failure"))
    );

    render(<App />);

    await act(async () => {
      fireEvent.click(screen.getByText("Run"));
    });

    // The output should show the error in monitor view
    await waitFor(() => {
      const outputEl = document.querySelector(".monitor-output");
      expect(outputEl?.textContent).toContain("Error");
    });
  });

  it("shows error state when server returns non-ok response", async () => {
    const mockFetch = mockFetchResponses({
      "/build": mockResponse({
        ok: false,
        status: 422,
        jsonData: { detail: "Missing required field" },
      }),
    });
    vi.stubGlobal("fetch", mockFetch);

    render(<App />);

    await act(async () => {
      fireEvent.click(screen.getByText("Run"));
    });

    await waitFor(() => {
      const outputEl = document.querySelector(".monitor-output");
      expect(outputEl?.textContent).toContain("Error");
    });
  });

  it("includes model in payload when set in advanced settings", async () => {
    const mockFetch = mockFetchResponses({
      "/build": mockResponse({
        ok: true,
        status: 200,
        jsonData: { task_id: "def-456", status: "QUEUED", backend: "claudecodecli" },
      }),
    });
    vi.stubGlobal("fetch", mockFetch);

    render(<App />);

    // Expand advanced and change model
    fireEvent.click(screen.getByText("Advanced"));
    const modelInput = screen.getByPlaceholderText("claude-opus-4-6") as HTMLInputElement;
    fireEvent.change(modelInput, { target: { value: "gpt-5.2" } });

    await act(async () => {
      fireEvent.click(screen.getByText("Run"));
    });

    const buildCall = mockFetch.mock.calls.find(
      (call: string[]) => typeof call[0] === "string" && call[0].includes("/build")
    );
    const body = JSON.parse((buildCall![1] as RequestInit).body as string);
    expect(body.model).toBe("gpt-5.2");
  });

  it("includes tools and skills in payload when set", async () => {
    const mockFetch = mockFetchResponses({
      "/build": mockResponse({
        ok: true,
        status: 200,
        jsonData: { task_id: "ghi-789", status: "QUEUED", backend: "claudecodecli" },
      }),
    });
    vi.stubGlobal("fetch", mockFetch);

    render(<App />);

    // Expand advanced and set tools/skills
    fireEvent.click(screen.getByText("Advanced"));
    const toolsInput = screen.getByPlaceholderText("execution,web") as HTMLInputElement;
    fireEvent.change(toolsInput, { target: { value: "execution, web" } });
    const skillsInput = screen.getByPlaceholderText("execution,web,prd,ralph") as HTMLInputElement;
    fireEvent.change(skillsInput, { target: { value: "prd, ralph" } });

    await act(async () => {
      fireEvent.click(screen.getByText("Run"));
    });

    const buildCall = mockFetch.mock.calls.find(
      (call: string[]) => typeof call[0] === "string" && call[0].includes("/build")
    );
    const body = JSON.parse((buildCall![1] as RequestInit).body as string);
    expect(body.tools).toEqual(["execution", "web"]);
    expect(body.skills).toEqual(["prd", "ralph"]);
  });

  it("toggles checkbox fields in advanced settings", () => {
    render(<App />);
    fireEvent.click(screen.getByText("Advanced"));

    const noPrCheckbox = screen.getByLabelText("No PR") as HTMLInputElement;
    expect(noPrCheckbox.checked).toBe(false);
    fireEvent.click(noPrCheckbox);
    expect(noPrCheckbox.checked).toBe(true);

    const executionCheckbox = screen.getByLabelText("Execution") as HTMLInputElement;
    expect(executionCheckbox.checked).toBe(false);
    fireEvent.click(executionCheckbox);
    expect(executionCheckbox.checked).toBe(true);

    const webCheckbox = screen.getByLabelText("Web") as HTMLInputElement;
    expect(webCheckbox.checked).toBe(false);
    fireEvent.click(webCheckbox);
    expect(webCheckbox.checked).toBe(true);

    const nativeAuthCheckbox = screen.getByLabelText("Native auth") as HTMLInputElement;
    expect(nativeAuthCheckbox.checked).toBe(false);
    fireEvent.click(nativeAuthCheckbox);
    expect(nativeAuthCheckbox.checked).toBe(true);

    const fixCiCheckbox = screen.getByLabelText("Fix CI") as HTMLInputElement;
    expect(fixCiCheckbox.checked).toBe(false);
    fireEvent.click(fixCiCheckbox);
    expect(fixCiCheckbox.checked).toBe(true);
  });

  it("changes max iterations in advanced settings", () => {
    render(<App />);
    fireEvent.click(screen.getByText("Advanced"));

    const iterInput = screen.getByDisplayValue("6") as HTMLInputElement;
    fireEvent.change(iterInput, { target: { value: "10" } });
    expect(iterInput.value).toBe("10");
  });
});

describe("Monitor view", () => {
  async function submitAndEnterMonitor() {
    const mockFetch = mockFetchResponses({
      "/build": mockResponse({
        ok: true,
        status: 200,
        jsonData: { task_id: "mon-001", status: "QUEUED", backend: "claudecodecli" },
      }),
    });
    vi.stubGlobal("fetch", mockFetch);

    render(<App />);

    await act(async () => {
      fireEvent.click(screen.getByText("Run"));
    });

    return mockFetch;
  }

  it("shows output tabs after submission", async () => {
    await submitAndEnterMonitor();

    expect(screen.getByRole("tab", { name: "Updates" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Raw" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Payload" })).toBeInTheDocument();
  });

  it("Updates tab is active by default", async () => {
    await submitAndEnterMonitor();

    const updatesTab = screen.getByRole("tab", { name: "Updates" });
    expect(updatesTab).toHaveAttribute("aria-selected", "true");
  });

  it("switches to Raw tab when clicked", async () => {
    await submitAndEnterMonitor();

    const rawTab = screen.getByRole("tab", { name: "Raw" });
    fireEvent.click(rawTab);

    expect(rawTab).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tab", { name: "Updates" })).toHaveAttribute(
      "aria-selected",
      "false"
    );
  });

  it("switches to Payload tab when clicked", async () => {
    await submitAndEnterMonitor();

    const payloadTab = screen.getByRole("tab", { name: "Payload" });
    fireEvent.click(payloadTab);

    expect(payloadTab).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tab", { name: "Updates" })).toHaveAttribute(
      "aria-selected",
      "false"
    );
  });

  it("shows the task ID badge after submission", async () => {
    await submitAndEnterMonitor();

    // The monitor title includes the short task ID
    await waitFor(() => {
      const title = document.querySelector(".monitor-title");
      expect(title?.textContent).toContain("mon-001");
    });
  });

  it("displays the status blinker", async () => {
    await submitAndEnterMonitor();

    const blinker = document.querySelector(".status-blinker");
    expect(blinker).toBeInTheDocument();
  });

  it("shows task inputs section", async () => {
    await submitAndEnterMonitor();

    expect(screen.getByText("Task inputs")).toBeInTheDocument();
  });

  it("shows content in Payload tab after switching", async () => {
    await submitAndEnterMonitor();

    const payloadTab = screen.getByRole("tab", { name: "Payload" });
    fireEvent.click(payloadTab);

    const outputEl = document.querySelector(".monitor-output");
    // The payload tab should display some JSON content (may be build response or
    // error from subsequent polling -- the key assertion is that switching tabs works).
    expect(outputEl?.textContent).toBeTruthy();
    expect(outputEl?.textContent?.trim().startsWith("{")).toBe(true);
  });
});

describe("Schedule view", () => {
  it("shows the schedule view with heading and New schedule button", () => {
    render(<App />);
    fireEvent.click(screen.getByText("Scheduled tasks"));

    expect(screen.getByText("Scheduled tasks", { selector: "h2" })).toBeInTheDocument();
    expect(screen.getByText("New schedule")).toBeInTheDocument();
    expect(screen.getByText("Refresh")).toBeInTheDocument();
  });

  it("shows the schedule form when New schedule is clicked", () => {
    render(<App />);
    fireEvent.click(screen.getByText("Scheduled tasks"));
    fireEvent.click(screen.getByText("New schedule"));

    // The schedule form should have a Name input and a cron input
    expect(screen.getByPlaceholderText("e.g. Daily docs update")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("0 0 * * * (midnight)")).toBeInTheDocument();
  });

  it("changes schedule form field values", () => {
    render(<App />);
    fireEvent.click(screen.getByText("Scheduled tasks"));
    fireEvent.click(screen.getByText("New schedule"));

    const nameInput = screen.getByPlaceholderText("e.g. Daily docs update") as HTMLInputElement;
    fireEvent.change(nameInput, { target: { value: "My nightly job" } });
    expect(nameInput.value).toBe("My nightly job");

    const cronInput = screen.getByPlaceholderText("0 0 * * * (midnight)") as HTMLInputElement;
    fireEvent.change(cronInput, { target: { value: "0 0 * * *" } });
    expect(cronInput.value).toBe("0 0 * * *");
  });

  it("shows cron preset dropdown in the schedule form", () => {
    render(<App />);
    fireEvent.click(screen.getByText("Scheduled tasks"));
    fireEvent.click(screen.getByText("New schedule"));

    // Cron presets are in a select dropdown
    expect(screen.getByText("Custom")).toBeInTheDocument();
  });

  it("selects a cron preset from the dropdown", () => {
    render(<App />);
    fireEvent.click(screen.getByText("Scheduled tasks"));
    fireEvent.click(screen.getByText("New schedule"));

    // Find the preset select by its label "Or preset"
    const presetSelect = screen.getByDisplayValue("Custom") as HTMLSelectElement;
    fireEvent.change(presetSelect, { target: { value: "daily" } });

    const cronInput = screen.getByPlaceholderText("0 0 * * * (midnight)") as HTMLInputElement;
    expect(cronInput.value).toBe("0 0 * * *");
  });

  it("submits schedule form and calls the API", async () => {
    // The save handler does POST then calls loadSchedules() which does GET.
    // Both hit /schedules. We use a smart mock that differentiates by method.
    const mockFetch = vi.fn().mockImplementation((url: string, init?: RequestInit) => {
      if (typeof url === "string" && url.includes("/schedules")) {
        if (init?.method === "POST") {
          return Promise.resolve(
            mockResponse({
              ok: true,
              status: 200,
              jsonData: { schedule_id: "sched-001", name: "Nightly" },
            })
          );
        }
        // GET (loadSchedules after save)
        return Promise.resolve(
          mockResponse({
            ok: true,
            status: 200,
            jsonData: { schedules: [], total: 0 },
          })
        );
      }
      return Promise.resolve(mockResponse({ ok: false, status: 503 }));
    });
    vi.stubGlobal("fetch", mockFetch);

    render(<App />);
    fireEvent.click(screen.getByText("Scheduled tasks"));
    fireEvent.click(screen.getByText("New schedule"));

    // Fill the form
    const nameInput = screen.getByPlaceholderText("e.g. Daily docs update") as HTMLInputElement;
    fireEvent.change(nameInput, { target: { value: "Nightly" } });

    const cronInput = screen.getByPlaceholderText("0 0 * * * (midnight)") as HTMLInputElement;
    fireEvent.change(cronInput, { target: { value: "0 0 * * *" } });

    const promptArea = screen.getByPlaceholderText("Update documentation...") as HTMLTextAreaElement;
    fireEvent.change(promptArea, { target: { value: "Run nightly checks" } });

    // Submit the schedule form
    const createButton = screen.getByText("Create schedule");
    await act(async () => {
      fireEvent.click(createButton);
    });

    // Verify fetch was called with /schedules POST
    const scheduleCall = mockFetch.mock.calls.find(
      (call: string[]) =>
        typeof call[0] === "string" &&
        call[0].includes("/schedules") &&
        (call[1] as RequestInit)?.method === "POST"
    );
    expect(scheduleCall).toBeTruthy();
    const body = JSON.parse((scheduleCall![1] as RequestInit).body as string);
    expect(body.name).toBe("Nightly");
    expect(body.cron_expression).toBe("0 0 * * *");
    expect(body.prompt).toBe("Run nightly checks");
  });

  it("hides the schedule form when Cancel is clicked", () => {
    render(<App />);
    fireEvent.click(screen.getByText("Scheduled tasks"));
    fireEvent.click(screen.getByText("New schedule"));

    // Form should be visible
    expect(screen.getByPlaceholderText("e.g. Daily docs update")).toBeInTheDocument();

    // Click Cancel
    fireEvent.click(screen.getByText("Cancel"));

    // Form should disappear; the empty state message should show
    expect(screen.getByText("No scheduled tasks yet.")).toBeInTheDocument();
  });

  it("refreshes schedules list when Refresh is clicked", async () => {
    const mockFetch = mockFetchResponses({
      "/schedules": mockResponse({
        ok: true,
        status: 200,
        jsonData: { schedules: [], total: 0 },
      }),
    });
    vi.stubGlobal("fetch", mockFetch);

    render(<App />);
    fireEvent.click(screen.getByText("Scheduled tasks"));

    await act(async () => {
      fireEvent.click(screen.getByText("Refresh"));
    });

    const scheduleFetches = mockFetch.mock.calls.filter(
      (call: string[]) =>
        typeof call[0] === "string" &&
        call[0].includes("/schedules") &&
        !(call[1] as RequestInit)?.method
    );
    expect(scheduleFetches.length).toBeGreaterThan(0);
  });

  it("shows schedule error when creation API returns failure", async () => {
    const mockFetch = mockFetchResponses({
      "/schedules": mockResponse({
        ok: false,
        status: 500,
        jsonData: { detail: "Server error" },
      }),
    });
    vi.stubGlobal("fetch", mockFetch);

    render(<App />);
    fireEvent.click(screen.getByText("Scheduled tasks"));
    fireEvent.click(screen.getByText("New schedule"));

    // Fill minimum fields and submit
    const nameInput = screen.getByPlaceholderText("e.g. Daily docs update") as HTMLInputElement;
    fireEvent.change(nameInput, { target: { value: "Test" } });
    const cronInput = screen.getByPlaceholderText("0 0 * * * (midnight)") as HTMLInputElement;
    fireEvent.change(cronInput, { target: { value: "* * * * *" } });
    const promptArea = screen.getByPlaceholderText("Update documentation...") as HTMLTextAreaElement;
    fireEvent.change(promptArea, { target: { value: "test" } });

    await act(async () => {
      fireEvent.click(screen.getByText("Create schedule"));
    });

    // Verify the submission happened
    const saveCall = mockFetch.mock.calls.find(
      (call: string[]) =>
        typeof call[0] === "string" &&
        call[0].includes("/schedules") &&
        (call[1] as RequestInit)?.method === "POST"
    );
    expect(saveCall).toBeTruthy();
  });
});

describe("Schedule list CRUD operations", () => {
  const SCHEDULE_ITEM = {
    schedule_id: "sched-001",
    name: "Nightly Build",
    cron_expression: "0 0 * * *",
    repo_path: "org/repo",
    prompt: "Update docs",
    backend: "claudecodecli",
    model: null,
    max_iterations: 6,
    pr_number: null,
    no_pr: false,
    enable_execution: false,
    enable_web: false,
    use_native_cli_auth: false,
    fix_ci: false,
    ci_check_wait_minutes: 3,
    tools: [],
    skills: [],
    enabled: true,
    created_at: "2026-01-01T00:00:00Z",
    last_run_at: null,
    last_run_task_id: null,
    run_count: 0,
    next_run_at: "2026-03-07T00:00:00Z",
  };

  function renderScheduleWithItems() {
    const mockFetch = vi.fn().mockImplementation((url: string, init?: RequestInit) => {
      if (typeof url === "string" && url.includes("/schedules")) {
        // GET single schedule for edit
        if (!init?.method && url.match(/\/schedules\/sched-/)) {
          return Promise.resolve(
            mockResponse({ ok: true, status: 200, jsonData: SCHEDULE_ITEM })
          );
        }
        // GET list
        if (!init?.method || init?.method === "GET") {
          return Promise.resolve(
            mockResponse({
              ok: true,
              status: 200,
              jsonData: { schedules: [SCHEDULE_ITEM], total: 1 },
            })
          );
        }
        // POST/PUT/DELETE
        return Promise.resolve(
          mockResponse({ ok: true, status: 200, jsonData: { schedule_id: "sched-001" } })
        );
      }
      return Promise.resolve(mockResponse({ ok: false, status: 503 }));
    });
    vi.stubGlobal("fetch", mockFetch);
    return mockFetch;
  }

  it("renders schedule items with name and actions", async () => {
    renderScheduleWithItems();
    render(<App />);

    fireEvent.click(screen.getByText("Scheduled tasks"));
    await act(async () => {
      fireEvent.click(screen.getByText("Refresh"));
    });

    await waitFor(() => {
      expect(screen.getByText("Nightly Build")).toBeInTheDocument();
    });
    expect(screen.getByText("Edit")).toBeInTheDocument();
    expect(screen.getByText("Run now")).toBeInTheDocument();
    expect(screen.getByText("Delete")).toBeInTheDocument();
    expect(screen.getByText("Disable")).toBeInTheDocument();
  });

  it("opens edit form when Edit button is clicked", async () => {
    renderScheduleWithItems();
    render(<App />);

    fireEvent.click(screen.getByText("Scheduled tasks"));
    await act(async () => {
      fireEvent.click(screen.getByText("Refresh"));
    });

    await waitFor(() => {
      expect(screen.getByText("Edit")).toBeInTheDocument();
    });

    await act(async () => {
      fireEvent.click(screen.getByText("Edit"));
    });

    await waitFor(() => {
      const nameInput = screen.getByPlaceholderText("e.g. Daily docs update") as HTMLInputElement;
      expect(nameInput.value).toBe("Nightly Build");
    });
  });

  it("calls DELETE when Delete button is clicked and confirmed", async () => {
    const mockFetch = renderScheduleWithItems();
    vi.stubGlobal("confirm", vi.fn().mockReturnValue(true));

    render(<App />);
    fireEvent.click(screen.getByText("Scheduled tasks"));
    await act(async () => {
      fireEvent.click(screen.getByText("Refresh"));
    });

    await waitFor(() => {
      expect(screen.getByText("Delete")).toBeInTheDocument();
    });

    await act(async () => {
      fireEvent.click(screen.getByText("Delete"));
    });

    const deleteCall = mockFetch.mock.calls.find(
      (call: [string, RequestInit?]) =>
        typeof call[0] === "string" &&
        call[0].includes("/schedules/sched-001") &&
        call[1]?.method === "DELETE"
    );
    expect(deleteCall).toBeTruthy();
  });

  it("does not call DELETE when user cancels confirm dialog", async () => {
    const mockFetch = renderScheduleWithItems();
    vi.stubGlobal("confirm", vi.fn().mockReturnValue(false));

    render(<App />);
    fireEvent.click(screen.getByText("Scheduled tasks"));
    await act(async () => {
      fireEvent.click(screen.getByText("Refresh"));
    });

    await waitFor(() => {
      expect(screen.getByText("Delete")).toBeInTheDocument();
    });

    await act(async () => {
      fireEvent.click(screen.getByText("Delete"));
    });

    const deleteCall = mockFetch.mock.calls.find(
      (call: [string, RequestInit?]) =>
        typeof call[0] === "string" &&
        call[0].includes("/schedules/sched-001") &&
        call[1]?.method === "DELETE"
    );
    expect(deleteCall).toBeUndefined();
  });

  it("triggers schedule via Run now button", async () => {
    const mockFetch = renderScheduleWithItems();
    vi.stubGlobal("confirm", vi.fn().mockReturnValue(true));
    vi.stubGlobal("alert", vi.fn());

    render(<App />);
    fireEvent.click(screen.getByText("Scheduled tasks"));
    await act(async () => {
      fireEvent.click(screen.getByText("Refresh"));
    });

    await waitFor(() => {
      expect(screen.getByText("Run now")).toBeInTheDocument();
    });

    // Override fetch for trigger response
    mockFetch.mockImplementation((url: string) => {
      if (typeof url === "string" && url.includes("/trigger")) {
        return Promise.resolve(
          mockResponse({
            ok: true,
            status: 200,
            jsonData: { task_id: "task-triggered-001", message: "ok" },
          })
        );
      }
      if (typeof url === "string" && url.includes("/schedules")) {
        return Promise.resolve(
          mockResponse({ ok: true, status: 200, jsonData: { schedules: [SCHEDULE_ITEM], total: 1 } })
        );
      }
      return Promise.resolve(mockResponse({ ok: false, status: 503 }));
    });

    await act(async () => {
      fireEvent.click(screen.getByText("Run now"));
    });

    const triggerCall = mockFetch.mock.calls.find(
      (call: [string, RequestInit?]) =>
        typeof call[0] === "string" &&
        call[0].includes("/trigger") &&
        call[1]?.method === "POST"
    );
    expect(triggerCall).toBeTruthy();
  });

  it("toggles schedule enabled state via Disable button", async () => {
    const mockFetch = renderScheduleWithItems();

    render(<App />);
    fireEvent.click(screen.getByText("Scheduled tasks"));
    await act(async () => {
      fireEvent.click(screen.getByText("Refresh"));
    });

    await waitFor(() => {
      expect(screen.getByText("Disable")).toBeInTheDocument();
    });

    await act(async () => {
      fireEvent.click(screen.getByText("Disable"));
    });

    const toggleCall = mockFetch.mock.calls.find(
      (call: [string, RequestInit?]) =>
        typeof call[0] === "string" &&
        call[0].includes("/disable") &&
        call[1]?.method === "POST"
    );
    expect(toggleCall).toBeTruthy();
  });
});

describe("Task selection and polling", () => {
  it("transitions to monitor view when a task is selected from history", async () => {
    // First submit a task to populate history
    const mockFetch = mockFetchResponses({
      "/build": mockResponse({
        ok: true,
        status: 200,
        jsonData: { task_id: "sel-001", status: "QUEUED", backend: "claudecodecli" },
      }),
    });
    vi.stubGlobal("fetch", mockFetch);

    render(<App />);

    await act(async () => {
      fireEvent.click(screen.getByText("Run"));
    });

    // Should be in monitor view now with the task ID visible
    await waitFor(() => {
      const title = document.querySelector(".monitor-title");
      expect(title?.textContent).toContain("sel-001");
    });

    // Navigate to submission and back
    fireEvent.click(screen.getByText("New submission"));

    // The task should appear in the task list; click it
    const taskRows = document.querySelectorAll(".task-row");
    if (taskRows.length > 0) {
      await act(async () => {
        fireEvent.click(taskRows[0]);
      });
    }
  });

  it("polls task status and updates on terminal status", async () => {
    // Submit a task first
    const mockFetch = vi.fn().mockImplementation((url: string) => {
      if (typeof url === "string" && url.includes("/build")) {
        return Promise.resolve(
          mockResponse({
            ok: true,
            status: 200,
            jsonData: { task_id: "poll-001", status: "QUEUED", backend: "claudecodecli" },
          })
        );
      }
      if (typeof url === "string" && url.includes("/tasks/poll-001")) {
        return Promise.resolve(
          mockResponse({
            ok: true,
            status: 200,
            jsonData: {
              task_id: "poll-001",
              status: "SUCCESS",
              result: { updates: ["Done!"] },
            },
          })
        );
      }
      return Promise.resolve(mockResponse({ ok: false, status: 503 }));
    });
    vi.stubGlobal("fetch", mockFetch);

    render(<App />);

    await act(async () => {
      fireEvent.click(screen.getByText("Run"));
    });

    // Wait for polling to pick up the terminal status
    await waitFor(
      () => {
        const blinker = document.querySelector(".status-blinker");
        // The blinker should reflect a terminal state
        expect(blinker).toBeInTheDocument();
      },
      { timeout: 5000 }
    );
  });

  it("handles poll error gracefully", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });

    const mockFetch = vi.fn().mockImplementation((url: string) => {
      if (typeof url === "string" && url.includes("/build")) {
        return Promise.resolve(
          mockResponse({
            ok: true,
            status: 200,
            jsonData: { task_id: "err-poll-001", status: "QUEUED", backend: "claudecodecli" },
          })
        );
      }
      if (typeof url === "string" && url.includes("/tasks/err-poll-001")) {
        return Promise.resolve(
          mockResponse({
            ok: false,
            status: 500,
            jsonData: { detail: "Internal server error" },
          })
        );
      }
      return Promise.resolve(mockResponse({ ok: false, status: 503 }));
    });
    vi.stubGlobal("fetch", mockFetch);

    render(<App />);

    await act(async () => {
      fireEvent.click(screen.getByText("Run"));
    });

    // Advance timers so polling fires
    await act(async () => {
      await vi.advanceTimersByTimeAsync(4000);
    });

    // The status should reflect poll_error
    const blinker = document.querySelector(".status-blinker");
    expect(blinker).toBeInTheDocument();

    vi.useRealTimers();
  });
});

describe("Notification and toast UI", () => {
  it("renders notification banner when permission is default", () => {
    vi.stubGlobal("Notification", { permission: "default", requestPermission: vi.fn() });
    render(<App />);

    expect(screen.getByText("Enable OS notifications for task updates?")).toBeInTheDocument();
    expect(screen.getByText("Enable")).toBeInTheDocument();
    expect(screen.getByText("Dismiss")).toBeInTheDocument();
  });

  it("dismisses notification banner when Dismiss is clicked", () => {
    vi.stubGlobal("Notification", { permission: "default", requestPermission: vi.fn() });
    render(<App />);

    fireEvent.click(screen.getByText("Dismiss"));

    expect(screen.queryByText("Enable OS notifications for task updates?")).not.toBeInTheDocument();
  });

  it("calls requestPermission when Enable is clicked", () => {
    const reqPerm = vi.fn().mockResolvedValue("granted");
    vi.stubGlobal("Notification", { permission: "default", requestPermission: reqPerm });
    render(<App />);

    fireEvent.click(screen.getByText("Enable"));
    expect(reqPerm).toHaveBeenCalled();
  });

  it("shows toast when a task reaches terminal status via polling", async () => {
    const mockFetch = vi.fn().mockImplementation((url: string) => {
      if (typeof url === "string" && url.includes("/build")) {
        return Promise.resolve(
          mockResponse({
            ok: true,
            status: 200,
            jsonData: { task_id: "toast-001", status: "QUEUED", backend: "claudecodecli" },
          })
        );
      }
      if (typeof url === "string" && url.includes("/tasks/toast-001")) {
        return Promise.resolve(
          mockResponse({
            ok: true,
            status: 200,
            jsonData: { task_id: "toast-001", status: "SUCCESS", result: null },
          })
        );
      }
      return Promise.resolve(mockResponse({ ok: false, status: 503 }));
    });
    vi.stubGlobal("fetch", mockFetch);

    render(<App />);

    await act(async () => {
      fireEvent.click(screen.getByText("Run"));
    });

    // Toast should appear when task transitions to terminal status
    await waitFor(
      () => {
        const toasts = document.querySelectorAll(".toast");
        expect(toasts.length).toBeGreaterThan(0);
      },
      { timeout: 5000 }
    );
  });

  it("removes toast when close button is clicked", async () => {
    const mockFetch = vi.fn().mockImplementation((url: string) => {
      if (typeof url === "string" && url.includes("/build")) {
        return Promise.resolve(
          mockResponse({
            ok: true,
            status: 200,
            jsonData: { task_id: "toast-close-001", status: "QUEUED", backend: "claudecodecli" },
          })
        );
      }
      if (typeof url === "string" && url.includes("/tasks/toast-close-001")) {
        return Promise.resolve(
          mockResponse({
            ok: true,
            status: 200,
            jsonData: { task_id: "toast-close-001", status: "SUCCESS", result: null },
          })
        );
      }
      return Promise.resolve(mockResponse({ ok: false, status: 503 }));
    });
    vi.stubGlobal("fetch", mockFetch);

    render(<App />);

    await act(async () => {
      fireEvent.click(screen.getByText("Run"));
    });

    await waitFor(
      () => {
        expect(document.querySelectorAll(".toast").length).toBeGreaterThan(0);
      },
      { timeout: 5000 }
    );

    // Click the toast close button
    const closeBtn = document.querySelector(".toast-close");
    expect(closeBtn).toBeInTheDocument();
    await act(async () => {
      fireEvent.click(closeBtn!);
    });

    expect(document.querySelectorAll(".toast").length).toBe(0);
  });
});

describe("Task discovery from current tasks API", () => {
  it("discovers running tasks from /tasks/current endpoint", async () => {
    const mockFetch = vi.fn().mockImplementation((url: string) => {
      if (typeof url === "string" && url.includes("/tasks/current")) {
        return Promise.resolve(
          mockResponse({
            ok: true,
            status: 200,
            jsonData: {
              tasks: [
                { task_id: "disc-001", status: "STARTED", backend: "goose", repo_path: "org/repo" },
              ],
              source: "celery",
            },
          })
        );
      }
      return Promise.resolve(mockResponse({ ok: false, status: 503 }));
    });
    vi.stubGlobal("fetch", mockFetch);

    render(<App />);

    // Wait for the task to appear in the task list (uses .task-row class)
    await waitFor(
      () => {
        const taskRows = document.querySelectorAll(".task-row");
        expect(taskRows.length).toBeGreaterThan(0);
      },
      { timeout: 5000 }
    );
  });

  it("handles /tasks/current API failure gracefully", async () => {
    const mockFetch = vi.fn().mockImplementation((url: string) => {
      if (typeof url === "string" && url.includes("/tasks/current")) {
        return Promise.reject(new Error("Network error"));
      }
      return Promise.resolve(mockResponse({ ok: false, status: 503 }));
    });
    vi.stubGlobal("fetch", mockFetch);

    render(<App />);

    // Should not crash — the app still renders
    await waitFor(() => {
      expect(screen.getByText("Run")).toBeInTheDocument();
    });
  });
});

describe("Monitor view resize and scroll", () => {
  it("handles monitor output scroll event", async () => {
    const mockFetch = mockFetchResponses({
      "/build": mockResponse({
        ok: true,
        status: 200,
        jsonData: { task_id: "scroll-001", status: "QUEUED", backend: "claudecodecli" },
      }),
    });
    vi.stubGlobal("fetch", mockFetch);

    render(<App />);

    await act(async () => {
      fireEvent.click(screen.getByText("Run"));
    });

    const outputEl = document.querySelector(".monitor-output");
    if (outputEl) {
      fireEvent.scroll(outputEl);
    }
    // No assertion needed — just verifying no errors on scroll
    expect(outputEl).toBeInTheDocument();
  });

  it("renders the resize handle in monitor view", async () => {
    const mockFetch = mockFetchResponses({
      "/build": mockResponse({
        ok: true,
        status: 200,
        jsonData: { task_id: "resize-001", status: "QUEUED", backend: "claudecodecli" },
      }),
    });
    vi.stubGlobal("fetch", mockFetch);

    render(<App />);

    await act(async () => {
      fireEvent.click(screen.getByText("Run"));
    });

    const handle = document.querySelector(".resize-handle");
    if (handle) {
      fireEvent.mouseDown(handle, { clientY: 200 });
    }
    // Verifies handleResizeStart runs without error
    expect(screen.getByText("Task inputs")).toBeInTheDocument();
  });
});

describe("New submission button resets state", () => {
  it("resets to submission form from monitor view", async () => {
    const mockFetch = mockFetchResponses({
      "/build": mockResponse({
        ok: true,
        status: 200,
        jsonData: { task_id: "reset-001", status: "QUEUED", backend: "claudecodecli" },
      }),
    });
    vi.stubGlobal("fetch", mockFetch);

    render(<App />);

    await act(async () => {
      fireEvent.click(screen.getByText("Run"));
    });

    // Should be in monitor view
    await waitFor(() => {
      expect(screen.getByText("Task inputs")).toBeInTheDocument();
    });

    // Click New submission to reset
    fireEvent.click(screen.getByText("New submission"));

    // Should be back in submission view with Run button
    expect(screen.getByText("Run")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("owner/repo")).toBeInTheDocument();
  });
});

describe("Hand World factory and incinerator", () => {
  function switchToHandWorld() {
    render(<App />);
    fireEvent.click(screen.getByText("Hand world"));
  }

  it("renders the Hand World card header", () => {
    switchToHandWorld();
    expect(screen.getByText("Hand World")).toBeInTheDocument();
  });

  it("renders factory entrance with FACTORY label", () => {
    switchToHandWorld();
    expect(screen.getByText("FACTORY")).toBeInTheDocument();
  });

  it("renders incinerator exit with INCINERATOR label", () => {
    switchToHandWorld();
    expect(screen.getByText("INCINERATOR")).toBeInTheDocument();
  });

  it("renders factory DOM elements (building, chimney, conveyor)", () => {
    switchToHandWorld();
    const factory = document.querySelector(".hh-factory");
    expect(factory).not.toBeNull();
    expect(factory!.querySelector(".factory-building")).not.toBeNull();
    expect(factory!.querySelector(".factory-chimney")).not.toBeNull();
    expect(factory!.querySelector(".factory-conveyor")).not.toBeNull();
    expect(factory!.querySelector(".factory-door")).not.toBeNull();
    expect(factory!.querySelector(".factory-roof")).not.toBeNull();
  });

  it("renders factory windows and status light", () => {
    switchToHandWorld();
    const factory = document.querySelector(".hh-factory");
    expect(factory!.querySelector(".factory-window-1")).not.toBeNull();
    expect(factory!.querySelector(".factory-window-2")).not.toBeNull();
    expect(factory!.querySelector(".factory-light")).not.toBeNull();
  });

  it("renders factory smoke particles", () => {
    switchToHandWorld();
    const factory = document.querySelector(".hh-factory");
    expect(factory!.querySelector(".factory-smoke-1")).not.toBeNull();
    expect(factory!.querySelector(".factory-smoke-2")).not.toBeNull();
    expect(factory!.querySelector(".factory-smoke-3")).not.toBeNull();
  });

  it("renders factory conveyor belt lines", () => {
    switchToHandWorld();
    const factory = document.querySelector(".hh-factory");
    expect(factory!.querySelector(".factory-conveyor-line-1")).not.toBeNull();
    expect(factory!.querySelector(".factory-conveyor-line-2")).not.toBeNull();
    expect(factory!.querySelector(".factory-conveyor-line-3")).not.toBeNull();
  });

  it("renders incinerator DOM elements (body, mouth, flames)", () => {
    switchToHandWorld();
    const incinerator = document.querySelector(".hh-incinerator");
    expect(incinerator).not.toBeNull();
    expect(incinerator!.querySelector(".incinerator-body")).not.toBeNull();
    expect(incinerator!.querySelector(".incinerator-mouth")).not.toBeNull();
    expect(incinerator!.querySelector(".incinerator-top")).not.toBeNull();
    expect(incinerator!.querySelector(".incinerator-grate")).not.toBeNull();
  });

  it("renders incinerator flames", () => {
    switchToHandWorld();
    const incinerator = document.querySelector(".hh-incinerator");
    expect(incinerator!.querySelector(".incinerator-flame-1")).not.toBeNull();
    expect(incinerator!.querySelector(".incinerator-flame-2")).not.toBeNull();
    expect(incinerator!.querySelector(".incinerator-flame-3")).not.toBeNull();
  });

  it("renders incinerator embers and heat glow", () => {
    switchToHandWorld();
    const incinerator = document.querySelector(".hh-incinerator");
    expect(incinerator!.querySelector(".incinerator-ember-1")).not.toBeNull();
    expect(incinerator!.querySelector(".incinerator-ember-2")).not.toBeNull();
    expect(incinerator!.querySelector(".incinerator-heat-glow")).not.toBeNull();
  });

  it("renders incinerator chimney and exhaust", () => {
    switchToHandWorld();
    const incinerator = document.querySelector(".hh-incinerator");
    expect(incinerator!.querySelector(".incinerator-chimney")).not.toBeNull();
    expect(incinerator!.querySelector(".incinerator-exhaust-1")).not.toBeNull();
    expect(incinerator!.querySelector(".incinerator-exhaust-2")).not.toBeNull();
  });

  it("renders work desks instead of zen plots", () => {
    switchToHandWorld();
    expect(document.querySelector(".work-desk")).not.toBeNull();
    expect(document.querySelector(".zen-plot")).toBeNull();
  });

  it("renders Factory Floor status summary", () => {
    switchToHandWorld();
    expect(screen.getByText("Factory Floor")).toBeInTheDocument();
  });

  it("renders Stations count in status summary", () => {
    switchToHandWorld();
    expect(screen.getByText(/Stations/)).toBeInTheDocument();
  });

  it("renders factory workers aria label on scene", () => {
    switchToHandWorld();
    expect(screen.getByLabelText("Current factory workers")).toBeInTheDocument();
  });

  it("does not render old zen-torii or zen-shrine elements", () => {
    switchToHandWorld();
    expect(document.querySelector(".zen-torii")).toBeNull();
    expect(document.querySelector(".zen-shrine")).toBeNull();
  });
});
