import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

export type CursorKey = { frame: number; x: number; y: number };

// Eased pointer that moves through a set of keyframes, with a click ripple.
export const Cursor: React.FC<{
  keys: CursorKey[];
  clicks?: number[];
  appearAt?: number;
}> = ({ keys, clicks = [], appearAt = 0 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // find surrounding keyframes
  let x = keys[0].x;
  let y = keys[0].y;
  for (let i = 0; i < keys.length - 1; i++) {
    const a = keys[i];
    const b = keys[i + 1];
    if (frame >= a.frame && frame <= b.frame) {
      const t = spring({
        frame: frame - a.frame,
        fps,
        durationInFrames: b.frame - a.frame,
        config: { damping: 200 },
      });
      x = interpolate(t, [0, 1], [a.x, b.x]);
      y = interpolate(t, [0, 1], [a.y, b.y]);
      break;
    }
    if (frame > b.frame) {
      x = b.x;
      y = b.y;
    }
  }

  const appear = interpolate(frame - appearAt, [0, 10], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // click ripple
  const activeClick = clicks.find((c) => frame >= c && frame <= c + 20);
  const ripple = activeClick
    ? interpolate(frame - activeClick, [0, 20], [0, 1], {
        extrapolateRight: "clamp",
      })
    : null;
  const press = activeClick
    ? interpolate(frame - activeClick, [0, 4, 10], [1, 0.86, 1], {
        extrapolateRight: "clamp",
      })
    : 1;

  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y,
        opacity: appear,
        transform: `scale(${press})`,
        transformOrigin: "top left",
        pointerEvents: "none",
        zIndex: 50,
      }}
    >
      {ripple !== null && (
        <div
          style={{
            position: "absolute",
            left: -2,
            top: -2,
            width: 44,
            height: 44,
            marginLeft: -22 + 2,
            marginTop: -22 + 2,
            borderRadius: "50%",
            border: "2px solid rgba(198,94,54,0.9)",
            transform: `translate(-50%,-50%) scale(${0.2 + ripple * 1})`,
            opacity: 1 - ripple,
          }}
        />
      )}
      <svg width={30} height={30} viewBox="0 0 24 24" style={{ filter: "drop-shadow(0 2px 4px rgba(0,0,0,0.35))" }}>
        <path
          d="M4 2 L4 20 L9 15 L12.5 22.5 L15.5 21 L12 13.5 L19 13.5 Z"
          fill="#fbfcf6"
          stroke="#17251d"
          strokeWidth={1.4}
          strokeLinejoin="round"
        />
      </svg>
    </div>
  );
};
