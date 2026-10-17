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

export function serviceLabels(farm: Farm) {
  return [
    farm.farmersMarket && "Market",
    farm.onFarm && "Farm pickup",
    farm.csa && "CSA",
    farm.ships && "Delivery",
    farm.onlineStore && "Order online",
  ].filter(Boolean) as string[];
}
