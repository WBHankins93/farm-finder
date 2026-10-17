/**
 * Runtime reader for the compact discovery index.
 *
 * The index is produced by `scripts/discovery_index.py` and served as a static
 * asset. It is deliberately *not* inlined in the worker bundle: expanding the
 * published feed into 68,618 JavaScript objects measures at ~152 MB retained,
 * and a Cloudflare Workers isolate is capped at 128 MB. Column-oriented views
 * over one inflated buffer hold the same dataset in ~37 MB, and the deployed
 * script stays small because the data never becomes JavaScript source.
 *
 * Field layout, flag bits, and the ASCII folding below mirror
 * `scripts/discovery_index.py` — change the two together.
 */
import type { Farm } from "./farms";

const MAGIC = "FFIDX1\0\0";
const UNIT_SEPARATOR = "\u0001";
const LIST_SEPARATOR = "\u0002";
const INDEX_ASSET_PATH = "/national-index.bin";

export type IndexPlace = {
  slug: string;
  name: string;
  state: string;
  label: string;
  lat: number;
  lng: number;
  farmCount: number;
};

type Header = {
  version: number;
  count: number;
  releaseId: string;
  states: string[];
  categories: string[];
  precisions: string[];
  productIds: string[];
  flagBits: Record<string, number>;
  displayFields: string[];
  sections: Record<string, { offset: number; length: number }>;
};

export type DiscoveryIndex = {
  count: number;
  releaseId: string;
  states: string[];
  categories: string[];
  productIds: string[];
  latitude: Float64Array;
  longitude: Float64Array;
  flags: Uint16Array;
  category: Uint8Array;
  precision: Uint8Array;
  productMask: Uint16Array;
  nameRank: Uint32Array;
  textStart: Uint32Array;
  textNameEnd: Uint32Array;
  textProductsEnd: Uint32Array;
  textPlaceEnd: Uint32Array;
  search: string;
  places: IndexPlace[];
  placeBySlug: Map<string, IndexPlace>;
  /** Bit positions within `flags`, keyed by the boolean they represent. */
  flag: Record<string, number>;
  /** True when record `i` has the given flag set. */
  hasFlag(i: number, bit: number): boolean;
  categoryOf(i: number): string;
  precisionOf(i: number): string;
  /** Expand one record. Call it for the handful of rows a response returns. */
  record(i: number): Farm;
  /** Row number for a public id, or -1. Builds its lookup map on first use. */
  positionOf(id: string): number;
  /**
   * Bitset of records whose searchable text contains `token`. Scans the packed
   * blob once per token instead of once per record, which is what keeps a
   * free-text query from degrading to O(records x blob).
   */
  recordsContaining(token: string): Uint8Array;
};

/**
 * Lowercase and strip to ASCII, matching `discovery_index.py::fold_ascii`.
 *
 * The packed search blob is pure ASCII so V8 keeps it in its one-byte string
 * representation; a single non-ASCII character would double its resident size.
 * Queries must be folded the same way to match what was indexed.
 */
export function foldAscii(value: string): string {
  return value
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^\u0000-\u007f]/g, "");
}

async function inflate(bytes: Uint8Array): Promise<Uint8Array> {
  // The container is gzipped on disk to stay under Cloudflare's 25 MiB
  // per-asset limit. Some asset layers decompress transparently, so only
  // inflate when the gzip magic is actually present.
  if (!(bytes[0] === 0x1f && bytes[1] === 0x8b)) return bytes;
  const stream = new Response(
    new Blob([bytes as BlobPart]).stream().pipeThrough(new DecompressionStream("gzip")),
  );
  return new Uint8Array(await stream.arrayBuffer());
}

