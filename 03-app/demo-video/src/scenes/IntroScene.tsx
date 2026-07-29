import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { colors, fonts } from "../theme";
import { AtlasPlate } from "../components/AtlasPlate";
import { Eyebrow } from "../components/atoms";

// Dark "field desk" open: contour rings ink in, wordmark and thesis rise.
export const IntroScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  const wordmark = spring({ frame: frame - 18, fps, config: { damping: 200 }, durationInFrames: 26 });
  const title = spring({ frame: frame - 34, fps, config: { damping: 200 }, durationInFrames: 34 });
  const sub = spring({ frame: frame - 58, fps, config: { damping: 200 }, durationInFrames: 24 });
  const fade = interpolate(frame, [95, 118], [1, 0], { extrapolateLeft: "clamp" });

  return (
    <AbsoluteFill style={{ background: colors.green, opacity: fade }}>
      {/* paper grain vignette */}
      <AbsoluteFill style={{ opacity: 0.9 }}>
        <AtlasPlate width={width} height={height} tone="dark" revealStart={0} />
      </AbsoluteFill>
      <AbsoluteFill
        style={{
          justifyContent: "center",
          alignItems: "flex-start",
          padding: "0 clamp(60px, 8vw, 130px)",
        }}
      >
        <div style={{ opacity: wordmark, transform: `translateY(${interpolate(wordmark, [0, 1], [16, 0])}px)` }}>
          <Eyebrow color={colors.brass} style={{ fontSize: 18 }}>
            FarmFinder · U.S. Farm Field Guide
          </Eyebrow>
        </div>
        <div
          style={{
            marginTop: 22,
            fontFamily: fonts.serif,
            color: colors.cream,
            fontSize: 108,
            lineHeight: 0.98,
            letterSpacing: "-0.02em",
            fontWeight: 500,
            opacity: title,
            transform: `translateY(${interpolate(title, [0, 1], [26, 0])}px)`,
          }}
        >
          Find the farms
          <br />
          behind your food.
        </div>
        <div
          style={{
            marginTop: 34,
            fontFamily: fonts.sans,
            color: "rgba(251,252,246,0.82)",
            fontSize: 26,
            maxWidth: 720,
            opacity: sub,
            transform: `translateY(${interpolate(sub, [0, 1], [16, 0])}px)`,
          }}
        >
          A living atlas of local growers, markets, pickup, and ordering paths —
          launching in Louisiana &amp; Mississippi.
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
