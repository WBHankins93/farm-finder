import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { colors } from "../theme";

// The living-atlas plate: concentric contour rings, parcel lines, a river
// curve and a scatter of map pins. Drawn entirely in SVG per the design
// system's "no hero raster asset" rule.
export const AtlasPlate: React.FC<{
  width: number;
  height: number;
  revealStart?: number;
  tone?: "light" | "dark";
}> = ({ width, height, revealStart = 0, tone = "light" }) => {
  const frame = useCurrentFrame();
  const cx = width * 0.62;
  const cy = height * 0.44;

  const line = tone === "dark" ? "rgba(230,235,222,0.16)" : colors.rule;
  const lineStrong = tone === "dark" ? "rgba(230,235,222,0.30)" : "#a9b3a3";
  const riverCol = colors.river;

  const contourReveal = interpolate(frame - revealStart, [0, 60], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const rings = [70, 130, 195, 265, 340, 420];

  const pins = [
    { x: 0.30, y: 0.30 },
    { x: 0.52, y: 0.22 },
    { x: 0.70, y: 0.36 },
    { x: 0.44, y: 0.52 },
    { x: 0.63, y: 0.60 },
    { x: 0.80, y: 0.55 },
    { x: 0.36, y: 0.72 },
    { x: 0.58, y: 0.78 },
  ];

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      style={{ display: "block" }}
    >
      {/* parcel grid */}
      <g stroke={line} strokeWidth={1}>
        {Array.from({ length: 9 }).map((_, i) => {
          const gx = (width / 8) * i;
          return <line key={`v${i}`} x1={gx} y1={0} x2={gx - 60} y2={height} opacity={0.5} />;
        })}
        {Array.from({ length: 7 }).map((_, i) => {
          const gy = (height / 6) * i;
          return <line key={`h${i}`} x1={0} y1={gy} x2={width} y2={gy + 34} opacity={0.4} />;
        })}
      </g>

      {/* river curve */}
      <path
        d={`M ${width * 0.05} ${height * 0.12}
            C ${width * 0.35} ${height * 0.28}, ${width * 0.18} ${height * 0.5}, ${width * 0.45} ${height * 0.62}
            S ${width * 0.7} ${height * 0.86}, ${width * 0.98} ${height * 0.8}`}
        fill="none"
        stroke={riverCol}
        strokeWidth={7}
        strokeLinecap="round"
        opacity={0.55}
        strokeDasharray={1400}
        strokeDashoffset={1400 * (1 - contourReveal)}
      />

      {/* contour rings */}
      <g fill="none" stroke={lineStrong} strokeWidth={1.4}>
        {rings.map((r, i) => {
          const on = interpolate(
            frame - revealStart,
            [i * 6, i * 6 + 30],
            [0, 1],
            { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
          );
          return (
            <circle
              key={r}
              cx={cx}
              cy={cy}
              r={r}
              opacity={0.6 * on}
              strokeDasharray={2 * Math.PI * r}
              strokeDashoffset={2 * Math.PI * r * (1 - on)}
            />
          );
        })}
      </g>

      {/* pins */}
      {pins.map((p, i) => {
        const on = interpolate(
          frame - revealStart,
          [30 + i * 5, 45 + i * 5],
          [0, 1],
          { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
        );
        const px = p.x * width;
        const py = p.y * height;
        return (
          <g key={i} opacity={on} transform={`translate(${px}, ${py})`}>
            <circle r={9} fill={colors.rust} opacity={0.18} />
            <circle r={4} fill={colors.rust} />
            <circle r={4} fill="none" stroke={colors.rust} strokeWidth={1.4} />
          </g>
        );
      })}
    </svg>
  );
};
