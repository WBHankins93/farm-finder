import React from "react";
import { Composition } from "remotion";
import { FarmFinderDemo, TOTAL_FRAMES } from "./FarmFinderDemo";

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="FarmFinderDemo"
      component={FarmFinderDemo}
      durationInFrames={TOTAL_FRAMES}
      fps={30}
      width={1920}
      height={1080}
    />
  );
};
