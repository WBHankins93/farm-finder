import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { colors, fonts } from "../theme";
import { AtlasPlate } from "../components/AtlasPlate";
import { CountUp, DrawRule, Eyebrow } from "../components/atoms";

// Closing card: coverage ledger and the "expanding region by region" thesis.
export const OutroScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const fadeIn = interpolate(frame, [0, 14], [0, 1], { extrapolateRight: "clamp" });
  const title = spring({ frame: frame - 12, fps, config: { damping: 200 }, durationInFrames: 30 });

  return (
    <AbsoluteFill style={{ background: colors.green, opacity: fadeIn }}>
      <AbsoluteFill style={{ opacity: 0.85 }}>
        <AtlasPlate width={width} height={height} tone="dark" revealStart={0} />
      </AbsoluteFill>
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", textAlign: "center", padding: "0 120px" }}>
        <Eyebrow color={colors.brass} style={{ fontSize: 17 }}>
          FarmFinder · U.S. Farm Field Guide
        </Eyebrow>
        <div
          style={{
            marginTop: 22,
            fontFamily: fonts.serif,
            color: colors.cream,
            fontSize: 80,
            lineHeight: 1.02,
            fontWeight: 500,
            letterSpacing: "-0.02em",
            opacity: title,
            transform: `translateY(${interpolate(title, [0, 1], [22, 0])}px)`,
          }}
        >
          Local food, mapped honestly.
        </div>

        <div style={{ width: 560, marginTop: 34 }}>
          <DrawRule start={30} color="rgba(251,252,246,0.5)" height={1} durationInFrames={22} />
        </div>

        <div style={{ display: "flex", gap: 70, marginTop: 30 }}>
          {[
            { n: 299, l: "farms mapped" },
            { n: 2, l: "states live" },
            { n: 9, l: "product categories" },
          ].map((it, i) => (
            <div key={it.l}>
              <div style={{ fontFamily: fonts.serif, fontSize: 56, color: colors.cream, fontWeight: 500 }}>
                <CountUp to={it.n} start={20 + i * 5} durationInFrames={40} />
              </div>
              <div style={{ fontFamily: fonts.sans, fontSize: 14, letterSpacing: "0.16em", textTransform: "uppercase", color: colors.brass, fontWeight: 600, marginTop: 6 }}>
                {it.l}
              </div>
            </div>
          ))}
        </div>

        <div style={{ marginTop: 40, fontFamily: fonts.sans, fontSize: 22, color: "rgba(251,252,246,0.85)" }}>
          Louisiana &amp; Mississippi live — expanding region by region.
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