function decode(buffer: ArrayBuffer): DiscoveryIndex {
  const bytes = new Uint8Array(buffer);
  const magic = new TextDecoder().decode(bytes.subarray(0, 8));
  if (magic !== MAGIC) {
    throw new Error(`discovery index has an unexpected container magic: ${JSON.stringify(magic)}`);
  }
  const headerLength = new DataView(buffer).getUint32(8, true);
  const header = JSON.parse(
    new TextDecoder().decode(bytes.subarray(12, 12 + headerLength)),
  ) as Header;
  if (header.version !== 1) {
    throw new Error(`discovery index version ${header.version} is not supported`);
  }

  // Section offsets are relative to a body that the writer aligned to 8 bytes,
  // so every typed-array view below is a view, never a copy.
  const bodyStart = Math.ceil((12 + headerLength) / 8) * 8;
  const at = (name: string) => {
    const section = header.sections[name];
    if (!section) throw new Error(`discovery index is missing section "${name}"`);
    return { offset: bodyStart + section.offset, length: section.length };
  };
  const view = <T>(
    name: string,
    Ctor: new (b: ArrayBuffer, o: number, n: number) => T,
    bytesPerElement: number,
  ): T => {
    const { offset, length } = at(name);
    return new Ctor(buffer, offset, length / bytesPerElement);
  };

  const searchSection = at("searchBlob");
  // One decode of a pure-ASCII blob; `indexOf` over it replaces per-record
  // strings entirely.
  const search = new TextDecoder("ascii").decode(
    bytes.subarray(searchSection.offset, searchSection.offset + searchSection.length),
  );

  const placesSection = at("places");
  const places = JSON.parse(
    new TextDecoder().decode(
      bytes.subarray(placesSection.offset, placesSection.offset + placesSection.length),
    ),
  ) as IndexPlace[];

  const displaySection = at("displayBlob");
  const displayBlob = bytes.subarray(
    displaySection.offset,
    displaySection.offset + displaySection.length,
  );
  const displayStart = view("displayStart", Uint32Array, 4);
  const textStart = view("textStart", Uint32Array, 4);
  const displayDecoder = new TextDecoder();

  const flag = header.flagBits;
  const flags = view("flags", Uint16Array, 2);
  const category = view("category", Uint8Array, 1);
  const precision = view("precision", Uint8Array, 1);

  let positions: Map<string, number> | null = null;

  const index: DiscoveryIndex = {
    count: header.count,
    releaseId: header.releaseId,
    states: header.states,
    categories: header.categories,
    productIds: header.productIds,
    latitude: view("latitude", Float64Array, 8),
    longitude: view("longitude", Float64Array, 8),
    flags,
    category,
    precision,
    productMask: view("productMask", Uint16Array, 2),
    nameRank: view("nameRank", Uint32Array, 4),
    textStart,
    textNameEnd: view("textNameEnd", Uint32Array, 4),
    textProductsEnd: view("textProductsEnd", Uint32Array, 4),
    textPlaceEnd: view("textPlaceEnd", Uint32Array, 4),
    search,
    places,
    placeBySlug: new Map(places.map((place) => [place.slug, place])),
    flag,

    hasFlag(i, bit) {
      return (flags[i] & (1 << bit)) !== 0;
    },
    categoryOf(i) {
      return header.categories[category[i]];
    },
    precisionOf(i) {
      return header.precisions[precision[i]];
    },

    record(i) {
      const parts = displayDecoder
        .decode(displayBlob.subarray(displayStart[i], displayStart[i + 1]))
        .split(UNIT_SEPARATOR);
      const field = (name: string) => parts[header.displayFields.indexOf(name)] ?? "";
      const productsText = field("products");
      return {
        id: field("id"),
        name: field("name"),
        category: field("category"),
        region: field("region"),
        parish: field("parish"),
        state: field("state"),
        city: field("city"),
        productsText: field("productsText"),
        products: productsText ? productsText.split(LIST_SEPARATOR) : [],
        marketPresence: field("marketPresence"),
        website: field("website"),
        hasWebsite: index.hasFlag(i, flag.hasWebsite),
        onlineStore: index.hasFlag(i, flag.onlineStore),
        facebook: index.hasFlag(i, flag.facebook),
        instagram: index.hasFlag(i, flag.instagram),
        farmersMarket: index.hasFlag(i, flag.farmersMarket),
        csa: index.hasFlag(i, flag.csa),
        ships: index.hasFlag(i, flag.ships),
        onFarm: index.hasFlag(i, flag.onFarm),
        contact: field("contact"),
        notes: field("notes"),
        source: field("source"),
        latitude: index.latitude[i],
        longitude: index.longitude[i],
        geoPrecision: index.precisionOf(i),
      };
    },

    positionOf(id) {
      if (!positions) {
        positions = new Map();
        for (let i = 0; i < header.count; i += 1) {
          const parts = displayDecoder.decode(
            displayBlob.subarray(displayStart[i], displayStart[i] + 128),
          );
          const end = parts.indexOf(UNIT_SEPARATOR);
          positions.set(end === -1 ? parts : parts.slice(0, end), i);
        }
      }
      return positions.get(id) ?? -1;
    },

    recordsContaining(token) {
      const hits = new Uint8Array(header.count);
      if (!token) return hits;
      let cursor = search.indexOf(token);
      let low = 0;
      while (cursor !== -1) {
        // Records are packed in order, so the search for each successive hit
        // can start from the previous record rather than from zero.
        let high = header.count;
        while (low < high) {
          const middle = (low + high) >>> 1;
          if (textStart[middle] <= cursor) low = middle + 1;
          else high = middle;
        }
        const record = low - 1;
        hits[record] = 1;
        // Skip to the end of this record: further hits inside it are redundant.
        cursor = search.indexOf(token, Math.max(cursor + token.length, textStart[record + 1]));
        low = record + 1;
      }
      return hits;
    },
  };

  return index;
}

