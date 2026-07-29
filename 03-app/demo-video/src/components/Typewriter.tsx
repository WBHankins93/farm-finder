import React from "react";
import { useCurrentFrame } from "remotion";

// Reveals `text` character-by-character between start and start+duration,
// with a blinking caret.
export const Typewriter: React.FC<{
  text: string;
  start: number;
  cps?: number; // characters per second
  fps?: number;
  showCaret?: boolean;
  style?: React.CSSProperties;
}> = ({ text, start, cps = 22, fps = 30, showCaret = true, style }) => {
  const frame = useCurrentFrame();
  const elapsed = Math.max(0, frame - start);
  const chars = Math.min(text.length, Math.floor((elapsed / fps) * cps));
  const done = chars >= text.length;
  const caretOn = Math.floor(frame / 8) % 2 === 0;
  return (
    <span style={style}>
      {text.slice(0, chars)}
      {showCaret && (!done || caretOn) && frame >= start && (
        <span style={{ opacity: caretOn ? 1 : 0.15, fontWeight: 400 }}>|</span>
      )}
    </span>
  );
};
