import assert from "node:assert/strict";
import test from "node:test";
import { choiceCaption, choosePlace, fallbackPlaceQueries, normalizePlace, normalizePlaceQuery, placeMatches, placeRank, trailingStateCode } from "../app/lib/place-match";
import { searchPlaces } from "../app/lib/discovery-server";

test("spellings people actually type all reach the same place", async () => {
  // Before this, only the exact "Madison, WI" resolved; the hero sent every
  // other spelling to a page that silently did nothing.
  for (const typed of ["Madison, WI", "madison wi", "Madison,WI", "MADISON WI", "madison wisconsin", "  madison ,  wi "]) {
    const result = await searchPlaces(typed, 8);
    assert.equal(result.items[0]?.label, "Madison, WI", `"${typed}" should resolve to Madison, WI`);
  }
});

test("a trailing state name is read as its postal code", () => {
  assert.equal(normalizePlaceQuery("madison wisconsin"), "madison wi");
  assert.equal(normalizePlaceQuery("charleston west virginia"), "charleston wv");
  assert.equal(normalizePlaceQuery("charleston south carolina"), "charleston sc");
  assert.equal(normalizePlaceQuery("kansas city missouri"), "kansas city mo");
});

test("a state name that is really a city is left alone", () => {
  // "washington" on its own is a city search; converting it to "wa" would send
  // someone looking for Washington, NC to every place in Washington state.
  assert.equal(normalizePlaceQuery("washington"), "washington");
  // A leading state name is part of a city name, not a qualifier.
  assert.equal(normalizePlaceQuery("kansas city"), "kansas city");
  assert.equal(normalizePlaceQuery("new york"), "new york");
});

test("west virginia is not misread as virginia", () => {
  assert.equal(normalizePlaceQuery("wheeling west virginia"), "wheeling wv");
  assert.equal(trailingStateCode("wheeling wv"), "wv");
  assert.equal(trailingStateCode("wheeling"), null);
});

test("punctuation and diacritics do not decide a match", () => {
  assert.equal(normalizePlace("Coeur d'Alene, ID"), "coeur d alene id");
  assert.equal(normalizePlace("Española, NM"), "espanola nm");
  assert.ok(placeMatches(normalizePlace("Española, NM"), normalizePlaceQuery("espanola")));
});

test("every typed word must begin a distinct word of the place", () => {
  const label = normalizePlace("San Jose, CA");
  assert.ok(placeMatches(label, "san jo"), "a half-typed word still suggests while typing");
  assert.ok(placeMatches(label, "jose ca"), "word order is not enforced");
  assert.ok(!placeMatches(label, "san san"), "one label word cannot satisfy two query words");
  assert.ok(!placeMatches(label, "san diego"), "every word has to match something");
  assert.ok(!placeMatches(label, ""), "an empty query matches nothing");
});

test("a whole-word match outranks a mid-word one", () => {
  // Typing "madison" should lead with Madison, not Madisonville.
  const query = normalizePlaceQuery("madison");
  assert.equal(placeRank("madison", query), 0);
  assert.equal(placeRank(normalizePlace("Madison, WI"), query), 1);
  assert.equal(placeRank(normalizePlace("Madisonville, KY"), query), 2);
  assert.equal(placeRank(normalizePlace("North Madison, IN"), query), 3);
});

test("an ambiguous city lists every state that has one, most farms first", async () => {
  const result = await searchPlaces("springfield", 8);
  assert.ok(result.items.length > 1, "Springfield exists in several states");
  const states = new Set(result.items.map((item) => item.state));
  assert.equal(states.size, result.items.length, "each suggestion is a different state");
  const counts = result.items.map((item) => item.farmCount);
  assert.deepEqual(counts, [...counts].sort((a, b) => b - a));
});

test("nonsense and near-empty queries return nothing rather than everything", async () => {
  assert.equal((await searchPlaces("zzqxv", 8)).items.length, 0);
  assert.equal((await searchPlaces("m", 8)).items.length, 0, "one character is too little to suggest from");
  assert.equal((await searchPlaces(" , ", 8)).items.length, 0, "punctuation alone is not a query");
});

const place = (label: string, farmCount: number) => ({ label, state: label.slice(-2), farmCount });

test("a submitted search goes straight to a city only when the visitor named one", () => {
  // One match, an exact label, a spelled-out state, or a dominant match: go.
  assert.equal(choosePlace("madison wi", [place("Madison, WI", 23)]).kind, "go");
  assert.equal(choosePlace("Madison, WI", [place("Madison, WI", 23), place("Madisonville, KY", 5)]).kind, "go");
  assert.equal(choosePlace("madison wisconsin", [place("Madison, WI", 23), place("Madison, NC", 12)]).kind, "go");
  const orleans = choosePlace("new orleans", [place("New Orleans, LA", 65), place("New Orleans, NY", 1)]);
  assert.equal(orleans.kind, "go");
  assert.equal(orleans.kind === "go" && orleans.place.label, "New Orleans, LA");
});

