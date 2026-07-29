import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { colors, categoryColors, fonts } from "../theme";
import { AppFrame } from "../components/AppFrame";
import { Eyebrow, DrawRule } from "../components/atoms";
import { Typewriter } from "../components/Typewriter";
import { Cursor } from "../components/Cursor";
import { farms } from "../data/farms";

// The dark "field desk" question inset: a practical question is typed, then a
// grounded answer register resolves with real farm records.
export const AskScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const question = "Where can I find a vegetable CSA near New Orleans?";
  const typeStart = 22;
  const typeDur = (question.length / 22) * fps; // matches cps=22
  const askClick = Math.round(typeStart + typeDur + 8);
  const thinking = interpolate(frame, [askClick, askClick + 8], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const answerStart = askClick + 26;

  const results = farms.filter((f) =>
    ["river-queen-greens", "jot-tittle-farms", "covey-rise-farm"].includes(f.id)
  );
  const distances: Record<string, string> = {
    "river-queen-greens": "in New Orleans",
    "jot-tittle-farms": "~48 mi · St. Amant",
    "covey-rise-farm": "~55 mi · Husser",
  };

  const panelIn = spring({ frame: frame - 4, fps, config: { damping: 200 }, durationInFrames: 24 });

  return (
    <AppFrame activeNav="Ask">
      <AbsoluteFill style={{ padding: "44px 60px" }}>
        <div style={{ opacity: panelIn }}>
          <Eyebrow color={colors.green2}>Ask the field guide</Eyebrow>
          <div
            style={{
              marginTop: 8,
              fontFamily: fonts.serif,
              fontSize: 40,
              color: colors.ink,
              fontWeight: 500,
            }}
          >
            A practical question, a grounded answer.
          </div>
        </div>

        {/* dark field desk */}
        <div
          style={{
            marginTop: 26,
            background: colors.green,
            borderRadius: 14,
            padding: 30,
            transform: `translateY(${interpolate(panelIn, [0, 1], [24, 0])}px)`,
            opacity: panelIn,
            boxShadow: "0 1px 0 rgba(23,37,29,0.4)",
          }}
        >
          {/* input row */}
          <div style={{ display: "flex", gap: 14, alignItems: "stretch" }}>
            <div
              style={{
                flex: 1,
                background: "rgba(251,252,246,0.06)",
                border: "1.5px solid rgba(251,252,246,0.32)",
                borderRadius: 10,
                padding: "18px 22px",
                fontFamily: fonts.sans,
                fontSize: 24,
                color: colors.cream,
                minHeight: 30,
              }}
            >
              {frame < typeStart ? (
                <span style={{ color: "rgba(251,252,246,0.4)" }}>
                  Ask about a product, season, or way to buy…
                </span>
              ) : (
                <Typewriter text={question} start={typeStart} cps={22} fps={fps} />
              )}
            </div>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                background: colors.rust,
                color: colors.cream,
                borderRadius: 10,
                padding: "0 30px",
                fontFamily: fonts.sans,
                fontSize: 21,
                fontWeight: 600,
                transform: frame >= askClick && frame <= askClick + 6 ? "scale(0.96)" : "scale(1)",
              }}
            >
              Ask →
            </div>
          </div>

          {/* suggested chips (before ask) */}
          {frame < askClick && (
            <div style={{ display: "flex", gap: 12, marginTop: 18, opacity: 0.85 }}>
              {["Vegetables in season", "CSA near me", "Where to buy honey"].map((s) => (
                <span
                  key={s}
                  style={{
                    fontFamily: fonts.sans,
                    fontSize: 15,
                    color: colors.cream,
                    border: "1px solid rgba(251,252,246,0.3)",
                    borderRadius: 999,
                    padding: "8px 16px",
                  }}
                >
                  {s}
                </span>
              ))}
            </div>
          )}

          {/* thinking */}
          {frame >= askClick && frame < answerStart && (
            <div
              style={{
                marginTop: 22,
                display: "flex",
                alignItems: "center",
                gap: 10,
                fontFamily: fonts.sans,
                color: "rgba(251,252,246,0.75)",
                fontSize: 17,
                opacity: thinking,
              }}
            >
              {[0, 1, 2].map((i) => (
                <span
                  key={i}
                  style={{
                    width: 9,
                    height: 9,
                    borderRadius: 99,
                    background: colors.brass,
                    opacity: 0.4 + 0.6 * Math.abs(Math.sin((frame - askClick) / 5 + i)),
                  }}
                />
              ))}
              Reading the field records…
            </div>
          )}

          {/* answer register */}
          {frame >= answerStart && (
            <div style={{ marginTop: 22 }}>
              <DrawRule start={answerStart} color="rgba(251,252,246,0.4)" height={1} durationInFrames={16} />
              <div
                style={{
                  marginTop: 16,
                  fontFamily: fonts.sans,
                  fontSize: 19,
                  lineHeight: 1.5,
                  color: colors.cream,
                  opacity: interpolate(frame - answerStart, [4, 20], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
                }}
              >
                <strong style={{ color: colors.brass }}>3 CSA farms</strong> grow vegetables within reach of
                New Orleans. Each takes CSA members now; the closest delivers into the city.
              </div>

              <div style={{ display: "flex", gap: 16, marginTop: 20 }}>
                {results.map((f, i) => {
                  const on = interpolate(
                    frame - answerStart,
                    [14 + i * 8, 30 + i * 8],
                    [0, 1],
                    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                  );
                  const c = categoryColors[f.category];
                  return (
                    <div
                      key={f.id}
                      style={{
                        flex: 1,
                        background: colors.cream,
                        borderRadius: 12,
                        padding: 20,
                        opacity: on,
                        transform: `translateY(${interpolate(on, [0, 1], [18, 0])}px)`,
                        borderLeft: `4px solid ${c}`,
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                        <span style={{ fontFamily: fonts.sans, fontSize: 12, letterSpacing: "0.1em", color: colors.green2 }}>
                          {f.recordId}
                        </span>
                        <span style={{ fontFamily: fonts.sans, fontSize: 13, color: colors.rust, fontWeight: 600 }}>
                          {distances[f.id]}
                        </span>
                      </div>
                      <div style={{ fontFamily: fonts.serif, fontSize: 25, color: colors.ink, marginTop: 6, fontWeight: 500 }}>
                        {f.name}
                      </div>
                      <div style={{ fontFamily: fonts.sans, fontSize: 15, color: colors.green2, marginTop: 4 }}>
                        {f.city}, {f.state} · {f.category}
                      </div>
                      <div style={{ fontFamily: fonts.sans, fontSize: 15, color: colors.ink, marginTop: 10, lineHeight: 1.4 }}>
                        {f.productsText}
                      </div>
                      <div style={{ marginTop: 12, display: "flex", gap: 8 }}>
                        <span style={{ fontFamily: fonts.sans, fontSize: 12, fontWeight: 600, color: colors.cream, background: colors.green2, padding: "4px 10px", borderRadius: 999 }}>
                          CSA
                        </span>
                        {f.onlineStore && (
                          <span style={{ fontFamily: fonts.sans, fontSize: 12, fontWeight: 600, color: colors.green, border: `1px solid ${colors.rule}`, padding: "4px 10px", borderRadius: 999 }}>
                            Order online
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </AbsoluteFill>

      {/* cursor: move to input, then to Ask button and click (body-relative) */}
      <Cursor
        appearAt={6}
        keys={[
          { frame: 6, x: 1400, y: 700 },
          { frame: 18, x: 520, y: 232 },
          { frame: askClick - 8, x: 560, y: 232 },
          { frame: askClick - 1, x: 1720, y: 232 },
        ]}
        clicks={[askClick]}
      />
    </AppFrame>
  );
};
