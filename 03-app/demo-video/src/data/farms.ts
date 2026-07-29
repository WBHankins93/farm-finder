// Real FarmFinder records, curated from 03-app/site/app/data/farms.json
export type Farm = {
  id: string;
  name: string;
  category: string;
  city: string;
  state: "LA" | "MS";
  parish: string;
  productsText: string;
  farmersMarket: boolean;
  onFarm: boolean;
  csa: boolean;
  ships: boolean;
  onlineStore: boolean;
  latitude: number;
  longitude: number;
  marketPresence: string;
  recordId: string;
  lastVerified: string;
  geoPrecision: string;
};

export const farms: Farm[] = [
  { id: "river-queen-greens", name: "River Queen Greens", category: "Produce", city: "New Orleans", state: "LA", parish: "Orleans", productsText: "Vegetables, fruit, eggs, mushrooms", farmersMarket: true, onFarm: true, csa: true, ships: false, onlineStore: true, latitude: 29.95465, longitude: -90.07507, marketPresence: "CSA, home delivery, pre-order", recordId: "FF-0029", lastVerified: "2026-07-15", geoPrecision: "city" },
  { id: "covey-rise-farm", name: "Covey Rise Farm", category: "Produce", city: "Husser", state: "LA", parish: "Tangipahoa", productsText: "30+ vegetable varieties year-round", farmersMarket: true, onFarm: true, csa: true, ships: false, onlineStore: false, latitude: 30.67944, longitude: -90.33722, marketPresence: "CSA, direct sales", recordId: "FF-0003", lastVerified: "2026-07-15", geoPrecision: "city" },
  { id: "jot-tittle-farms", name: "Jot & Tittle Farms", category: "Produce", city: "St. Amant", state: "LA", parish: "Ascension", productsText: "Organic vegetables, eggs", farmersMarket: false, onFarm: true, csa: true, ships: false, onlineStore: false, latitude: 30.22472, longitude: -90.86889, marketPresence: "CSA, home delivery, on-farm", recordId: "FF-0114", lastVerified: "2026-07-15", geoPrecision: "city" },
  { id: "fullness-farm", name: "Fullness Farm", category: "Mixed", city: "Baton Rouge", state: "LA", parish: "E. Baton Rouge", productsText: "Vegetables, fruit, honey", farmersMarket: true, onFarm: false, csa: true, ships: false, onlineStore: true, latitude: 30.44332, longitude: -91.18747, marketPresence: "CSA, Red Stick Farmers Market", recordId: "FF-0116", lastVerified: "2026-07-15", geoPrecision: "city" },
  { id: "berry-hill-farm", name: "Berry Hill Farm", category: "Mixed", city: "Loranger", state: "LA", parish: "Tangipahoa", productsText: "Produce, grass-fed beef, eggs, honey", farmersMarket: false, onFarm: false, csa: true, ships: true, onlineStore: true, latitude: 30.63583, longitude: -90.39806, marketPresence: "Online, home delivery NOLA + Northlake, CSA", recordId: "FF-0139", lastVerified: "2026-07-15", geoPrecision: "city" },
  { id: "luckett-farms", name: "Luckett Farms", category: "Mixed", city: "Pride", state: "LA", parish: "E. Baton Rouge", productsText: "Vegetables, fruit, honey", farmersMarket: false, onFarm: true, csa: true, ships: false, onlineStore: true, latitude: 30.69389, longitude: -90.97806, marketPresence: "CSA, home delivery, roadside stand, U-pick", recordId: "FF-0120", lastVerified: "2026-07-15", geoPrecision: "city" },
  { id: "maranatha-farm", name: "Maranatha Farm", category: "Produce", city: "Slaughter", state: "LA", parish: "E. Feliciana", productsText: "Vegetables (CSA)", farmersMarket: false, onFarm: true, csa: true, ships: false, onlineStore: false, latitude: 30.717406, longitude: -91.141496, marketPresence: "CSA program", recordId: "FF-0271", lastVerified: "2026-07-15", geoPrecision: "city" },
  { id: "loup-farms", name: "Loup Farms", category: "Produce", city: "New Roads", state: "LA", parish: "Pointe Coupee", productsText: "Vegetables", farmersMarket: false, onFarm: true, csa: true, ships: false, onlineStore: false, latitude: 30.70157, longitude: -91.43622, marketPresence: "CSA, Saturday farm stand", recordId: "FF-0067", lastVerified: "2026-07-15", geoPrecision: "city" },
  { id: "2-guys-honey", name: "2 Guys Honey", category: "Honey/Specialty", city: "Hessmer", state: "LA", parish: "Avoyelles", productsText: "Honey", farmersMarket: false, onFarm: false, csa: false, ships: true, onlineStore: true, latitude: 31.05963, longitude: -92.12124, marketPresence: "Online, home delivery, local grocery", recordId: "FF-0224", lastVerified: "2026-07-15", geoPrecision: "city" },
  { id: "4sisters-rice", name: "4Sisters Rice", category: "Rice", city: "Mer Rouge", state: "LA", parish: "Morehouse", productsText: "Organic rice", farmersMarket: false, onFarm: false, csa: false, ships: true, onlineStore: true, latitude: 32.77513, longitude: -91.79263, marketPresence: "Online, delivery, national grocers", recordId: "FF-0193", lastVerified: "2026-07-15", geoPrecision: "city" },
  { id: "anna-marie-seafood", name: "Anna Marie Seafood", category: "Seafood", city: "Montegut", state: "LA", parish: "Terrebonne", productsText: "Wild-caught Gulf seafood", farmersMarket: true, onFarm: false, csa: false, ships: false, onlineStore: false, latitude: 29.47, longitude: -90.71, marketPresence: "Direct sales, farmers markets", recordId: "FF-0054", lastVerified: "2026-07-15", geoPrecision: "city" },
  { id: "3r-cattle-company", name: "3R Cattle Company", category: "Meat", city: "Gulfport", state: "MS", parish: "Harrison", productsText: "Grass-fed and grain-fed beef", farmersMarket: false, onFarm: true, csa: false, ships: false, onlineStore: false, latitude: 30.36742, longitude: -89.09282, marketPresence: "Direct sales, 1500 acres", recordId: "FF-0084", lastVerified: "2026-07-15", geoPrecision: "city" },
  { id: "5d-natural-farm", name: "5D Natural Farm", category: "Mixed", city: "Raymond", state: "MS", parish: "Hinds", productsText: "Pasture-raised poultry, eggs, peppers, okra, tomatoes", farmersMarket: true, onFarm: false, csa: false, ships: false, onlineStore: false, latitude: 32.25787, longitude: -90.42901, marketPresence: "Community farmers market vendor", recordId: "FF-0008", lastVerified: "2026-07-15", geoPrecision: "city" },
  { id: "blue-courage-farms", name: "Blue Courage Farms", category: "Produce", city: "Jackson", state: "MS", parish: "Hinds", productsText: "Diverse fresh produce, delivered", farmersMarket: false, onFarm: false, csa: false, ships: true, onlineStore: false, latitude: 32.29876, longitude: -90.18481, marketPresence: "Delivery service", recordId: "FF-0277", lastVerified: "2026-07-15", geoPrecision: "region" },
  { id: "banks-rice", name: "Banks Family Rice", category: "Rice", city: "Tupelo", state: "MS", parish: "Lee", productsText: "Rice", farmersMarket: false, onFarm: true, csa: false, ships: false, onlineStore: false, latitude: 34.25761, longitude: -88.70339, marketPresence: "Direct sales", recordId: "FF-0296", lastVerified: "2026-07-15", geoPrecision: "region" },
];

export function serviceLabels(f: Farm): string[] {
  return [
    f.farmersMarket && "Market",
    f.onFarm && "Farm pickup",
    f.csa && "CSA",
    f.ships && "Delivery",
    f.onlineStore && "Order online",
  ].filter(Boolean) as string[];
}

// Bounding box for the launch coverage (LA + MS), used to project lat/long
// into the atlas map panel.
export const bounds = {
  minLat: 29.2,
  maxLat: 34.9,
  minLng: -94.1,
  maxLng: -88.2,
};

export function project(
  lat: number,
  lng: number,
  w: number,
  h: number,
  pad = 0.08
): { x: number; y: number } {
  const px = (lng - bounds.minLng) / (bounds.maxLng - bounds.minLng);
  const py = 1 - (lat - bounds.minLat) / (bounds.maxLat - bounds.minLat);
  const padX = w * pad;
  const padY = h * pad;
  return {
    x: padX + px * (w - padX * 2),
    y: padY + py * (h - padY * 2),
  };
}