test("an ambiguous city asks instead of guessing a state", () => {
  // Guessing sends someone hundreds of miles from where they meant.
  const madison = choosePlace("madison", [place("Madison, WI", 23), place("Madison, NC", 12), place("Madison, MN", 7)]);
  assert.equal(madison.kind, "choose");
  assert.equal(madison.kind === "choose" && madison.places.length, 3);
  assert.equal(choosePlace("springfield", [place("Springfield, MA", 29), place("Springfield, KY", 20)]).kind, "choose");
});

test("a state the visitor typed beats farm count, even a dominant one", () => {
  // Wisconsin has more than four times the farms, which on its own would be
  // enough to skip the question. The visitor said Mississippi.
  const decision = choosePlace("madison ms", [place("Madison, WI", 40), place("Madison, MS", 7)]);
  assert.equal(decision.kind, "go");
  assert.equal(decision.kind === "go" && decision.place.label, "Madison, MS");
});

test("a state name that ends a real city's name is not read as the state", () => {
  // "Mount Washington" is a city in Kentucky. Reading its last word as "WA"
  // sent the visitor straight to Mount Vernon, WA — the one Washington-state
  // match — and "Port Washington" offered only Washington-state ports.
  const mount = choosePlace("mount washington", [place("Mount Washington, KY", 4), place("Mount Washington, MA", 1), place("Mount Vernon, WA", 78)]);
  assert.equal(mount.kind === "go" && mount.place.label, "Mount Washington, KY");
  const port = choosePlace("Port Washington", [
    place("Port Washington, WI", 4), place("Port Washington, OH", 2), place("Port Washington, NY", 1),
    place("Port Angeles, WA", 38), place("Port Townsend, WA", 34),
  ]);
  assert.equal(port.kind, "choose");
  assert.deepEqual(port.kind === "choose" && port.places.map((item) => item.label), ["Port Washington, WI", "Port Washington, OH", "Port Washington, NY"]);
  // A state name no candidate city carries is still read as the state.
  const spokane = choosePlace("spokane washington", [place("Spokane, WA", 9), place("Spokane, MO", 1)]);
  assert.equal(spokane.kind === "go" && spokane.place.label, "Spokane, WA");
});

test("port washington offers only Port Washingtons, through the real index", async () => {
  const typed = "port washington";
  const decision = choosePlace(typed, (await searchPlaces(typed, 8)).items);
  const labels = decision.kind === "go" ? [decision.place.label] : decision.kind === "choose" ? decision.places.map((item) => item.label) : [];
  assert.ok(labels.length > 0 && labels.every((label) => label.startsWith("Port Washington, ")), `got ${labels.join(", ")}`);
});

test("the pick-one caption counts states, not places", () => {
  // "New York" matches four places in two states. Saying "is in 4 states"
  // was simply false, and the list under it showed only NY and MN.
  const newYork = [place("New York, NY", 43), place("New York Mills, MN", 12), place("City of New York, NY", 1), place("upper level New York, NY", 1)];
  assert.equal(choiceCaption("new york", newYork), "“new york” matches 4 places in 2 states.");
  // One place per state reads as before.
  const springfield = [place("Springfield, MA", 29), place("Springfield, KY", 20), place("Springfield, MO", 13)];
  assert.equal(choiceCaption("springfield", springfield), "“springfield” is in 3 states.");
  // Two same-named places in one state: still true, and singular.
  assert.equal(choiceCaption("washington pa", [place("Washington, PA", 6), place("Washington Boro, PA", 4)]), "“washington pa” matches 2 places in 1 state.");
});

test("no match is reported as none, not as an empty choice", () => {
  assert.deepEqual(choosePlace("zzqxv", []), { kind: "none" });
});

test("did-you-mean retries with looser queries, never the original", () => {
  assert.deepEqual(fallbackPlaceQueries("madisonn wi"), ["madisonn", "madi"]);
  assert.deepEqual(fallbackPlaceQueries("sprngfield"), ["sprn"], "the whole word was already the query");
  assert.deepEqual(fallbackPlaceQueries("ab"), [], "too short to loosen usefully");
});

test("did-you-mean finds the city behind a typo", async () => {
  // The hero's no-match path: full query, then each fallback until one hits.
  const typed = "madisonn wi";
  assert.equal((await searchPlaces(typed, 8)).items.length, 0);
  let suggestions: string[] = [];
  for (const fallback of fallbackPlaceQueries(typed)) {
    suggestions = (await searchPlaces(fallback, 4)).items.map((item) => item.label);
    if (suggestions.length) break;
  }
  assert.ok(suggestions.includes("Madison, WI"), `expected Madison, WI among ${suggestions.join(", ")}`);
});
