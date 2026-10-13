import assert from "node:assert/strict";
import test from "node:test";
import {
  farmLocationLabel,
  farmProfileSummary,
  formatProductLabels,
  formatProductSummary,
  normalizeProductLabels,
  productLabelsForFarm,
} from "../app/lib/farm-presentation";

test("normalizes comma and semicolon fragments without changing their order or first spelling", () => {
  assert.deepEqual(
    normalizeProductLabels(
      "Grass-finished beef, pork; eggs",
      ["PORK", " eggs ; Whole   chicken", "Pastured Eggs"],
    ),
    ["Grass-finished beef", "pork", "eggs", "Whole chicken", "Pastured Eggs"],
  );
});

test("ignores empty fragments and whitespace-only product fields", () => {
  assert.deepEqual(normalizeProductLabels(" ; , ", ["", "  ", ";"]), []);
});

test("keeps descriptive commas inside parentheses with their product", () => {
  assert.deepEqual(
    normalizeProductLabels("Organic eggs (chicken, duck, goose), meats; honey"),
    ["Organic eggs (chicken, duck, goose)", "meats", "honey"],
  );
});

test("uses productsText order and adds non-duplicate structured products as a fallback", () => {
  assert.deepEqual(
    productLabelsForFarm({
      productsText: "Tomatoes; Okra, tomatoes",
      products: ["OKRA", "Cucumbers"],
    }),
    ["Tomatoes", "Okra", "Cucumbers"],
  );
});

test("formats product labels as natural English", () => {
  assert.equal(formatProductLabels([]), "");
  assert.equal(formatProductLabels(["eggs"]), "eggs");
  assert.equal(formatProductLabels(["eggs", "honey"]), "eggs and honey");
  assert.equal(formatProductLabels(["eggs", "honey", "milk"]), "eggs, honey, and milk");
});

test("caps long product prose while preserving a count of the remaining products", () => {
  assert.equal(
    formatProductSummary(["apples", "beans", "carrots", "dill", "eggs", "flowers", "garlic"]),
    "apples, beans, carrots, dill, and eggs, plus 2 more",
  );
});

test("profile summary uses normalized products and retains explicit missing-data language", () => {
  const base = {
    name: "Black Creek Farm",
    category: "Meat",
    city: "Picayune",
    state: "MS",
    productsText: "beef; pork, Beef",
    products: ["PORK", "eggs"],
    marketPresence: "On-farm sales",
  };

  assert.equal(
    farmProfileSummary(base),
    "Black Creek Farm is a meat producer near Picayune, MS. Known products include beef, pork, and eggs. Current sales information lists on-farm sales.",
  );
  assert.equal(
    farmProfileSummary({ ...base, productsText: "", products: [], marketPresence: "" }),
    "Black Creek Farm is a meat producer near Picayune, MS. Specific products have not been listed yet. A confirmed sales schedule is not listed yet.",
  );
});

test("profile summary does not invent a category or location when fields are missing", () => {
  assert.equal(
    farmProfileSummary({
      name: "Field Notes Farm",
      category: "",
      city: "",
      state: "",
      productsText: "Honey",
      products: [],
      marketPresence: "",
    }),
    "Field Notes Farm is an independent producer. Known products include Honey. A confirmed sales schedule is not listed yet.",
  );
});

test("profile summary uses the correct article for Urban Farm", () => {
  assert.equal(
    farmProfileSummary({
      name: "City Soil",
      category: "Urban Farm",
      city: "Chicago",
      state: "IL",
      productsText: "greens",
      products: [],
      marketPresence: "",
    }),
    "City Soil is an urban farm producer near Chicago, IL. Known products include greens. A confirmed sales schedule is not listed yet.",
  );
});

test("location label avoids stray punctuation when city or state is missing", () => {
  assert.equal(farmLocationLabel({ city: "", state: "MS", parish: "Pearl River" }), "MS · Pearl River");
  assert.equal(farmLocationLabel({ city: "Picayune", state: "", parish: "" }), "Picayune · Area not listed");
  assert.equal(farmLocationLabel({ city: "", state: "", parish: "" }), "Area not listed");
});
