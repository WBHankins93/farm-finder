import type { ReactNode, SVGProps } from "react";

/**
 * Field-marks — FarmFinder's category + ways-to-buy icon set.
 *
 * Single-weight line glyphs drawn on a 24px grid, stroked in `currentColor`
 * so one definition works on paper, cream, or green and inherits the category
 * color where it's placed. No icon-library dependency, no fills, no gradients —
 * see docs/design/visual-language-research-and-plan.md (§2.2).
 */

export type MarkName =
  | "leaf"
  | "fruit"
  | "egg"
  | "beef"
  | "pork"
  | "poultry"
  | "honey"
  | "dairy"
  | "seafood"
  | "rice"
  | "flowers"
  | "mushrooms"
  | "basket"
  | "urban"
  | "jar"
  | "market"
  | "farm"
  | "csa"
  | "ships"
  | "online";

const flowerPetal = "M12 11C9.6 8.3 10.1 4.8 12 3.2 13.9 4.8 14.4 8.3 12 11Z";

const MARKS: Record<MarkName, ReactNode> = {
  leaf: (
    <>
      <path d="M20 4C11 4 5 9 5 15c0 2 1.2 3.8 3 3.8 7 0 12-6.4 12-14.8Z" />
      <path d="M8 18.2C11 13 15 9 18 7" />
    </>
  ),
  fruit: (
    <>
      <path d="M12 9c-1.4-1.4-3.6-1.7-5.2-.6C4.8 9.7 4.4 13 5.6 16c1 2.4 2.9 4 4.4 4 .8 0 1.2-.4 2-.4s1.2.4 2 .4c1.5 0 3.4-1.6 4.4-4 1.2-3 .8-6.3-1.2-7.6-1.6-1.1-3.8-.8-5.2.6Z" />
      <path d="M12 9V5.6" />
      <path d="M12 5.8c0-1.6 1.3-2.6 2.9-2.6C14.9 4.8 13.6 5.8 12 5.8Z" />
    </>
  ),
  egg: <path d="M12 4c3.3 0 6 4.6 6 8.6S15.3 20 12 20s-6-3-6-7.4S8.7 4 12 4Z" />,
  beef: (
    <>
      <path d="M5.5 8.2c2-2.6 6-3.7 10-2.7 3.1.8 4.9 2.8 4.7 5.2-.2 3.1-3.1 5.6-7.2 6.2-4.7.7-8.6-.7-9.6-3.8-.5-1.6 0-3.3 2.1-4.9Z" />
      <circle cx="8" cy="11.2" r="1.7" />
    </>
  ),
  pork: (
    <>
      <path d="M5.4 6.6 6.8 4M18.6 6.6 17.2 4" />
      <path d="M5 11c0-3 3-5 7-5s7 2 7 5c0 4-3 7-7 7s-7-3-7-7Z" />
      <path d="M8.8 12.6c0-1.4 1.4-2.4 3.2-2.4s3.2 1 3.2 2.4-1.4 2.4-3.2 2.4-3.2-1-3.2-2.4Z" />
      <path d="M10.9 12.6v.01M13.1 12.6v.01" />
    </>
  ),
  poultry: (
    <>
      <path d="M4.5 13.2c-1.4-.4-2.3.3-2.3.3" />
      <path d="M6.2 19c-2.2 0-3.7-1.8-3.7-4.2C2.5 11.5 5.4 9 9 9c3.4 0 5.7 2.2 5.7 5.1" />
      <circle cx="16.4" cy="8.4" r="2.3" />
      <path d="M15.7 6.3c.4-1 1.9-1 2.3.1" />
      <path d="M18.6 8.6 21 8M16.6 10.6l.4 1.6" />
      <path d="M8.8 19v2M12.6 19v2" />
    </>
  ),
  honey: (
    <>
      <path d="M8 4h8l4 8-4 8H8l-4-8 4-8Z" />
      <path d="M12 9c1.6 2.1 2.6 3.4 2.6 4.6a2.6 2.6 0 0 1-5.2 0C9.4 12.4 10.4 11.1 12 9Z" />
    </>
  ),
  dairy: (
    <>
      <path d="M9 4h6" />
      <path d="M9.5 4v2.6L8 9.2V19a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V9.2L14.5 6.6V4" />
      <path d="M8 13h8" />
    </>
  ),
  seafood: (
    <>
      <path d="M20 12c-3-4-8-5-12-3-2 1-3.6 2.3-4.6 3 1 .7 2.6 2 4.6 3 4 2 9 1 12-3Z" />
      <path d="M4 12 1.6 9.4v5.2Z" />
      <path d="M16.4 10.6v.01" />
    </>
  ),
  rice: (
    <>
      <path d="M12 21V8" />
      <path d="M12 8c0-2 1.5-3.6 3.6-3.6C15.6 6.5 14.1 8 12 8ZM12 8c0-2-1.5-3.6-3.6-3.6C8.4 6.5 9.9 8 12 8Z" />
      <path d="M12 12c0-2 1.5-3.6 3.6-3.6C15.6 10.5 14.1 12 12 12ZM12 12c0-2-1.5-3.6-3.6-3.6C8.4 10.5 9.9 12 12 12Z" />
    </>
  ),
  flowers: (
    <>
      <path d={flowerPetal} />
      <path d={flowerPetal} transform="rotate(72 12 11)" />
      <path d={flowerPetal} transform="rotate(144 12 11)" />
      <path d={flowerPetal} transform="rotate(216 12 11)" />
      <path d={flowerPetal} transform="rotate(288 12 11)" />
      <circle cx="12" cy="11" r="1.7" />
    </>
  ),
  mushrooms: (
    <>
      <path d="M4 11c0-4 3.6-7 8-7s8 3 8 7c0 1-.9 1.6-2.1 1.6H6.1C4.9 12.6 4 12 4 11Z" />
      <path d="M9.6 12.6v3.9c0 1.7 1 2.5 2.4 2.5s2.4-.8 2.4-2.5v-3.9" />
      <path d="M9 8.4v.01M14 9.4v.01M12 6.9v.01" />
    </>
  ),
  basket: (
    <>
      <path d="M4 9h16l-1.5 9.6a1 1 0 0 1-1 .8H6.5a1 1 0 0 1-1-.8L4 9Z" />
      <path d="M8 9c0-2.2 1.4-3.4 3-3.4M12.4 9c.4-2.6 2.4-3.6 4-3" />
      <path d="M8.5 12v4.5M12 12v4.5M15.5 12v4.5" />
    </>
  ),
  urban: (
    <>
      <path d="M5 20V8h11v12" />
      <path d="M4 20h16" />
      <path d="M9 20v-4h3v4" />
      <path d="M13 11h1M13 14.5h1" />
      <path d="M12.6 8c0-2 1.7-3.3 3.3-3.3-.2 1.9-1.5 3.1-3.3 3.3ZM12.6 8V5.4" />
    </>
  ),
  jar: (
    <>
      <path d="M8 4h8v2l-1 1v1.2c1.2.7 2 1.9 2 3.3V19a1 1 0 0 1-1 1H8a1 1 0 0 1-1-1v-6.5c0-1.4.8-2.6 2-3.3V7L8 6V4Z" />
      <path d="M7.4 12.2h9.2" />
    </>
  ),
  market: (
    <>
      <path d="M3 9.5 5 4.5h14l2 5" />
      <path d="M4.5 9.5V19.5h15V9.5" />
      <path d="M3 9.5h18" />
      <path d="M9.5 19.5V13h5v6.5" />
    </>
  ),
  farm: (
    <>
      <path d="M4 20V9l8-5 8 5v11" />
      <path d="M3.5 20h17" />
      <path d="M9.5 20v-5.5h5V20" />
      <path d="M9.5 14.5h5" />
    </>
  ),
  csa: (
    <>
      <path d="M3 7.5 12 4l9 3.5-9 3.5-9-3.5Z" />
      <path d="M3 7.6V16l9 4 9-4V7.6" />
      <path d="M12 11.2V20" />
    </>
  ),
  ships: (
    <>
      <path d="M2 7h11v9H2z" />
      <path d="M13 10h4l3 3v3h-7z" />
      <circle cx="7" cy="17.5" r="1.6" />
      <circle cx="17" cy="17.5" r="1.6" />
    </>
  ),
  online: (
    <>
      <path d="M6 8h12l-1 11a1 1 0 0 1-1 .9H8a1 1 0 0 1-1-.9L6 8Z" />
      <path d="M9 8V6a3 3 0 0 1 6 0v2" />
    </>
  ),
};

