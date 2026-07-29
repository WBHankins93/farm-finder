import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { colors, categoryColors, fonts } from "../theme";
import { Farm, project } from "../data/farms";

// A living map panel: paper base, river slate water, contour texture and
// dropped category pins for each farm. `selectedId` gets a rust confidence ring.
export const MapPanel: React.FC<{
  width: number;
  height: number;
  farms: Farm[];
  dropStart?: number;
  selectedId?: string;
  selectStart?: number;
}> = ({ width, height, farms, dropStart = 0, selectedId, selectStart = 0 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <div
      style={{
        position: "relative",
        width,
        height,
        background: "#dfe4d6",
        overflow: "hidden",
      }}
    >
      {/* water / river slate wash */}
      <svg width={width} height={height} style={{ position: "absolute", inset: 0 }}>
        <rect width={width} height={height} fill="#dfe4d6" />
        <path
          d={`M 0 ${height * 0.86} C ${width * 0.3} ${height * 0.78}, ${width * 0.5} ${height} , ${width} ${height * 0.9} L ${width} ${height} L 0 ${height} Z`}
          fill={colors.river}
          opacity={0.22}
        />
        <path
          d={`M ${width * 0.2} ${height * 0.1} C ${width * 0.4} ${height * 0.3}, ${width * 0.28} ${height * 0.55}, ${width * 0.52} ${height * 0.7}`}
          fill="none"
          stroke={colors.river}
          strokeWidth={5}
          opacity={0.4}
          strokeLinecap="round"
        />
        {/* contour texture */}
        <g stroke="#c3cbb8" strokeWidth={1} fill="none" opacity={0.7}>
          {Array.from({ length: 6 }).map((_, i) => (
            <circle key={i} cx={width * 0.66} cy={height * 0.38} r={40 + i * 46} />
          ))}
        </g>
        {/* state label */}
      </svg>
      <div
        style={{
          position: "absolute",
          top: 14,
          left: 16,
          fontFamily: fonts.sans,
          fontSize: 12,
          fontWeight: 600,
          letterSpacing: "0.18em",
          color: colors.green,
          textTransform: "uppercase",
          background: "rgba(251,252,246,0.75)",
          padding: "5px 10px",
          borderRadius: 6,
        }}
      >
        Living map · LA · MS
      </div>

      {/* pins */}
      {farms.map((f, i) => {
        const { x, y } = project(f.latitude, f.longitude, width, height);
        const c = categoryColors[f.category] ?? colors.green2;
        const isSel = f.id === selectedId;
        const drop = spring({
          frame: frame - (dropStart + i * 4),
          fps,
          durationInFrames: 22,
          config: { damping: 12, stiffness: 120 },
        });
        const rise = interpolate(drop, [0, 1], [-26, 0]);
        const selPulse = isSel
          ? 1 + 0.15 * Math.sin((frame - selectStart) / 6)
          : 1;
        return (
          <div
            key={f.id}
            style={{
              position: "absolute",
              left: x,
              top: y,
              transform: `translate(-50%, -100%) translateY(${rise}px) scale(${drop})`,
              opacity: drop,
              zIndex: isSel ? 20 : 5,
            }}
          >
            {isSel && (
              <div
                style={{
                  position: "absolute",
                  left: "50%",
                  bottom: -6,
                  width: 46 * selPulse,
                  height: 46 * selPulse,
                  marginLeft: (-46 * selPulse) / 2,
                  marginBottom: (-46 * selPulse) / 2,
                  borderRadius: "50%",
                  border: `2px solid ${colors.rust}`,
                  opacity: 0.7,
                }}
              />
            )}
            <svg width={26} height={34} viewBox="0 0 26 34">
              <path
                d="M13 33 C13 33 24 20 24 12 A11 11 0 1 0 2 12 C2 20 13 33 13 33 Z"
                fill={isSel ? colors.rust : c}
                stroke={colors.cream}
                strokeWidth={2}
              />
              <circle cx={13} cy={12} r={4.2} fill={colors.cream} />
            </svg>
          </div>
        );
      })}
    </div>
  );
};
