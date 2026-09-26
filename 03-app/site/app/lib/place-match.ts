/**
 * Tolerant matching for the city autocomplete.
 *
 * Places are labelled "City, ST", and the lookup used to be a raw substring
 * test on that label — so "madison wi" missed "Madison, WI" on the comma alone,
 * and "madison wisconsin" missed it entirely. A visitor who typed either got no
 * result and, from the hero, no feedback at all.
 *
 * Both sides are now reduced to plain lowercase words, a trailing state name is
 * read as its postal code, and every word the visitor typed has to begin one of
 * the label's words. That accepts the spellings people actually use —
 * "madison wi", "Madison,WI", "madison wisconsin", "san fran" — without
 * inventing fuzzy matches that would send someone to the wrong state.
 *
 * Pure and dependency-free so it is tested directly (tests/place-match.test.ts).
 */

const stateNames: Record<string, string> = {
  alabama: "al", alaska: "ak", arizona: "az", arkansas: "ar", california: "ca",
  colorado: "co", connecticut: "ct", delaware: "de", "district of columbia": "dc",
  florida: "fl", georgia: "ga", hawaii: "hi", idaho: "id", illinois: "il",
  indiana: "in", iowa: "ia", kansas: "ks", kentucky: "ky", louisiana: "la",
  maine: "me", maryland: "md", massachusetts: "ma", michigan: "mi",
  minnesota: "mn", mississippi: "ms", missouri: "mo", montana: "mt",
  nebraska: "ne", nevada: "nv", "new hampshire": "nh", "new jersey": "nj",
  "new mexico": "nm", "new york": "ny", "north carolina": "nc",
  "north dakota": "nd", ohio: "oh", oklahoma: "ok", oregon: "or",
  pennsylvania: "pa", "rhode island": "ri", "south carolina": "sc",
  "south dakota": "sd", tennessee: "tn", texas: "tx", utah: "ut", vermont: "vt",
  virginia: "va", washington: "wa", "west virginia": "wv", wisconsin: "wi",
  wyoming: "wy",
};

// Longest first, so "west virginia" is read before "virginia" can claim it.
const stateNamesByLength = Object.keys(stateNames).sort((a, b) => b.length - a.length);

const stateCodes = new Set(Object.values(stateNames));