/** Broad data category (`farm.category`) → mark. */
const CATEGORY_MARK: Record<string, MarkName> = {
  Produce: "leaf",
  Mixed: "basket",
  Meat: "beef",
  "Honey/Specialty": "honey",
  Dairy: "dairy",
  Seafood: "seafood",
  Rice: "rice",
  "Urban Farm": "urban",
  "Value-Added": "jar",
};

/** Harvest-index / product-filter id → mark. */
const PRODUCT_MARK: Record<string, MarkName> = {
  vegetables: "leaf",
  fruit: "fruit",
  eggs: "egg",
  beef: "beef",
  pork: "pork",
  poultry: "poultry",
  honey: "honey",
  dairy: "dairy",
  seafood: "seafood",
  rice: "rice",
  flowers: "flowers",
  mushrooms: "mushrooms",
};

/** Ways-to-buy service key → mark. */
const SERVICE_MARK: Record<string, MarkName> = {
  farmersMarket: "market",
  onFarm: "farm",
  csa: "csa",
  ships: "ships",
  onlineStore: "online",
};

export function markForCategory(category: string): MarkName {
  return CATEGORY_MARK[category] ?? "leaf";
}

export function markForProduct(productId: string): MarkName | null {
  return PRODUCT_MARK[productId] ?? null;
}

export function markForService(serviceKey: string): MarkName | null {
  return SERVICE_MARK[serviceKey] ?? null;
}

export function Mark({
  name,
  className = "mark",
  ...rest
}: {
  name: MarkName;
} & SVGProps<SVGSVGElement>) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      {...rest}
    >
      {MARKS[name]}
    </svg>
  );
}
