/**
 * useMovement — keyboard-driven player movement hook for Hand World.
 *
 * Encapsulates arrow-key / WASD input handling, position clamping within
 * office bounds, desk collision detection, and direction/walking state.
 */
import { useEffect, useRef, useState } from "react";

import { OFFICE_BOUNDS, PLAYER_MOVE_STEP, SPAWN_PADDING } from "../constants";
import type { DeskSlot, PlayerDirection, PlayerPosition } from "../types";
import { checkDeskCollision } from "../App.utils";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type UseMovementOptions = {
  /** Whether the world view is active — hook only binds keys when true. */
  active: boolean;
  /** Pre-computed desk slot positions used for collision detection. */
  deskSlots: DeskSlot[];
};

export type UseMovementReturn = {
  playerPosition: PlayerPosition;
  playerDirection: PlayerDirection;
  isPlayerWalking: boolean;
};

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/** Generate a random spawn position within office bounds, avoiding edges. */
export function randomSpawnPosition(): PlayerPosition {
  const minX = OFFICE_BOUNDS.minX + SPAWN_PADDING;
  const maxX = OFFICE_BOUNDS.maxX - SPAWN_PADDING;
  const minY = OFFICE_BOUNDS.minY + SPAWN_PADDING;
  const maxY = OFFICE_BOUNDS.maxY - SPAWN_PADDING;
  return {
    x: minX + Math.random() * (maxX - minX),
    y: minY + Math.random() * (maxY - minY),
  };
}

export function useMovement(options: UseMovementOptions): UseMovementReturn {
  const { active, deskSlots } = options;

  // Compute a stable random spawn position once per mount.
  const spawnRef = useRef<PlayerPosition>(randomSpawnPosition());
  const [playerPosition, setPlayerPosition] = useState<PlayerPosition>(spawnRef.current);
  const [playerDirection, setPlayerDirection] = useState<PlayerDirection>("down");
  const [isPlayerWalking, setIsPlayerWalking] = useState(false);

  useEffect(() => {
    if (!active) {
      return;
    }

    const keysPressed = new Set<string>();
    let animationFrame: number | null = null;

    const movePlayer = () => {
      if (keysPressed.size === 0) {
        setIsPlayerWalking(false);
        animationFrame = null;
        return;
      }

      setIsPlayerWalking(true);

      // Update direction outside the position updater to keep it pure.
      if (keysPressed.has("ArrowUp") || keysPressed.has("w")) {
        setPlayerDirection("up");
      }
      if (keysPressed.has("ArrowDown") || keysPressed.has("s")) {
        setPlayerDirection("down");
      }
      if (keysPressed.has("ArrowLeft") || keysPressed.has("a")) {
        setPlayerDirection("left");
      }
      if (keysPressed.has("ArrowRight") || keysPressed.has("d")) {
        setPlayerDirection("right");
      }

      setPlayerPosition((current: PlayerPosition) => {
        let newX = current.x;
        let newY = current.y;

        if (keysPressed.has("ArrowUp") || keysPressed.has("w")) {
          newY -= PLAYER_MOVE_STEP;
        }
        if (keysPressed.has("ArrowDown") || keysPressed.has("s")) {
          newY += PLAYER_MOVE_STEP;
        }
        if (keysPressed.has("ArrowLeft") || keysPressed.has("a")) {
          newX -= PLAYER_MOVE_STEP;
        }
        if (keysPressed.has("ArrowRight") || keysPressed.has("d")) {
          newX += PLAYER_MOVE_STEP;
        }

        newX = Math.max(OFFICE_BOUNDS.minX, Math.min(OFFICE_BOUNDS.maxX, newX));
        newY = Math.max(OFFICE_BOUNDS.minY, Math.min(OFFICE_BOUNDS.maxY, newY));

        if (checkDeskCollision(newX, newY, deskSlots)) {
          return current;
        }

        return { x: newX, y: newY };
      });

      animationFrame = requestAnimationFrame(movePlayer);
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      const key = event.key;
      const target = event.target as HTMLElement | null;
      const isTyping =
        target instanceof HTMLInputElement ||
        target instanceof HTMLTextAreaElement ||
        target?.isContentEditable;

      if (["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"].includes(key)) {
        event.preventDefault();
        if (!keysPressed.has(key)) {
          keysPressed.add(key);
          if (animationFrame === null) {
            animationFrame = requestAnimationFrame(movePlayer);
          }
        }
      } else if (["w", "a", "s", "d"].includes(key) && !isTyping) {
        event.preventDefault();
        if (!keysPressed.has(key)) {
          keysPressed.add(key);
          if (animationFrame === null) {
            animationFrame = requestAnimationFrame(movePlayer);
          }
        }
      }
    };

    const handleKeyUp = (event: KeyboardEvent) => {
      keysPressed.delete(event.key);
      if (keysPressed.size === 0) {
        setIsPlayerWalking(false);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("keyup", handleKeyUp);

    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("keyup", handleKeyUp);
      if (animationFrame !== null) {
        cancelAnimationFrame(animationFrame);
      }
    };
  }, [active, deskSlots]);

  return {
    playerPosition,
    playerDirection,
    isPlayerWalking,
  };
}
