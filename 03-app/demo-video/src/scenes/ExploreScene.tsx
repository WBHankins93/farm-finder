import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { colors, categoryColors, fonts } from "../theme";
import { AppFrame } from "../components/AppFrame";
import { CategoryChip, Eyebrow, ServiceTag } from "../components/atoms";
import { Typewriter } from "../components/Typewriter";
import { Cursor } from "../components/Cursor";
import { MapPanel } from "../components/MapPanel";
import { farms, serviceLabels } from "../data/farms";

// The discovery instrument: search + filters over a synchronized ledger / map
// split. A record is selected and its field-record card resolves.
export const ExploreScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // ledger = produce & mixed vegetable growers
  const ledger = farms
    .filter((f) => ["Produce", "Mixed"].includes(f.category))
    .slice(0, 7);
  const selectedId = "river-queen-greens";
  const selected = farms.find((f) => f.id === selectedId)!;

  const controlsIn = spring({ frame, fps, config: { damping: 200 }, durationInFrames: 20 });
  const searchStart = 16;
  const selectClick = 210;
  const cardStart = selectClick + 6;

  const bodyW = 1920;
  const bodyH = 1080 - 118;
  const leftW = 720;
  const mapW = bodyW - leftW;
  const mapH = bodyH - 178;

  const cardIn = spring({ frame: frame - cardStart, fps, config: { damping: 22, stiffness: 90 }, durationInFrames: 30 });

  return (
    <AppFrame activeNav="Explore">
      {/* controls bar */}
      <div style={{ position: "absolute", top: 0, left: 0, right: 0, padding: "26px 44px 20px", borderBottom: `1px solid ${colors.rule}`, opacity: controlsIn }}>
        <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
          <Eyebrow color={colors.green2}>Explore</Eyebrow>
          <div
            style={{
              flex: 1,
              maxWidth: 620,
              background: colors.cream,
              border: `1.5px solid ${colors.ink}`,
              borderRadius: 10,
              padding: "13px 18px",
              fontFamily: fonts.sans,
              fontSize: 20,
              color: colors.ink,
              display: "flex",
              alignItems: "center",
              gap: 10,
            }}
          >
            <span style={{ color: colors.green2 }}>⌕</span>
            {frame < searchStart ? (
              <span style={{ color: colors.green2 }}>Search food, farm, or town…</span>
            ) : (
              <Typewriter text="greens" start={searchStart} cps={9} fps={fps} />
            )}
          </div>
          {/* state toggle */}
          <div style={{ display: "flex", border: `1.5px solid ${colors.rule}`, borderRadius: 10, overflow: "hidden" }}>
            {["LA", "MS", "ALL"].map((s) => (
              <span
                key={s}
                style={{
                  fontFamily: fonts.sans,
                  fontSize: 16,
                  fontWeight: 600,
                  padding: "12px 20px",
                  background: s === "ALL" ? colors.green : "transparent",
                  color: s === "ALL" ? colors.cream : colors.ink,
                }}
              >
                {s}
              </span>
            ))}
          </div>
        </div>

        {/* category chips */}
        <div style={{ display: "flex", gap: 10, marginTop: 16, alignItems: "center" }}>
          {["All", "Produce", "Mixed", "Meat", "Honey/Specialty", "Seafood", "Rice"].map((cat) => (
            <CategoryChip key={cat} category={cat} active={cat === "Produce" && frame > 60} />
          ))}
          <span style={{ marginLeft: "auto", fontFamily: fonts.sans, fontSize: 15, color: colors.green2 }}>
            {ledger.length} results · CSA & delivery available
          </span>
        </div>
      </div>

      {/* split: ledger + map */}
      <div style={{ position: "absolute", top: 178, left: 0, right: 0, bottom: 0, display: "flex" }}>
        {/* result ledger */}
        <div style={{ width: leftW, borderRight: `1.5px solid ${colors.ink}`, overflow: "hidden", background: colors.paper }}>
          {ledger.map((f, i) => {
            const on = spring({ frame: frame - (30 + i * 7), fps, config: { damping: 200 }, durationInFrames: 22 });
            const isSel = f.id === selectedId && frame >= selectClick;
            const c = categoryColors[f.category];
            return (
              <div
                key={f.id}
                style={{
                  display: "flex",
                  gap: 16,
                  padding: "18px 26px",
                  borderBottom: `1px solid ${colors.rule}`,
                  background: isSel ? colors.paperDeep : "transparent",
                  borderLeft: isSel ? `4px solid ${colors.rust}` : "4px solid transparent",
                  opacity: on,
                  transform: `translateY(${interpolate(on, [0, 1], [16, 0])}px)`,
                }}
              >
                <span style={{ fontFamily: fonts.sans, fontSize: 14, fontWeight: 600, color: colors.green2, width: 34, paddingTop: 4 }}>
                  {String(i + 1).padStart(3, "0")}
                </span>
                <span style={{ width: 12, height: 12, borderRadius: 3, background: c, marginTop: 8 }} />
                <div style={{ flex: 1 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                    <span style={{ fontFamily: fonts.serif, fontSize: 24, color: colors.ink, fontWeight: 500 }}>{f.name}</span>
                    <span style={{ fontFamily: fonts.sans, fontSize: 13, color: colors.green2, letterSpacing: "0.06em" }}>{f.recordId}</span>
                  </div>
                  <div style={{ fontFamily: fonts.sans, fontSize: 15, color: colors.green2, marginTop: 3 }}>
                    {f.city}, {f.state} · {f.parish}
                  </div>
                  <div style={{ fontFamily: fonts.sans, fontSize: 15, color: colors.ink, marginTop: 7 }}>{f.productsText}</div>
                  <div style={{ display: "flex", gap: 7, marginTop: 10, flexWrap: "wrap" }}>
                    {serviceLabels(f).map((s) => (
                      <ServiceTag key={s} label={s} />
                    ))}
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* map */}
        <div style={{ flex: 1, position: "relative" }}>
          <MapPanel
            width={mapW}
            height={mapH}
            farms={farms}
            dropStart={30}
            selectedId={frame >= selectClick ? selectedId : undefined}
            selectStart={selectClick}
          />

          {/* selected field-record card slides over the map */}
          {frame >= cardStart && (
            <div
              style={{
                position: "absolute",
                right: 24,
                top: 24,
                width: 420,
                background: colors.cream,
                border: `1.5px solid ${colors.ink}`,
                borderRadius: 14,
                padding: 24,
                opacity: cardIn,
                transform: `translateX(${interpolate(cardIn, [0, 1], [60, 0])}px)`,
                boxShadow: "0 18px 40px rgba(23,37,29,0.22)",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontFamily: fonts.sans, fontSize: 12, letterSpacing: "0.16em", textTransform: "uppercase", color: colors.rust, fontWeight: 600 }}>
                  Field record
                </span>
                <span style={{ fontFamily: fonts.sans, fontSize: 13, color: colors.green2 }}>{selected.recordId}</span>
              </div>
              <div style={{ fontFamily: fonts.serif, fontSize: 34, color: colors.ink, marginTop: 10, fontWeight: 500, lineHeight: 1.05 }}>
                {selected.name}
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 8 }}>
                <span style={{ width: 12, height: 12, borderRadius: 3, background: categoryColors[selected.category] }} />
                <span style={{ fontFamily: fonts.sans, fontSize: 16, color: colors.green2 }}>
                  {selected.category} · {selected.city}, {selected.state}
                </span>
              </div>
              <div style={{ height: 1, background: colors.rule, margin: "16px 0" }} />
              <div style={{ fontFamily: fonts.sans, fontSize: 13, letterSpacing: "0.12em", textTransform: "uppercase", color: colors.green2, fontWeight: 600 }}>
                Products
              </div>
              <div style={{ fontFamily: fonts.sans, fontSize: 17, color: colors.ink, marginTop: 6, lineHeight: 1.4 }}>
                {selected.productsText}
              </div>
              <div style={{ fontFamily: fonts.sans, fontSize: 13, letterSpacing: "0.12em", textTransform: "uppercase", color: colors.green2, fontWeight: 600, marginTop: 16 }}>
                Ways to buy
              </div>
              <div style={{ display: "flex", gap: 8, marginTop: 8, flexWrap: "wrap" }}>
                {serviceLabels(selected).map((s) => (
                  <ServiceTag key={s} label={s} />
                ))}
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 18 }}>
                <span style={{ fontFamily: fonts.sans, fontSize: 13, color: colors.green2 }}>
                  ◉ Location confidence: {selected.geoPrecision}
                </span>
                <span style={{ fontFamily: fonts.sans, fontSize: 13, color: colors.green2 }}>
                  Verified {selected.lastVerified}
                </span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* cursor moves down the ledger and clicks River Queen Greens (row 1) */}
      <Cursor
        appearAt={60}
        keys={[
          { frame: 60, x: 900, y: 120 },
          { frame: 130, x: 340, y: 236 },
          { frame: selectClick - 10, x: 340, y: 236 },
          { frame: selectClick - 1, x: 340, y: 236 },
        ]}
        clicks={[selectClick]}
      />
    </AppFrame>
  );
};
