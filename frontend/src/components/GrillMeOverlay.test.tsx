import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { beforeAll, describe, it, expect, vi, afterEach } from "vitest";

import GrillMeOverlay from "./GrillMeOverlay";
import type { GrillMeOverlayProps } from "./GrillMeOverlay";
import type { GrillSessionState } from "../hooks/useGrillSession";
import type { GrillFormState, GrillMessage } from "../types";

// ---------------------------------------------------------------------------
// jsdom stubs
// ---------------------------------------------------------------------------
beforeAll(() => {
  Element.prototype.scrollIntoView = vi.fn();
});

// ---------------------------------------------------------------------------
// Mock sub-components that have their own test suites
// ---------------------------------------------------------------------------
vi.mock("./RepoChipInput", () => ({
  default: ({ value, onChange, placeholder, ariaLabel }: {
    value: string[];
    onChange: (repos: string[]) => void;
    placeholder?: string;
    ariaLabel?: string;
  }) => (
    <div data-testid="repo-chip-input" aria-label={ariaLabel}>
      <span data-testid="chip-count">{value.length}</span>
      <input
        placeholder={placeholder}
        onChange={(e) => onChange([...value, e.target.value])}
      />
    </div>
  ),
}));

vi.mock("./RepoSuggestInput", () => ({
  default: ({ value, onChange, placeholder, ariaLabel, required, className }: {
    value: string;
    onChange: (val: string) => void;
    placeholder?: string;
    ariaLabel?: string;
    required?: boolean;
    className?: string;
  }) => (
    <input
      data-testid="repo-suggest-input"
      className={className}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      aria-label={ariaLabel}
      required={required}
    />
  ),
}));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  // Reset any persisted drafts between tests.
  try {
    window.localStorage.clear();
  } catch {
    /* ignore */
  }
});

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeSession(overrides: Partial<GrillSessionState> = {}): GrillSessionState {
  return {
    phase: "form",
    sessionId: null,
    status: "idle",
    messages: [],
    error: null,
    isLoading: false,
    finalPlan: null,
    startSession: vi.fn(),
    sendMessage: vi.fn(),
    requestPlan: vi.fn(),
    reset: vi.fn(),
    ...overrides,
  };
}

const DEFAULT_FORM: GrillFormState = {
  repo_path: "",
  prompt: "",
  model: "",
  github_token: "",
  reference_repos: "",
  backend: "claudecodecli",
};

function makeProps(overrides: Partial<GrillMeOverlayProps> = {}): GrillMeOverlayProps {
  return {
    session: makeSession(),
    recentRepos: ["owner/repo-a", "owner/repo-b"],
    serverHasGithubToken: true,
    initialForm: DEFAULT_FORM,
    onClose: vi.fn(),
    onSubmitPlan: vi.fn(),
    ...overrides,
  };
}

function renderOverlay(overrides: Partial<GrillMeOverlayProps> = {}) {
  const props = makeProps(overrides);
  const result = render(<GrillMeOverlay {...props} />);
  return { ...result, props };
}

