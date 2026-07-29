import React from "react";
import { colors, fonts } from "../theme";

// The site header — the "notebook binding" — plus a light browser chrome so
// the demo reads as a real product screen.
export const AppFrame: React.FC<{
  children: React.ReactNode;
  activeNav?: "Ask" | "Harvest" | "Explore";
}> = ({ children, activeNav }) => {
  const nav: Array<"Ask" | "Harvest" | "Explore"> = ["Ask", "Harvest", "Explore"];
  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        background: colors.paper,
        display: "flex",
        flexDirection: "column",
        fontFamily: fonts.sans,
      }}
    >
      {/* browser chrome */}
      <div
        style={{
          height: 46,
          background: "#e4e7dc",
          borderBottom: `1px solid ${colors.rule}`,
          display: "flex",
          alignItems: "center",
          padding: "0 20px",
          gap: 9,
          flex: "0 0 auto",
        }}
      >
        <span style={{ width: 12, height: 12, borderRadius: 99, background: "#c65e36" }} />
        <span style={{ width: 12, height: 12, borderRadius: 99, background: "#a28745" }} />
        <span style={{ width: 12, height: 12, borderRadius: 99, background: "#4d735b" }} />
        <div
          style={{
            marginLeft: 18,
            flex: 1,
            maxWidth: 520,
            height: 26,
            borderRadius: 8,
            background: colors.cream,
            border: `1px solid ${colors.rule}`,
            display: "flex",
            alignItems: "center",
            padding: "0 14px",
            fontSize: 13,
            color: colors.green2,
            letterSpacing: "0.01em",
          }}
        >
          farmfinder.app
        </div>
      </div>

      {/* site header / binding */}
      <div
        style={{
          height: 72,
          background: colors.paper,
          borderBottom: `1.5px solid ${colors.ink}`,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0 44px",
          flex: "0 0 auto",
        }}
      >
        <div style={{ display: "flex", alignItems: "baseline", gap: 14 }}>
          <span
            style={{
              fontFamily: fonts.sans,
              fontWeight: 700,
              fontSize: 20,
              letterSpacing: "0.14em",
              color: colors.ink,
            }}
          >
            FARMFINDER
          </span>
          <span
            style={{
              fontSize: 12,
              letterSpacing: "0.2em",
              textTransform: "uppercase",
              color: colors.green2,
              fontWeight: 600,
            }}
          >
            U.S. Farm Field Guide
          </span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 30 }}>
          {nav.map((n) => (
            <span
              key={n}
              style={{
                fontSize: 15,
                fontWeight: activeNav === n ? 700 : 500,
                letterSpacing: "0.03em",
                color: activeNav === n ? colors.rust : colors.ink,
                borderBottom: activeNav === n ? `2px solid ${colors.rust}` : "2px solid transparent",
                paddingBottom: 3,
              }}
            >
              {n}
            </span>
          ))}
          <span
            style={{
              fontSize: 15,
              fontWeight: 500,
              color: colors.ink,
              border: `1.5px solid ${colors.ink}`,
              borderRadius: 999,
              padding: "8px 18px",
            }}
          >
            Find farms
          </span>
        </div>
      </div>

      {/* body */}
      <div style={{ position: "relative", flex: 1, overflow: "hidden" }}>{children}</div>
    </div>
  );
};
