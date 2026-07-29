import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { colors, fonts } from "../theme";
import { AppFrame } from "../components/AppFrame";
import { DrawRule, Eyebrow } from "../components/atoms";

type Crop = { n: string; label: string; color: string; season: string; count: number };

const crops: Crop[] = [
  { n: "01", label: "Vegetables & greens", color: "#4d735b", season: "Tomatoes, okra, squash, peas & field greens", count: 168 },
  { n: "02", label: "Fruit & berries", color: "#c65e36", season: "Blueberries, citrus, figs & stone fruit", count: 54 },
  { n: "03", label: "Eggs & poultry", color: "#a28745", season: "Pasture-raised year-round", count: 61 },
  { n: "04", label: "Beef & pork", color: "#863f32", season: "Grass-fed & pastured, by the cut or share", count: 56 },
  { n: "05", label: "Honey & specialty", color: "#a28745", season: "Wildflower & tupelo honey, preserves", count: 28 },
  { n: "06", label: "Gulf seafood", color: "#397386", season: "Wild-caught shrimp, oysters & fish", count: 9 },
];

// The harvest index: crop rows, not an equal-card grid. The selected row draws
// a rule and reveals its season detail.
export const HarvestScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const header = spring({ frame, fps, config: { damping: 200 }, durationInFrames: 22 });
  const selectedIndex = 0; // Vegetables highlighted
  const selectAt = 70;

  return (
    <AppFrame activeNav="Harvest">
      <AbsoluteFill style={{ padding: "48px 60px" }}>
        <div style={{ opacity: header, display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
          <div>
            <Eyebrow color={colors.green2}>Harvest index</Eyebrow>
            <div style={{ marginTop: 8, fontFamily: fonts.serif, fontSize: 40, color: colors.ink, fontWeight: 500 }}>
              What&apos;s growing, and who grows it.
            </div>
          </div>
          <span style={{ fontFamily: fonts.sans, fontSize: 15, color: colors.green2, letterSpacing: "0.04em" }}>
            Browse by what you want to cook →
          </span>
        </div>

        <div style={{ marginTop: 30 }}>
          {crops.map((c, i) => {
            const on = spring({ frame: frame - (10 + i * 6), fps, config: { damping: 200 }, durationInFrames: 22 });
            const selected = i === selectedIndex && frame >= selectAt;
            return (
              <div
                key={c.n}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 26,
                  padding: "22px 24px",
                  borderTop: `1px solid ${colors.rule}`,
                  borderBottom: i === crops.length - 1 ? `1px solid ${colors.rule}` : "none",
                  background: selected ? colors.paperDeep : "transparent",
                  opacity: on,
                  transform: `translateX(${interpolate(on, [0, 1], [-24, 0])}px)`,
                }}
              >
                <span style={{ fontFamily: fonts.sans, fontSize: 18, fontWeight: 600, color: colors.green2, width: 34 }}>
                  {c.n}
                </span>
                <span style={{ width: 16, height: 16, borderRadius: 4, background: c.color }} />
                <span
                  style={{
                    fontFamily: fonts.serif,
                    fontSize: 34,
                    color: colors.ink,
                    fontWeight: 500,
                    minWidth: 420,
                  }}
                >
                  {c.label}
                </span>

                {selected ? (
                  <span
                    style={{
                      fontFamily: fonts.sans,
                      fontSize: 17,
                      color: colors.green,
                      flex: 1,
                      opacity: interpolate(frame - selectAt, [4, 16], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
                    }}
                  >
                    {c.season}
                  </span>
                ) : (
                  <span style={{ flex: 1 }} />
                )}

                <span
                  style={{
                    fontFamily: fonts.sans,
                    fontSize: 16,
                    fontWeight: 600,
                    color: colors.ink,
                    background: colors.cream,
                    border: `1px solid ${colors.rule}`,
                    borderRadius: 999,
                    padding: "6px 15px",
                  }}
                >
                  {c.count} farms
                </span>
              </div>
            );
          })}
          <div style={{ marginTop: 4 }}>
            {frame >= selectAt && <DrawRule start={selectAt} color={colors.rust} height={2.5} durationInFrames={16} style={{ width: "34%" }} />}
          </div>
        </div>
      </AbsoluteFill>
    </AppFrame>
  );
};
