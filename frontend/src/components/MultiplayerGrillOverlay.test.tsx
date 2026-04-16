import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import MultiplayerGrillOverlay from "./MultiplayerGrillOverlay";
import type { MultiplayerGrillOverlayProps } from "./MultiplayerGrillOverlay";
import type { MultiplayerGrillChatState } from "../hooks/useMultiplayerGrillChat";
import type {
  GrillFormState,
  GrillMessage,
  MultiplayerGrillSession,
} from "../types";

beforeAll(() => {
  Element.prototype.scrollIntoView = vi.fn();
});

vi.mock("./RepoChipInput", () => ({
  default: ({ value }: { value: string[] }) => (
    <div data-testid="repo-chip-input">{value.length}</div>
  ),
}));

vi.mock("./RepoSuggestInput", () => ({
  default: ({
    value,
    onChange,
    placeholder,
    ariaLabel,
    required,
  }: {
    value: string;
    onChange: (val: string) => void;
    placeholder?: string;
    ariaLabel?: string;
    required?: boolean;
  }) => (
    <input
      data-testid="repo-suggest-input"
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
  try {
    window.localStorage.clear();
  } catch {
    /* ignore */
  }
});

const DEFAULT_FORM: GrillFormState = {
  repo_path: "",
  prompt: "",
  model: "",
  github_token: "",
  reference_repos: "",
  backend: "claudecodecli",
};

function makeChat(overrides: Partial<MultiplayerGrillChatState> = {}): MultiplayerGrillChatState {
  return {
    messages: [],
    status: "idle",
    finalPlan: null,
    isLoading: false,
    error: null,
    sendMessage: vi.fn().mockResolvedValue(undefined),
    requestPlan: vi.fn().mockResolvedValue(undefined),
    endSession: vi.fn().mockResolvedValue(undefined),
    ...overrides,
  };
}

function makeSession(overrides: Partial<MultiplayerGrillSession> = {}): MultiplayerGrillSession {
  return {
    id: "sess-1",
    creatorId: "creator-1",
    creatorName: "Alice",
    creatorColor: "#ff0000",
    repoPath: "owner/repo",
    prompt: "Help me design X",
    backend: "claudecodecli",
    createdAt: Date.now(),
    status: "active",
    finalPlan: null,
    votes: {},
    submitted: false,
    ...overrides,
  };
}

function makeMessage(overrides: Partial<GrillMessage> & { id: string }): GrillMessage {
  return {
    role: "assistant",
    content: "Hi",
    type: "message",
    timestamp: Date.now() / 1000,
    ...overrides,
  };
}

function makeProps(
  overrides: Partial<MultiplayerGrillOverlayProps> = {},
): MultiplayerGrillOverlayProps {
  return {
    sessions: [],
    selectedSessionId: null,
    onSelectSession: vi.fn(),
    recentRepos: ["owner/repo-a"],
    serverHasGithubToken: true,
    initialForm: DEFAULT_FORM,
    localPlayerId: "me",
    chat: makeChat(),
    onClose: vi.fn(),
    onCreateSession: vi.fn().mockResolvedValue("sess-1"),
    onVote: vi.fn(),
    onSubmitPlan: vi.fn(),
    ...overrides,
  };
}

function renderOverlay(overrides: Partial<MultiplayerGrillOverlayProps> = {}) {
  const props = makeProps(overrides);
  const result = render(<MultiplayerGrillOverlay {...props} />);
  return { ...result, props };
}

describe("MultiplayerGrillOverlay", () => {
  describe("session list", () => {
    it("shows the empty state when there are no sessions", () => {
      renderOverlay();
      expect(
        screen.getByText(/No grill sessions yet/i),
      ).toBeInTheDocument();
    });

    it("lists active and submitted sessions in separate sections", () => {
      const active = makeSession({ id: "a", creatorName: "Active Person" });
      const submitted = makeSession({
        id: "b",
        creatorName: "Done Person",
        submitted: true,
      });
      renderOverlay({ sessions: [active, submitted] });
      expect(screen.getByText("Active Sessions")).toBeInTheDocument();
      // "Submitted" appears as both a section header and a badge — match the header role.
      expect(
        screen.getByRole("heading", { name: "Submitted" }),
      ).toBeInTheDocument();
      expect(screen.getByText("Active Person")).toBeInTheDocument();
      expect(screen.getByText("Done Person")).toBeInTheDocument();
    });

    it("calls onSelectSession when a session card is clicked", () => {
      const session = makeSession({ id: "abc" });
      const { props } = renderOverlay({ sessions: [session] });
      fireEvent.click(screen.getByText("Help me design X"));
      expect(props.onSelectSession).toHaveBeenCalledWith("abc");
    });

    it("shows the new-session form when Start a New Grill is clicked", () => {
      renderOverlay();
      fireEvent.click(screen.getByText("Start a New Grill"));
      expect(screen.getByText("Start Grilling")).toBeInTheDocument();
      expect(screen.getByTestId("repo-suggest-input")).toBeInTheDocument();
    });
  });

  describe("session detail", () => {
    it("renders selected session messages", () => {
      const session = makeSession({ id: "sel" });
      const messages = [
        makeMessage({ id: "m1", role: "assistant", content: "ai says hi" }),
        makeMessage({ id: "m2", role: "user", content: "user replies" }),
      ];
      renderOverlay({
        sessions: [session],
        selectedSessionId: "sel",
        chat: makeChat({ messages }),
      });
      expect(screen.getByText("ai says hi")).toBeInTheDocument();
      expect(screen.getByText("user replies")).toBeInTheDocument();
    });

    it("calls onSelectSession(null) when Back is clicked", () => {
      const session = makeSession({ id: "sel" });
      const { props } = renderOverlay({
        sessions: [session],
        selectedSessionId: "sel",
      });
      fireEvent.click(screen.getByLabelText("Back to sessions"));
      expect(props.onSelectSession).toHaveBeenCalledWith(null);
    });

    it("posts message via chat.sendMessage when Send is clicked", () => {
      const session = makeSession({ id: "sel" });
      const sendMessage = vi.fn().mockResolvedValue(undefined);
      renderOverlay({
        sessions: [session],
        selectedSessionId: "sel",
        chat: makeChat({ sendMessage }),
      });
      const textarea = screen.getByPlaceholderText(/Type a message/);
      fireEvent.change(textarea, { target: { value: "hello there" } });
      fireEvent.click(screen.getByText("Send"));
      expect(sendMessage).toHaveBeenCalledWith("hello there");
    });
  });

  describe("plan voting and submission", () => {
    it("shows the vote panel when a final plan exists", () => {
      const session = makeSession({ id: "sel" });
      renderOverlay({
        sessions: [session],
        selectedSessionId: "sel",
        chat: makeChat({ finalPlan: "Some plan" }),
      });
      expect(screen.getByText(/Vote on this plan/i)).toBeInTheDocument();
      expect(screen.getByLabelText("Vote up")).toBeInTheDocument();
      expect(screen.getByLabelText("Vote down")).toBeInTheDocument();
    });

    it("calls onVote with 'up' when the up button is clicked (no prior vote)", () => {
      const session = makeSession({ id: "sel" });
      const { props } = renderOverlay({
        sessions: [session],
        selectedSessionId: "sel",
        chat: makeChat({ finalPlan: "Some plan" }),
      });
      fireEvent.click(screen.getByLabelText("Vote up"));
      expect(props.onVote).toHaveBeenCalledWith("sel", "up");
    });

    it("calls onVote with null to clear an existing vote", () => {
      const session = makeSession({
        id: "sel",
        votes: { me: "up" },
      });
      const { props } = renderOverlay({
        sessions: [session],
        selectedSessionId: "sel",
        chat: makeChat({ finalPlan: "Some plan" }),
      });
      fireEvent.click(screen.getByLabelText("Vote up"));
      expect(props.onVote).toHaveBeenCalledWith("sel", null);
    });

    it("only shows Submit as Task to the creator", () => {
      const session = makeSession({
        id: "sel",
        creatorId: "someone-else",
      });
      renderOverlay({
        sessions: [session],
        selectedSessionId: "sel",
        localPlayerId: "me",
        chat: makeChat({ finalPlan: "The plan" }),
      });
      expect(screen.queryByText("Submit as Task")).not.toBeInTheDocument();
      expect(screen.getByText(/Only Alice can submit this plan/i)).toBeInTheDocument();
    });

    it("shows Submit as Task to the creator and calls onSubmitPlan", () => {
      const session = makeSession({
        id: "sel",
        creatorId: "me",
      });
      const { props } = renderOverlay({
        sessions: [session],
        selectedSessionId: "sel",
        localPlayerId: "me",
        chat: makeChat({ finalPlan: "The Plan Text" }),
      });
      fireEvent.click(screen.getByText("Submit as Task"));
      expect(props.onSubmitPlan).toHaveBeenCalledWith(session, "The Plan Text");
    });
  });
});