type AssetFetcher = { fetch(request: Request): Promise<Response> };

let assets: AssetFetcher | null = null;
let origin = "";
let pending: Promise<DiscoveryIndex> | null = null;

/**
 * Record where this isolate can reach the index asset.
 *
 * The worker entry supplies the ASSETS binding, which is how production reads
 * it. Route handlers also call this with their request URL, because `vinext
 * dev` serves routes without going through the worker entry — there is no
 * binding there, only the dev server's own origin.
 */
export function bindDiscoveryContext(fetcher: AssetFetcher | undefined, requestUrl: string): void {
  if (fetcher) assets = fetcher;
  if (!requestUrl) return;
  try {
    origin = new URL(requestUrl).origin;
  } catch {
    /* keep the previous origin */
  }
}

async function fromAssetBinding(): Promise<ArrayBuffer | null> {
  if (!assets) return null;
  const response = await assets.fetch(new Request(new URL(INDEX_ASSET_PATH, origin || "http://localhost")));
  if (response.ok) return response.arrayBuffer();
  throw new Error(`discovery index asset returned ${response.status}`);
}

async function fromFileSystem(): Promise<ArrayBuffer | null> {
  // Unit tests run under real Node with no server in front of them. The
  // workerd runtime used by `vinext dev` has an fs shim that cannot read host
  // files, so a failure here is expected there and falls through to HTTP.
  try {
    const { readFile } = await import("node:fs/promises");
    const { fileURLToPath } = await import("node:url");
    const file = await readFile(fileURLToPath(new URL(`../../public${INDEX_ASSET_PATH}`, import.meta.url)));
    return file.buffer.slice(file.byteOffset, file.byteOffset + file.byteLength) as ArrayBuffer;
  } catch {
    return null;
  }
}

async function fromOrigin(): Promise<ArrayBuffer | null> {
  if (!origin) return null;
  const response = await fetch(new URL(INDEX_ASSET_PATH, origin));
  if (!response.ok) throw new Error(`discovery index fetch returned ${response.status}`);
  return response.arrayBuffer();
}

async function readIndexBytes(): Promise<ArrayBuffer> {
  for (const source of [fromAssetBinding, fromFileSystem, fromOrigin]) {
    const bytes = await source();
    if (bytes) return bytes;
  }
  throw new Error(
    `discovery index ${INDEX_ASSET_PATH} is unavailable — run "npm run data:build" to generate it`,
  );
}

/** The index for this isolate, built at most once. */
export function loadDiscoveryIndex(): Promise<DiscoveryIndex> {
  if (!pending) {
    pending = (async () => {
      const raw = await readIndexBytes();
      const inflated = await inflate(new Uint8Array(raw));
      return decode(
        inflated.buffer.slice(
          inflated.byteOffset,
          inflated.byteOffset + inflated.byteLength,
        ) as ArrayBuffer,
      );
    })().catch((error) => {
      // Never cache a failed load: the next request should retry.
      pending = null;
      throw error;
    });
  }
  return pending;
}
