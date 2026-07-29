// FarmFinder design tokens — mirrored from
// 03-app/site/docs/design/web-design-system.md
export const colors = {
  paper: "#eef0e6", // weathered seed paper — page canvas
  paperDeep: "#d9ddce", // pressed cane fiber — selected/secondary surfaces
  cream: "#fbfcf6", // oyster-shell white — readable records and controls
  ink: "#17251d", // wet field ink — primary type and rules
  green: "#173f2c", // chlorophyll ink — deep sections, active state
  green2: "#4d735b", // leaf ledger — produce, secondary state
  river: "#557681", // river slate — map / water context
  rust: "#c65e36", // persimmon stamp — focus, selection, critical action
  brass: "#a28745", // dry cane — honey, counts, subtle warmth
  rule: "#bcc5b8", // pressed-paper edge — dividers, control boundaries
} as const;

export const categoryColors: Record<string, string> = {
  Produce: "#4d735b",
  Mixed: "#c65e36",
  Meat: "#863f32",
  "Honey/Specialty": "#a28745",
  Dairy: "#557681",
  Seafood: "#397386",
  Rice: "#8d815c",
  "Urban Farm": "#68743f",
  "Value-Added": "#775d7b",
};

export const fonts = {
  // display / editorial
  serif: "var(--ff-serif)",
  // interface / data
  sans: "var(--ff-sans)",
};
