export type Farm = {
  id: string;
  name: string;
  category: string;
  region: string;
  parish: string;
  state: string;
  city: string;
  productsText: string;
  products: string[];
  marketPresence: string;
  website: string;
  hasWebsite: boolean;
  onlineStore: boolean;
  facebook: boolean;
  instagram: boolean;
  farmersMarket: boolean;
  csa: boolean;
  ships: boolean;
  onFarm: boolean;
  contact: string;
  notes: string;
  source: string;
  latitude: number;
  longitude: number;
  geoPrecision: string;
};

// Hue-separated so pins stay distinguishable at 6-9px on the map. Each category
// owns a distinct hue family; icon + text still dual-encode (visual-language spec)
// so red/green proximity stays colorblind-safe. Kept within the earthy brand range.
export const categoryColors: Record<string, string> = {
  Produce: "#3f7d54",        // leaf green
  "Urban Farm": "#94a13f",   // lime/olive — separated from Produce
  Meat: "#a5382b",           // deep red
  Mixed: "#d97a2b",          // orange — separated from Meat
  "Honey/Specialty": "#e0a81f", // amber
  Rice: "#8a7d58",           // muted khaki — separated from Honey
  Dairy: "#5b7d88",          // slate blue
  Seafood: "#2f8ca0",        // teal — separated from Dairy
  "Value-Added": "#7d5b93",  // violet
};

export function serviceLabels(farm: Farm) {
  return [
    farm.farmersMarket && "Market",
    farm.onFarm && "Farm pickup",
    farm.csa && "CSA",
    farm.ships && "Delivery",
    farm.onlineStore && "Order online",
  ].filter(Boolean) as string[];
}
