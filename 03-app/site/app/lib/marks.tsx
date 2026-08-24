import type { ComponentType } from "react";
import type { IconProps } from "@phosphor-icons/react";
import {
  BasketIcon,
  BirdIcon,
  BuildingsIcon,
  CheeseIcon,
  CherriesIcon,
  CookingPotIcon,
  CowIcon,
  EggIcon,
  FishIcon,
  FlowerTulipIcon,
  GrainsIcon,
  HexagonIcon,
  PackageIcon,
  PiggyBankIcon,
  PlantIcon,
  ShoppingBagOpenIcon,
  StorefrontIcon,
  TractorIcon,
  TruckIcon,
} from "@phosphor-icons/react/ssr";

/**
 * FarmFinder's shared category and service vocabulary.
 *
 * The icon geometry comes from the packaged Phosphor icon set. Keeping the
 * mapping here gives every surface the same metaphor, weight, and accessible
 * behavior without maintaining SVG paths in the application.
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

const MARKS: Record<MarkName, ComponentType<IconProps>> = {
  leaf: PlantIcon,
  fruit: CherriesIcon,
  egg: EggIcon,
  beef: CowIcon,
  pork: PiggyBankIcon,
  poultry: BirdIcon,
  honey: HexagonIcon,
  dairy: CheeseIcon,
  seafood: FishIcon,
  rice: GrainsIcon,
  flowers: FlowerTulipIcon,
  mushrooms: PlantIcon,
  basket: BasketIcon,
  urban: BuildingsIcon,
  jar: CookingPotIcon,
  market: StorefrontIcon,
  farm: TractorIcon,
  csa: PackageIcon,
  ships: TruckIcon,
  online: ShoppingBagOpenIcon,
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
} & IconProps) {
  const Icon = MARKS[name];
  return (
    <Icon
      className={className}
      weight="duotone"
      aria-hidden="true"
      focusable="false"
      {...rest}
    />
  );
}
