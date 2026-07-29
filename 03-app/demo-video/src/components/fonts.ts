import { loadFont as loadNewsreader } from "@remotion/google-fonts/Newsreader";
import { loadFont as loadGeist } from "@remotion/google-fonts/Geist";

const newsreader = loadNewsreader("normal", {
  weights: ["400", "500", "600"],
  subsets: ["latin"],
});
const geist = loadGeist("normal", {
  weights: ["400", "500", "600", "700"],
  subsets: ["latin"],
});

// CSS custom properties consumed by theme.ts (fonts.serif / fonts.sans)
export const fontStyle: React.CSSProperties = {
  // @ts-expect-error custom properties
  "--ff-serif": `${newsreader.fontFamily}, Georgia, serif`,
  "--ff-sans": `${geist.fontFamily}, system-ui, sans-serif`,
};

export const fontsReady = () =>
  Promise.all([newsreader.waitUntilDone(), geist.waitUntilDone()]);