function makeMessage(overrides: Partial<GrillMessage> & { id: string }): GrillMessage {
  return {
    role: "assistant",
    content: "Hello",
    type: "message",
    timestamp: Date.now() / 1000,
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Overlay structure
// ---------------------------------------------------------------------------

describe("GrillMeOverlay", () => {
  describe("overlay structure", () => {
    it("renders the overlay with a close button", () => {
      renderOverlay();
      expect(screen.getByLabelText("Close")).toBeInTheDocument();
    });

    it("calls onClose when close button is clicked", () => {
      const { props } = renderOverlay();
      fireEvent.click(screen.getByLabelText("Close"));
      expect(props.onClose).toHaveBeenCalledOnce();
    });

    it("calls onClose when backdrop is clicked", () => {
      const { props, container } = renderOverlay();
      const backdrop = container.querySelector(".grill-overlay");
      expect(backdrop).not.toBeNull();
      fireEvent.click(backdrop!);
      expect(props.onClose).toHaveBeenCalledOnce();
    });

    it("does not call onClose when content area is clicked", () => {
      const { props, container } = renderOverlay();
      const content = container.querySelector(".grill-overlay-content");
      fireEvent.click(content!);
      expect(props.onClose).not.toHaveBeenCalled();
    });
  });

  // ---- Phase titles ----

  describe("phase titles", () => {
    it("shows 'Grill Me' title in form phase", () => {
      renderOverlay({ session: makeSession({ phase: "form" }) });
      expect(screen.getByText("Grill Me")).toBeInTheDocument();
    });

    it("shows 'Grilling in Progress' title in chatting phase", () => {
      renderOverlay({ session: makeSession({ phase: "chatting" }) });
      expect(screen.getByText("Grilling in Progress")).toBeInTheDocument();
    });

    it("shows 'Final Plan' title in plan phase", () => {
      renderOverlay({
        session: makeSession({ phase: "plan", finalPlan: "The plan" }),
      });
      expect(screen.getByText("Final Plan")).toBeInTheDocument();
    });
  });

  // ---- Form phase ----

  describe("form phase", () => {
    it("renders form fields", () => {
      renderOverlay();
      expect(screen.getByTestId("repo-suggest-input")).toBeInTheDocument();
      expect(screen.getByPlaceholderText(/Describe your plan/)).toBeInTheDocument();
      expect(screen.getByText("Model")).toBeInTheDocument();
      expect(screen.getByText(/GitHub Token/)).toBeInTheDocument();
      expect(screen.getByText("Reference Repos")).toBeInTheDocument();
    });

    it("renders Start Grilling button", () => {
      renderOverlay();
      expect(screen.getByText("Start Grilling")).toBeInTheDocument();
    });

    it("renders Starting... when loading", () => {
      renderOverlay({ session: makeSession({ phase: "form", isLoading: true }) });
      expect(screen.getByText("Starting...")).toBeInTheDocument();
    });

    it("disables button when loading", () => {
      renderOverlay({ session: makeSession({ phase: "form", isLoading: true }) });
      expect(screen.getByText("Starting...")).toBeDisabled();
    });

    it("calls startSession on form submit", () => {
      const session = makeSession({ phase: "form" });
      renderOverlay({
        session,
        initialForm: {
          repo_path: "my/repo",
          prompt: "add feature",
          model: "gpt-5.2",
          github_token: "ghp_123",
          reference_repos: "",
          backend: "claudecodecli",
        },
      });

      fireEvent.submit(screen.getByText("Start Grilling").closest("form")!);
      expect(session.startSession).toHaveBeenCalledOnce();
      const formArg = (session.startSession as ReturnType<typeof vi.fn>).mock.calls[0][0];
      expect(formArg.repo_path).toBe("my/repo");
      expect(formArg.prompt).toBe("add feature");
    });

    it("shows error message when error exists", () => {
      renderOverlay({
        session: makeSession({ phase: "form", error: "Something went wrong" }),
      });
      expect(screen.getByText("Something went wrong")).toBeInTheDocument();
    });

    it("shows required star for token when server lacks github token", () => {
      renderOverlay({ serverHasGithubToken: false });
      expect(screen.getByText("*")).toBeInTheDocument();
    });

    it("does not show required star when server has github token", () => {
      renderOverlay({ serverHasGithubToken: true });
      expect(screen.queryByText("*")).not.toBeInTheDocument();
    });
  });

  // ---- Chat phase ----

  describe("chat phase", () => {
    it("renders user and assistant messages", () => {
      const messages: GrillMessage[] = [
        makeMessage({ id: "m1", role: "assistant", content: "What is your approach?" }),
        makeMessage({ id: "m2", role: "user", content: "Use microservices" }),
      ];
      renderOverlay({
        session: makeSession({ phase: "chatting", messages }),
      });

      expect(screen.getByText("Interviewer")).toBeInTheDocument();
      expect(screen.getByText("You")).toBeInTheDocument();
    });

    it("renders system messages", () => {
      const messages: GrillMessage[] = [
        makeMessage({ id: "s1", role: "system", content: "Analyzing repo..." }),
      ];
      renderOverlay({
        session: makeSession({ phase: "chatting", messages }),
      });
      expect(screen.getByText("Analyzing repo...")).toBeInTheDocument();
    });

    it("collapses consecutive system messages", () => {
      const messages: GrillMessage[] = [
        makeMessage({ id: "s1", role: "system", content: "Step 1" }),
        makeMessage({ id: "s2", role: "system", content: "Step 2" }),
        makeMessage({ id: "s3", role: "system", content: "Step 3" }),
      ];
      renderOverlay({
        session: makeSession({ phase: "chatting", messages }),
      });
      // Last message shown in summary
      expect(screen.getByText("Step 3")).toBeInTheDocument();
      // Count badge
      expect(screen.getByText("3 steps")).toBeInTheDocument();
    });

    it("shows thinking indicator when loading", () => {
      renderOverlay({
        session: makeSession({ phase: "chatting", isLoading: true }),
      });
      const thinking = document.querySelector(".grill-thinking-dots");
      expect(thinking).not.toBeNull();
    });

    it("does not show thinking indicator when not loading", () => {
      renderOverlay({
        session: makeSession({ phase: "chatting", isLoading: false }),
      });
      const thinking = document.querySelector(".grill-thinking-dots");
      expect(thinking).toBeNull();
    });

    it("shows error in chat phase", () => {
      renderOverlay({
        session: makeSession({ phase: "chatting", error: "Connection lost" }),
      });
      expect(screen.getByText("Connection lost")).toBeInTheDocument();
    });

    it("renders Send and Wrap Up buttons", () => {
      renderOverlay({
        session: makeSession({ phase: "chatting" }),
      });
      expect(screen.getByText("Send")).toBeInTheDocument();
      expect(screen.getByText("Wrap Up")).toBeInTheDocument();
    });

    it("disables Send when input is empty", () => {
      renderOverlay({
        session: makeSession({ phase: "chatting" }),
      });
      expect(screen.getByText("Send")).toBeDisabled();
    });

    it("calls sendMessage when Send is clicked with input", () => {
      const session = makeSession({ phase: "chatting" });
      renderOverlay({ session });

      const textarea = document.querySelector(".grill-chat-input") as HTMLTextAreaElement;
      fireEvent.change(textarea, { target: { value: "my response" } });
      fireEvent.click(screen.getByText("Send"));

      expect(session.sendMessage).toHaveBeenCalledWith("my response");
    });

    it("clears input after sending", () => {
      const session = makeSession({ phase: "chatting" });
      renderOverlay({ session });

      const textarea = document.querySelector(".grill-chat-input") as HTMLTextAreaElement;
      fireEvent.change(textarea, { target: { value: "my response" } });
      fireEvent.click(screen.getByText("Send"));

      expect(textarea.value).toBe("");
    });

    it("sends on Enter key (without Shift)", () => {
      const session = makeSession({ phase: "chatting" });
      renderOverlay({ session });

      const textarea = document.querySelector(".grill-chat-input") as HTMLTextAreaElement;
      fireEvent.change(textarea, { target: { value: "enter test" } });
      fireEvent.keyDown(textarea, { key: "Enter", shiftKey: false });

      expect(session.sendMessage).toHaveBeenCalledWith("enter test");
    });

    it("does not send on Shift+Enter", () => {
      const session = makeSession({ phase: "chatting" });
      renderOverlay({ session });

      const textarea = document.querySelector(".grill-chat-input") as HTMLTextAreaElement;
      fireEvent.change(textarea, { target: { value: "newline test" } });
      fireEvent.keyDown(textarea, { key: "Enter", shiftKey: true });

      expect(session.sendMessage).not.toHaveBeenCalled();
    });

    it("does not send empty/whitespace input", () => {
      const session = makeSession({ phase: "chatting" });
      renderOverlay({ session });

      const textarea = document.querySelector(".grill-chat-input") as HTMLTextAreaElement;
      fireEvent.change(textarea, { target: { value: "   " } });
      fireEvent.keyDown(textarea, { key: "Enter", shiftKey: false });

      expect(session.sendMessage).not.toHaveBeenCalled();
    });

    it("disables input and buttons when loading", () => {
      renderOverlay({
        session: makeSession({ phase: "chatting", isLoading: true }),
      });

      const textarea = document.querySelector(".grill-chat-input") as HTMLTextAreaElement;
      expect(textarea.disabled).toBe(true);
      expect(screen.getByText("Wrap Up")).toBeDisabled();
    });

    it("calls requestPlan when Wrap Up is clicked", () => {
      const session = makeSession({ phase: "chatting" });
      renderOverlay({ session });

      fireEvent.click(screen.getByText("Wrap Up"));
      expect(session.requestPlan).toHaveBeenCalledOnce();
    });
  });

  // ---- Plan phase ----

  describe("plan phase", () => {
    it("renders the final plan content", () => {
      renderOverlay({
        session: makeSession({
          phase: "plan",
          finalPlan: "This is the **final** plan",
        }),
      });

      const planContent = document.querySelector(".grill-plan-content");
      expect(planContent).not.toBeNull();
      expect(planContent!.innerHTML).toContain("<strong>final</strong>");
    });

    it("renders Submit as Task and Keep Grilling buttons", () => {
      renderOverlay({
        session: makeSession({ phase: "plan", finalPlan: "Plan content" }),
      });
      expect(screen.getByText("Submit as Task")).toBeInTheDocument();
      expect(screen.getByText("Keep Grilling")).toBeInTheDocument();
    });

    it("calls onSubmitPlan when Submit as Task is clicked", () => {
      const session = makeSession({ phase: "plan", finalPlan: "The plan" });
      const { props } = renderOverlay({ session });

      fireEvent.click(screen.getByText("Submit as Task"));
      expect(props.onSubmitPlan).toHaveBeenCalledWith("The plan");
    });

    it("calls sendMessage when Keep Grilling is clicked", () => {
      const session = makeSession({ phase: "plan", finalPlan: "The plan" });
      renderOverlay({ session });

      fireEvent.click(screen.getByText("Keep Grilling"));
      expect(session.sendMessage).toHaveBeenCalledOnce();
    });

    it("does not render plan phase when finalPlan is null", () => {
      renderOverlay({
        session: makeSession({ phase: "plan", finalPlan: null }),
      });
      expect(screen.queryByText("Submit as Task")).not.toBeInTheDocument();
    });
  });

  // ---- System message grouping ----

  describe("system message grouping", () => {
    it("renders single system message without collapse", () => {
      const messages: GrillMessage[] = [
        makeMessage({ id: "s1", role: "system", content: "Single system msg" }),
      ];
      renderOverlay({
        session: makeSession({ phase: "chatting", messages }),
      });
      expect(screen.getByText("Single system msg")).toBeInTheDocument();
      expect(screen.queryByText(/steps/)).not.toBeInTheDocument();
    });

    it("marks error system messages with error class", () => {
      const messages: GrillMessage[] = [
        makeMessage({ id: "e1", role: "system", content: "Error occurred", type: "error" }),
      ];
      renderOverlay({
        session: makeSession({ phase: "chatting", messages }),
      });
      const errorEl = screen.getByText("Error occurred");
      expect(errorEl.className).toContain("grill-msg-error");
    });

    it("interleaves chat and system groups correctly", () => {
      const messages: GrillMessage[] = [
        makeMessage({ id: "s1", role: "system", content: "Setup" }),
        makeMessage({ id: "a1", role: "assistant", content: "Question 1" }),
        makeMessage({ id: "s2", role: "system", content: "Processing" }),
        makeMessage({ id: "s3", role: "system", content: "Done processing" }),
      ];
      renderOverlay({
        session: makeSession({ phase: "chatting", messages }),
      });
      expect(screen.getByText("Setup")).toBeInTheDocument();
      expect(screen.getByText("Interviewer")).toBeInTheDocument();
      expect(screen.getByText("Done processing")).toBeInTheDocument();
      expect(screen.getByText("2 steps")).toBeInTheDocument();
    });
  });

  // ---- Draft persistence ----

  describe("draft persistence", () => {
    it("persists form prompt draft to localStorage on change", () => {
      renderOverlay({ session: makeSession({ phase: "form" }) });
      const prompt = screen.getByPlaceholderText(/Describe your plan/) as HTMLTextAreaElement;
      fireEvent.change(prompt, { target: { value: "draft prompt" } });

      const raw = window.localStorage.getItem("hh_grill_form_draft");
      expect(raw).not.toBeNull();
      expect(JSON.parse(raw!).prompt).toBe("draft prompt");
    });

    it("hydrates form fields from persisted draft on remount", () => {
      window.localStorage.setItem(
        "hh_grill_form_draft",
        JSON.stringify({
          repo_path: "persisted/repo",
          prompt: "persisted prompt",
          model: "gpt-5.2",
          reference_repos: "",
          backend: "claudecodecli",
        }),
      );

      renderOverlay({ session: makeSession({ phase: "form" }) });
      const prompt = screen.getByPlaceholderText(/Describe your plan/) as HTMLTextAreaElement;
      expect(prompt.value).toBe("persisted prompt");
      const repo = screen.getByTestId("repo-suggest-input") as HTMLInputElement;
      expect(repo.value).toBe("persisted/repo");
    });

    it("does not persist the github token in the form draft", () => {
      renderOverlay({
        session: makeSession({ phase: "form" }),
        initialForm: {
          repo_path: "",
          prompt: "",
          model: "",
          github_token: "ghp_secret",
          reference_repos: "",
          backend: "claudecodecli",
        },
      });

      // Trigger a re-persist by editing an unrelated field.
      const prompt = screen.getByPlaceholderText(/Describe your plan/) as HTMLTextAreaElement;
      fireEvent.change(prompt, { target: { value: "anything" } });

      const raw = window.localStorage.getItem("hh_grill_form_draft");
      expect(raw).not.toBeNull();
      const parsed = JSON.parse(raw!);
      expect(parsed).not.toHaveProperty("github_token");
    });

    it("clears the form draft after starting the session", () => {
      window.localStorage.setItem(
        "hh_grill_form_draft",
        JSON.stringify({ prompt: "old draft" }),
      );
      const session = makeSession({ phase: "form" });
      renderOverlay({
        session,
        initialForm: {
          repo_path: "x/y",
          prompt: "a prompt",
          model: "",
          github_token: "",
          reference_repos: "",
          backend: "claudecodecli",
        },
      });

      fireEvent.submit(screen.getByText("Start Grilling").closest("form")!);
      expect(window.localStorage.getItem("hh_grill_form_draft")).toBeNull();
    });

    it("hydrates chat input draft from localStorage", () => {
      window.localStorage.setItem("hh_grill_chat_draft", "in-flight answer");
      renderOverlay({ session: makeSession({ phase: "chatting" }) });
      const textarea = document.querySelector(".grill-chat-input") as HTMLTextAreaElement;
      expect(textarea.value).toBe("in-flight answer");
    });

    it("persists chat input draft on change", () => {
      renderOverlay({ session: makeSession({ phase: "chatting" }) });
      const textarea = document.querySelector(".grill-chat-input") as HTMLTextAreaElement;
      fireEvent.change(textarea, { target: { value: "typing..." } });
      expect(window.localStorage.getItem("hh_grill_chat_draft")).toBe("typing...");
    });

    it("clears chat draft after send", () => {
      window.localStorage.setItem("hh_grill_chat_draft", "will be sent");
      const session = makeSession({ phase: "chatting" });
      renderOverlay({ session });
      const textarea = document.querySelector(".grill-chat-input") as HTMLTextAreaElement;
      fireEvent.change(textarea, { target: { value: "will be sent" } });
      fireEvent.click(screen.getByText("Send"));

      expect(session.sendMessage).toHaveBeenCalledWith("will be sent");
      expect(window.localStorage.getItem("hh_grill_chat_draft")).toBeNull();
    });
  });

  // ---- Markdown rendering ----

  describe("markdown rendering in messages", () => {
    it("renders fenced code blocks", () => {
      const messages: GrillMessage[] = [
        makeMessage({
          id: "md1",
          role: "assistant",
          content: "Check this:\n```python\nprint('hello')\n```",
        }),
      ];
      renderOverlay({
        session: makeSession({ phase: "chatting", messages }),
      });
      const codeBlock = document.querySelector(".grill-code-block");
      expect(codeBlock).not.toBeNull();
      expect(codeBlock!.textContent).toContain("print('hello')");
    });

    it("renders bold and italic text", () => {
      const messages: GrillMessage[] = [
        makeMessage({
          id: "md2",
          role: "assistant",
          content: "This is **bold** and *italic* text",
        }),
      ];
      renderOverlay({
        session: makeSession({ phase: "chatting", messages }),
      });
      const content = document.querySelector(".grill-msg-content");
      expect(content!.innerHTML).toContain("<strong>bold</strong>");
      expect(content!.innerHTML).toContain("<em>italic</em>");
    });

    it("renders headers", () => {
      const messages: GrillMessage[] = [
        makeMessage({
          id: "md3",
          role: "assistant",
          content: "# Heading 1\n## Heading 2\n### Heading 3",
        }),
      ];
      renderOverlay({
        session: makeSession({ phase: "chatting", messages }),
      });
      const content = document.querySelector(".grill-msg-content");
      expect(content!.querySelector("h2.grill-h")).not.toBeNull();
      expect(content!.querySelector("h3.grill-h")).not.toBeNull();
      expect(content!.querySelector("h4.grill-h")).not.toBeNull();
    });

    it("renders unordered lists", () => {
      const messages: GrillMessage[] = [
        makeMessage({
          id: "md4",
          role: "assistant",
          content: "- Item A\n- Item B",
        }),
      ];
      renderOverlay({
        session: makeSession({ phase: "chatting", messages }),
      });
      const content = document.querySelector(".grill-msg-content");
      expect(content!.querySelector("ul.grill-ul")).not.toBeNull();
      const items = content!.querySelectorAll("li.grill-li");
      expect(items.length).toBe(2);
    });

    it("renders inline code", () => {
      const messages: GrillMessage[] = [
        makeMessage({
          id: "md5",
          role: "assistant",
          content: "Use `console.log()` for debugging",
        }),
      ];
      renderOverlay({
        session: makeSession({ phase: "chatting", messages }),
      });
      const inlineCode = document.querySelector(".grill-inline-code");
      expect(inlineCode).not.toBeNull();
      expect(inlineCode!.textContent).toBe("console.log()");
    });

    it("escapes HTML in code blocks", () => {
      const messages: GrillMessage[] = [
        makeMessage({
          id: "md6",
          role: "assistant",
          content: "```html\n<script>alert('xss')</script>\n```",
        }),
      ];
      renderOverlay({
        session: makeSession({ phase: "chatting", messages }),
      });
      const codeBlock = document.querySelector(".grill-code-block code");
      expect(codeBlock!.innerHTML).toContain("&lt;script&gt;");
      expect(codeBlock!.innerHTML).not.toContain("<script>");
    });
  });
});