/** Lowercase, strip diacritics and punctuation, collapse whitespace. */
export function normalizePlace(value: string): string {
  return value
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

/**
 * Normalize a visitor's query and read a trailing state name as its code.
 *
 * Only a *trailing* state name is converted, and only when something precedes
 * it: "madison wisconsin" becomes "madison wi", but "washington" on its own
 * stays a city search, and "kansas city" is left alone because the state name
 * leads rather than trails.
 */
export function normalizePlaceQuery(value: string): string {
  const normalized = normalizePlace(value);
  for (const name of stateNamesByLength) {
    if (normalized.endsWith(` ${name}`) && normalized.length > name.length + 1) {
      return `${normalized.slice(0, -name.length)}${stateNames[name]}`;
    }
  }
  return normalized;
}

/** The postal code a normalized query ends in, if it names a state at all. */
export function trailingStateCode(normalizedQuery: string): string | null {
  const words = normalizedQuery.split(" ");
  const last = words[words.length - 1];
  return words.length > 1 && stateCodes.has(last) ? last : null;
}

/**
 * Whether every query word begins a distinct word of the label, in any order.
 *
 * Distinct, so "san san" does not match "San Jose" twice over; prefix, so a
 * half-typed "madis" still suggests Madison while the visitor is typing.
 */
export function placeMatches(normalizedLabel: string, normalizedQuery: string): boolean {
  if (!normalizedQuery) return false;
  return placeWordsMatch(normalizedLabel.split(" "), normalizedQuery.split(" "));
}

/** `placeMatches` over pre-split words, for callers that cache the split. */
export function placeWordsMatch(labelWords: readonly string[], queryWords: readonly string[]): boolean {
  if (queryWords.length === 0 || queryWords.length > labelWords.length) return false;
  let used = 0;
  for (const word of queryWords) {
    let found = -1;
    for (let index = 0; index < labelWords.length; index += 1) {
      if ((used & (1 << index)) === 0 && labelWords[index].startsWith(word)) {
        found = index;
        break;
      }
    }
    if (found === -1) return false;
    used |= 1 << found;
  }
  return true;
}

/**
 * Rank a matching place, lower first: the label reading exactly as typed, then
 * one that starts with the query as whole words ("madison" → "Madison, WI"),
 * then one that starts mid-word ("madison" → "Madisonville, KY"), then any
 * other match. Farm count breaks ties, so among equally good spellings the
 * place with more farms leads.
 */
export function placeRank(normalizedLabel: string, normalizedQuery: string): number {
  if (normalizedLabel === normalizedQuery) return 0;
  if (normalizedLabel.startsWith(`${normalizedQuery} `)) return 1;
  if (normalizedLabel.startsWith(normalizedQuery)) return 2;
  return 3;
}

type Candidate = { label: string; state: string; farmCount: number };

export type PlaceDecision<T extends Candidate> =
  | { kind: "go"; place: T }
  | { kind: "choose"; places: T[] }
  | { kind: "none" };

/**
 * Decide what a submitted city search should do with its ranked matches.
 *
 * Go straight to a place only when the visitor has effectively named one: a
 * single match, a label typed exactly, a state they spelled out that the top
 * match is in, or a top match that so outweighs the rest that the others are
 * noise ("New Orleans, LA" with 65 farms against "New Orleans, NY" with 1).
 * Otherwise — "Springfield", "Madison" — ask, because guessing the state sends
 * someone hundreds of miles from where they meant.
 */
export function choosePlace<T extends Candidate>(query: string, allPlaces: readonly T[]): PlaceDecision<T> {
  if (allPlaces.length === 0) return { kind: "none" };
  if (allPlaces.length === 1) return { kind: "go", place: allPlaces[0] };

  const normalizedQuery = normalizePlaceQuery(query);
  if (normalizePlace(allPlaces[0].label) === normalizedQuery) return { kind: "go", place: allPlaces[0] };

  // A trailing state name can be the end of a city's own name: "Mount
  // Washington" is in Kentucky, not "Mount … in Washington". When some
  // candidate carries the words exactly as typed, the visitor named that city,
  // so keep to those and do not read the last word as a state.
  const literal = normalizePlace(query);
  const namedCities = literal === normalizedQuery
    ? []
    : allPlaces.filter((place) => placeMatches(normalizePlace(place.label), literal));
  const places = namedCities.length ? namedCities : allPlaces;
  const [top, next] = places;
  if (places.length === 1) return { kind: "go", place: top };

  // A state the visitor typed is the strongest signal there is, so it settles
  // the question on its own: farm count must never carry someone who asked
  // for Mississippi off to Wisconsin.
  const state = namedCities.length ? null : trailingStateCode(normalizedQuery);
  if (state) {
    const inState = places.filter((place) => place.state.toLowerCase() === state);
    if (inState.length === 1) return { kind: "go", place: inState[0] };
    return { kind: "choose", places: inState.length ? inState : [...places] };
  }

  if (top.farmCount >= 4 * Math.max(1, next.farmCount)) return { kind: "go", place: top };
  return { kind: "choose", places: [...places] };
}

/**
 * Looser queries to try when a city search finds nothing, for "did you mean".
 * The leading word first ("madisonn wi" → "madisonn"), then its first four
 * letters ("madi"), which catches a typo past the fourth letter without
 * inventing an edit-distance search.
 */
export function fallbackPlaceQueries(query: string): string[] {
  const [first = ""] = normalizePlace(query).split(" ");
  const queries = [first, first.slice(0, 4)].filter((value) => value.length >= 3);
  return [...new Set(queries)].filter((value) => value !== normalizePlace(query));
}
