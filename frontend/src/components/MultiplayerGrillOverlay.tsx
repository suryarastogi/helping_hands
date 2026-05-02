/**
 * MultiplayerGrillOverlay — top-level modal that routes between the lobby
 * view (session list + create) and the room view (active session UI).
 *
 * Opened from the world sprite (see HandWorldScene) — mirrors the
 * Asteroids/solo-Grill overlay pattern.
 */
import { useEffect, useState } from "react";

import { useMultiplayerGrill, useMultiplayerGrillLobby } from "../hooks/useMultiplayerGrill";
import type { MGrillCreateForm, MGrillSessionSummary } from "../types";
import MultiplayerGrillLobby from "./MultiplayerGrillLobby";
import MultiplayerGrillRoom from "./MultiplayerGrillRoom";

type Props = {
  onClose: () => void;
  onMinimize: () => void;
  minimized: boolean;
  onSubmitPlan: (taskId: string) => void;
  /** Current local player id (Yjs clientID as string). */
  playerId: string;
  /** Current local player name. */
  playerName: string;
  /** Pre-fill values for the Create form. */
  initialCreateForm?: Partial<MGrillCreateForm>;
  /** Whether the server reports a global GITHUB_TOKEN (affects copy). */
  serverHasGithubToken?: boolean;
};

export default function MultiplayerGrillOverlay({
  onClose,
  onMinimize,
  minimized,
  onSubmitPlan,
  playerId,
  playerName,
  initialCreateForm,
  serverHasGithubToken = false,
}: Props) {
  const session = useMultiplayerGrill();
  const lobby = useMultiplayerGrillLobby(session.sessionId === null);
  const [showCreate, setShowCreate] = useState(false);

  // When a session is submitted, notify the parent so it can show the task.
  useEffect(() => {
    const tid = session.state?.submitted_task_id;
    if (tid) {
      onSubmitPlan(tid);
    }
  }, [session.state?.submitted_task_id, onSubmitPlan]);

  const handleJoin = (s: MGrillSessionSummary) => {
    setShowCreate(false);
    session.joinSession(s.session_id);
  };

  const handleFullClose = () => {
    session.leaveSession();
    onClose();
  };

  if (minimized) return null;

  if (session.sessionId) {
    return (
      <section
        className="mgrill-overlay"
        role="dialog"
        aria-modal="true"
        aria-label="Multiplayer Grill Room"
      >
        <MultiplayerGrillRoom
          actions={session}
          playerId={playerId}
          playerName={playerName}
          serverHasGithubToken={serverHasGithubToken}
          onClose={onMinimize}
          onLeave={handleFullClose}
        />
      </section>
    );
  }

  return (
    <section
      className="mgrill-overlay"
      role="dialog"
      aria-modal="true"
      aria-label="Multiplayer Grill Lobby"
    >
      <MultiplayerGrillLobby
        lobby={lobby}
        showCreate={showCreate}
        onToggleCreate={() => setShowCreate((v) => !v)}
        onCreate={async (form) => {
          const sid = await session.createSession(form, playerName);
          if (sid) {
            setShowCreate(false);
          }
        }}
        onJoin={handleJoin}
        onClose={handleFullClose}
        isCreating={session.isLoading}
        error={session.error}
        initialCreateForm={initialCreateForm}
        serverHasGithubToken={serverHasGithubToken}
      />
    </section>
  );
}
