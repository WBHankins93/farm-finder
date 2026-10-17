import type { ServiceKey } from "./discovery-contract";

export type ProductGuide = {
  id: string;
  label: string;
  shortLabel: string;
  description: string;
  season: string;
  color: string;
};

export const categories = [
  "Produce",
  "Mixed",
  "Meat",
  "Honey/Specialty",
  "Dairy",
  "Seafood",
  "Rice",
  "Urban Farm",
  "Value-Added",
];

export const serviceFilters: { key: ServiceKey; label: string; shortLabel: string }[] = [
  { key: "farmersMarket", label: "At farmers markets", shortLabel: "Markets" },
  { key: "onFarm", label: "On-farm sales", shortLabel: "Farm pickup" },
  { key: "csa", label: "CSA shares", shortLabel: "CSA" },
  { key: "ships", label: "Delivery or shipping", shortLabel: "Delivery" },
  { key: "onlineStore", label: "Order online", shortLabel: "Order online" },
];

export const productGuides: ProductGuide[] = [
  { id: "vegetables", label: "Vegetables & greens", shortLabel: "Vegetables", description: "Everyday produce, leafy greens, tomatoes, squash, okra, peas, herbs, and microgreens.", season: "Cool-season greens and roots give way to tomatoes, peppers, okra, squash, and field peas as warmer weather arrives.", color: "#55734d" },
  { id: "fruit", label: "Fruit, berries & citrus", shortLabel: "Fruit & citrus", description: "Berries, peaches, melons, orchard fruit, and regional citrus.", season: "Berries and peaches arrive from spring into summer; melons peak in heat; citrus follows in fall and winter.", color: "#b65f39" },
  { id: "eggs", label: "Eggs", shortLabel: "Eggs", description: "Chicken, duck, and other farm eggs from mixed farms, homesteads, and poultry producers.", season: "Eggs may be available year-round, but supply changes with heat, daylight, flock size, and farm schedules.", color: "#c08a2e" },
  { id: "beef", label: "Beef & cattle", shortLabel: "Beef", description: "Grass-fed, grass-finished, grain-finished, and pasture-raised beef sold by the cut or share.", season: "Frozen cuts can be available year-round; bulk beef and processor dates often require reservations.", color: "#8b3e30" },
  { id: "pork", label: "Pork", shortLabel: "Pork", description: "Pastured pork, heritage hogs, sausage, and whole- or half-animal shares.", season: "Cuts may be stocked year-round, while bulk orders follow processing schedules.", color: "#a95246" },
  { id: "poultry", label: "Chicken & poultry", shortLabel: "Poultry", description: "Pastured chicken, turkey, duck, and other poultry sold fresh, frozen, or by pre-order.", season: "Many small flocks process on set dates, so reservations and pickup windows matter.", color: "#9a6936" },
  { id: "honey", label: "Honey & bee products", shortLabel: "Honey", description: "Raw honey, comb honey, beeswax goods, and apiary products.", season: "Honey stores well, but varietals and fresh harvests follow local bloom cycles.", color: "#bd8628" },
  { id: "dairy", label: "Milk, cheese & dairy", shortLabel: "Dairy", description: "Cow and goat milk, artisan cheeses, creamery goods, and farmstead dairy products.", season: "Availability depends on herd cycles, licensing, and production schedules.", color: "#557a78" },
  { id: "seafood", label: "Seafood & crawfish", shortLabel: "Seafood", description: "Crawfish, shrimp, crab, fish, oysters, and direct-from-the-water products.", season: "Catch windows shift with weather, water conditions, regulation, and species.", color: "#39738c" },
  { id: "rice", label: "Rice & grains", shortLabel: "Rice", description: "Farm-grown rice, specialty varieties, milled grains, and pantry staples.", season: "Milled grain is shelf-stable beyond harvest; specialty varieties may sell out between crops.", color: "#99835c" },
  { id: "flowers", label: "Flowers & nursery", shortLabel: "Flowers", description: "Cut flowers, edible flowers, native plants, seedlings, and nursery goods.", season: "Flower and plant availability is highly seasonal; spring and fall often offer the widest selection.", color: "#7d5b7f" },
  { id: "mushrooms", label: "Mushrooms", shortLabel: "Mushrooms", description: "Fresh culinary mushrooms, specialty varieties, grow kits, and fungi-based products.", season: "Cultivated mushrooms may grow year-round, but weekly harvests change quickly.", color: "#6f665c" },
];
