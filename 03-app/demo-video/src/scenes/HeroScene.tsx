import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { colors, fonts } from "../theme";
import { AppFrame } from "../components/AppFrame";
import { AtlasPlate } from "../components/AtlasPlate";
import { CountUp, DrawRule, Eyebrow, Pill } from "../components/atoms";

// The atlas hero: eyebrow, oversized editorial title, one action, coverage
// ledger that counts up.
export const HeroScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const enter = (d: number) =>
    spring({ frame: frame - d, fps, config: { damping: 200 }, durationInFrames: 26 });

  const title = enter(6);
  const cta = enter(30);
  const ledger = enter(46);

  const ledgerItems = [
    { n: 299, label: "farms mapped" },
    { n: 220, label: "Louisiana" },
    { n: 79, label: "Mississippi" },
  ];

  return (
    <AppFrame>
      {/* atlas plate on the right */}
      <AbsoluteFill style={{ left: "44%" }}>
        <AtlasPlate width={1075} height={880} revealStart={0} />
      </AbsoluteFill>
      {/* soft paper wash so text stays readable over plate */}
      <AbsoluteFill
        style={{
          background: `linear-gradient(100deg, ${colors.paper} 40%, rgba(238,240,230,0.65) 58%, rgba(238,240,230,0) 74%)`,
        }}
      />

      <div style={{ position: "absolute", top: 56, left: 60, right: 60 }}>
        <Eyebrow color={colors.rust}>
          LA · MS live · expanding region by region
        </Eyebrow>
        <span
          style={{
            float: "right",
            fontFamily: fonts.sans,
            fontSize: 13,
            letterSpacing: "0.18em",
            textTransform: "uppercase",
            color: colors.green2,
            border: `1px solid ${colors.rule}`,
            borderRadius: 6,
            padding: "6px 12px",
          }}
        >
          Field record / Jul 2026
        </span>
      </div>

      <div style={{ position: "absolute", top: 132, left: 60, maxWidth: 760 }}>
        <div
          style={{
            fontFamily: fonts.serif,
            fontSize: 96,
            lineHeight: 0.96,
            letterSpacing: "-0.02em",
            color: colors.ink,
            fontWeight: 500,
            opacity: title,
            transform: `translateY(${interpolate(title, [0, 1], [24, 0])}px)`,
          }}
        >
          Find the farms,
          <br />
          <span style={{ color: colors.green }}>behind your food.</span>
        </div>

        <div
          style={{
            marginTop: 30,
            fontFamily: fonts.sans,
            fontSize: 24,
            color: colors.ink,
            maxWidth: 560,
            opacity: cta,
          }}
        >
          Find growers, markets, pickup, and ordering paths near you.
        </div>

        <div style={{ marginTop: 30, opacity: cta, transform: `translateY(${interpolate(cta, [0, 1], [14, 0])}px)` }}>
          <Pill color={colors.rust} filled>
            Find food near you ↓
          </Pill>
        </div>
      </div>

      {/* coverage ledger */}
      <div style={{ position: "absolute", left: 60, right: 60, bottom: 64, opacity: ledger }}>
        <DrawRule start={46} color={colors.ink} height={1.5} durationInFrames={20} />
        <div style={{ display: "flex", gap: 72, marginTop: 22 }}>
          {ledgerItems.map((it, i) => (
            <div key={it.label}>
              <div
                style={{
                  fontFamily: fonts.serif,
                  fontSize: 52,
                  fontWeight: 500,
                  color: i === 0 ? colors.green : colors.ink,
                  lineHeight: 1,
                }}
              >
                <CountUp to={it.n} start={48 + i * 6} durationInFrames={44} />
              </div>
              <div
                style={{
                  marginTop: 8,
                  fontFamily: fonts.sans,
                  fontSize: 15,
                  letterSpacing: "0.14em",
                  textTransform: "uppercase",
                  color: colors.green2,
                  fontWeight: 600,
                }}
              >
                {it.label}
              </div>
            </div>
          ))}
          <div style={{ marginLeft: "auto", alignSelf: "flex-end" }}>
            <span
              style={{
                fontFamily: fonts.sans,
                fontSize: 14,
                color: colors.green2,
                letterSpacing: "0.04em",
              }}
            >
              Source-verified · last checked 2026-07-15
            </span>
          </div>
        </div>
      </div>
    </AppFrame>
  );
};
