/**
 * RemoteCursor — renders a colored arrow cursor with a name label for a
 * remote player's mouse position in the Hand World scene.
 */
import type { CSSProperties } from "react";

export type RemoteCursorProps = {
  name: string;
  color: string;
  x: number;
  y: number;
};

export default function RemoteCursor({ name, color, x, y }: RemoteCursorProps) {
  const style: CSSProperties = {
    left: `${x}%`,
    top: `${y}%`,
    "--cursor-color": color,
  } as CSSProperties;

  return (
    <div className="remote-cursor" style={style} aria-label={`${name}'s cursor`}>
      <svg
        className="remote-cursor-arrow"
        width="16"
        height="20"
        viewBox="0 0 16 20"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <path
          d="M1 1L6 18L8.5 10.5L15 8.5L1 1Z"
          fill={color}
          stroke="white"
          strokeWidth="1.5"
          strokeLinejoin="round"
        />
      </svg>
      <span className="remote-cursor-label" style={{ backgroundColor: color }}>
        {name}
      </span>
    </div>
  );
}
