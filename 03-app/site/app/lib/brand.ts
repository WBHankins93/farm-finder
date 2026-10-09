/**
 * The Market Stand palette, as data.
 *
 * `globals.css` is still where the browser reads these values from — this
 * module does not generate the CSS, because a build step that rewrites the
 * stylesheet is a worse trade than a test that proves the two agree. What this
 * gives us is a palette that can be *read*: by the brand page, by future
 * React Native primitives, and by `tests/brand.test.ts`, which fails if a
 * value here and a value in `:root` drift apart, or if a token meant for text
 * stops clearing 4.5:1 on the surfaces it is used on.
 *
 * Adding a colour: add it here with its role and `onSurfaces`, add the same
 * value to `:root`, and the test will tell you if you got it wrong.
 * Reasoning behind the palette is in `docs/design/brand.md`.
 */

export type BrandToken = {
  /** CSS custom property name, without the leading `--`. */
  name: string;
  value: string;
  /** Plain-language name, for the brand page and for design conversations. */
  label: string;
  role: string;
  /**
   * Surfaces this colour is allowed to carry small text on. Each is checked at
   * 4.5:1. An empty list means the token is a surface or a large-format /
   * decorative colour and carries no small-text obligation.
   */
  onSurfaces: string[];
};

export type BrandGroup = { title: string; note: string; tokens: BrandToken[] };

export const brandPalette: BrandGroup[] = [
  {
    title: "Surfaces",
    note: "Warm cream leads. The page is paper, cards are a shade brighter, kraft carries secondary bands.",
    tokens: [
      { name: "paper", value: "#fbf6ec", label: "Cream", role: "Page canvas", onSurfaces: [] },
      { name: "paper-deep", value: "#f3e9d4", label: "Kraft", role: "Secondary surfaces and bands", onSurfaces: [] },
      { name: "cream", value: "#fffdf7", label: "Oyster", role: "Cards, controls, sheets", onSurfaces: [] },
      { name: "sky", value: "#cfe3ea", label: "Sky", role: "Map water, quiet information", onSurfaces: [] },
    ],
  },
  {
    title: "Ink",
    note: "Soil rather than near-black: a warm text colour keeps the page from going cold under the cream.",
    tokens: [
      { name: "ink", value: "#2b211c", label: "Soil", role: "Body text, dark bands", onSurfaces: ["paper", "cream", "paper-deep", "sun"] },
      { name: "muted", value: "#6b5e54", label: "Muted soil", role: "Supporting text, captions", onSurfaces: ["paper", "cream", "paper-deep"] },
    ],
  },
  {
    title: "Brand",
    note:
      "Tomato is the brand; rust is the same idea at a contrast a label can survive. They are two tokens on purpose — " +
      "the brand tomato is 3.97:1 on cream, which is fine for a logo and wrong for 11px type.",
    tokens: [
      { name: "tomato", value: "#d9482b", label: "Tomato", role: "Logo, fills, large display type", onSurfaces: [] },
      { name: "rust", value: "#c0392b", label: "Rust", role: "Links, labels, small accents, primary buttons", onSurfaces: ["paper", "cream", "paper-deep"] },
      { name: "green", value: "#1f5136", label: "Field green", role: "Structure, trust, active state", onSurfaces: ["paper", "cream", "paper-deep"] },
      { name: "sun", value: "#f4c95d", label: "Butter", role: "Distance pills, step markers, highlights", onSurfaces: [] },
    ],
  },
  {
    title: "Secondary",
    note: "Category and data colours. Each one still has to be readable as text where it is used as text.",
    tokens: [
      { name: "green-2", value: "#3e6b45", label: "Leaf", role: "Produce, secondary state", onSurfaces: ["paper", "cream"] },
      { name: "brass", value: "#8a6a1c", label: "Brass", role: "Honey, counts, warm secondary", onSurfaces: ["paper", "cream"] },
      { name: "river", value: "#3f6b78", label: "River", role: "Water, dairy, seafood context", onSurfaces: ["paper", "cream"] },
      { name: "sun-deep", value: "#e8b43c", label: "Deep butter", role: "Hover and pressed states for butter", onSurfaces: [] },
      { name: "rule", value: "#e2d6bd", label: "Rule", role: "Dividers and control edges", onSurfaces: [] },
    ],
  },
];

export const brandTokens: BrandToken[] = brandPalette.flatMap((group) => group.tokens);

export function brandToken(name: string): BrandToken | undefined {
  return brandTokens.find((token) => token.name === name);
}

/** Corner radii. Market stands are built from crates and awnings, not hairlines. */
export const brandRadii = [
  { name: "radius-sm", value: "10px", role: "Chips, tiles, small controls" },
  { name: "radius", value: "14px", role: "Cards, sheets, panels" },
  { name: "radius-lg", value: "20px", role: "Hero photograph, large media" },
];

/** Type roles. Both faces are loaded in `app/layout.tsx`. */
export const brandType = [
  { role: "Display", face: "Plus Jakarta Sans", usage: "Headlines, farm names, counts", sample: "Find the farms" },
  { role: "Interface", face: "DM Sans", usage: "Body copy, controls, labels, data", sample: "496 farms within 50 miles" },
];

/** Relative luminance, per WCAG 2.x. */
export function luminance(hex: string): number {
  const value = hex.replace("#", "");
  const channels = [0, 2, 4].map((offset) => parseInt(value.slice(offset, offset + 2), 16) / 255);
  const linear = channels.map((channel) => (channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4));
  return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2];
}

/** Contrast ratio between two hex colours, rounded to two places. */
export function contrastRatio(a: string, b: string): number {
  const [high, low] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return Math.round(((high + 0.05) / (low + 0.05)) * 100) / 100;
}
