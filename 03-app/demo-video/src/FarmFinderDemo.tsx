import React from "react";
import { AbsoluteFill, interpolate, Sequence, useCurrentFrame } from "remotion";
import { colors } from "./theme";
import { fontStyle } from "./components/fonts";
import { IntroScene } from "./scenes/IntroScene";
import { HeroScene } from "./scenes/HeroScene";
import { AskScene } from "./scenes/AskScene";
import { HarvestScene } from "./scenes/HarvestScene";
import { ExploreScene } from "./scenes/ExploreScene";
import { OutroScene } from "./scenes/OutroScene";

const XFADE = 12;

// Fades a scene in over the first XFADE frames and out over the last XFADE,
// so adjacent sequences crossfade when overlapped.
const Fade: React.FC<{ durationInFrames: number; children: React.ReactNode }> = ({
  durationInFrames,
  children,
}) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(
    frame,
    [0, XFADE, durationInFrames - XFADE, durationInFrames],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );
  return <AbsoluteFill style={{ opacity }}>{children}</AbsoluteFill>;
};

type Scene = { comp: React.FC; dur: number };

const scenes: Scene[] = [
  { comp: IntroScene, dur: 120 },
  { comp: HeroScene, dur: 210 },
  { comp: AskScene, dur: 348 },
  { comp: HarvestScene, dur: 192 },
  { comp: ExploreScene, dur: 486 },
  { comp: OutroScene, dur: 156 },
];

export const TOTAL_FRAMES = scenes.reduce((a, s) => a + s.dur, 0) - XFADE * (scenes.length - 1);

export const FarmFinderDemo: React.FC = () => {
  let from = 0;
  return (
    <AbsoluteFill style={{ ...fontStyle, background: colors.paper }}>
      {scenes.map((s, i) => {
        const start = from;
        from += s.dur - XFADE;
        const Comp = s.comp;
        return (
          <Sequence key={i} from={start} durationInFrames={s.dur} name={Comp.name}>
            <Fade durationInFrames={s.dur}>
              <Comp />
            </Fade>
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
