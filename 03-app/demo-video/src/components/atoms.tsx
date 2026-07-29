import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { colors, categoryColors, fonts } from "../theme";

// A small uppercase, widely-tracked metadata label.
export const Eyebrow: React.FC<{
  children: React.ReactNode;
  color?: string;
  style?: React.CSSProperties;
}> = ({ children, color = colors.ink, style }) => (
  <span
    style={{
      fontFamily: fonts.sans,
      fontSize: 15,
      fontWeight: 600,
      letterSpacing: "0.22em",
      textTransform: "uppercase",
      color,
      ...style,
    }}
  >
    {children}
  </span>
);

// Fine-bordered transparent pill — the FarmFinder action stamp.
export const Pill: React.FC<{
  children: React.ReactNode;
  color?: string;
  filled?: boolean;
  style?: React.CSSProperties;
}> = ({ children, color = colors.ink, filled, style }) => (
  <span
    style={{
      display: "inline-flex",
      alignItems: "center",
      gap: 10,
      fontFamily: fonts.sans,
      fontSize: 17,
      fontWeight: 500,
      letterSpacing: "0.03em",
      padding: "13px 26px",
      borderRadius: 999,
      border: `1.5px solid ${color}`,
      color: filled ? colors.cream : color,
      background: filled ? color : "transparent",
      ...style,
    }}
  >
    {children}
  </span>
);

// A category chip with the color square that always accompanies text.
export const CategoryChip: React.FC<{
  category: string;
  active?: boolean;
}> = ({ category, active }) => {
  const c = categoryColors[category] ?? colors.green2;
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 9,
        fontFamily: fonts.sans,
        fontSize: 15,
        fontWeight: 500,
        padding: "8px 15px",
        borderRadius: 999,
        border: `1.5px solid ${active ? c : colors.rule}`,
        background: active ? c : "transparent",
        color: active ? colors.cream : colors.ink,
        whiteSpace: "nowrap",
      }}
    >
      <span
        style={{
          width: 10,
          height: 10,
          borderRadius: 3,
          background: active ? colors.cream : c,
        }}
      />
      {category}
    </span>
  );
};

// Small service tag used on records.
export const ServiceTag: React.FC<{ label: string }> = ({ label }) => (
  <span
    style={{
      fontFamily: fonts.sans,
      fontSize: 13,
      fontWeight: 500,
      letterSpacing: "0.02em",
      color: colors.green,
      padding: "4px 11px",
      borderRadius: 999,
      border: `1px solid ${colors.rule}`,
      background: colors.cream,
    }}
  >
    {label}
  </span>
);

// A horizontal rule that "draws in" like a field-note annotation.
export const DrawRule: React.FC<{
  start: number;
  color?: string;
  height?: number;
  durationInFrames?: number;
  style?: React.CSSProperties;
}> = ({ start, color = colors.ink, height = 2, durationInFrames = 18, style }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = spring({
    frame: frame - start,
    fps,
    config: { damping: 200 },
    durationInFrames,
  });
  return (
    <div
      style={{
        height,
        background: color,
        transformOrigin: "left center",
        transform: `scaleX(${p})`,
        ...style,
      }}
    />
  );
};

// Rising-count number for the coverage ledger.
export const CountUp: React.FC<{
  to: number;
  start: number;
  durationInFrames?: number;
  style?: React.CSSProperties;
}> = ({ to, start, durationInFrames = 40, style }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = spring({
    frame: frame - start,
    fps,
    config: { damping: 200 },
    durationInFrames,
  });
  const value = Math.round(interpolate(p, [0, 1], [0, to]));
  return <span style={style}>{value}</span>;
};
