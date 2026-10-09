import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { brandPalette, brandRadii, brandTokens, contrastRatio } from "../app/lib/brand";

/**
 * The palette is declared twice — as CSS custom properties the browser reads,
 * and as data the brand page and future native primitives read. Two
 * declarations drift, so these tests make drift a build failure rather than
 * something somebody notices in a screenshot six weeks later.
 */

const stylesheet = await readFile(new URL("../app/globals.css", import.meta.url), "utf8");
const rootBlock = stylesheet.slice(stylesheet.indexOf(":root {"), stylesheet.indexOf("}", stylesheet.indexOf(":root {")));

function cssValue(name: string): string | null {
  const match = rootBlock.match(new RegExp(`--${name}\\s*:\\s*([^;]+);`));
  return match ? match[1].trim() : null;
}

test("every brand token is declared in :root with the same value", () => {
  for (const token of brandTokens) {
    const declared = cssValue(token.name);
    assert.ok(declared, `--${token.name} (${token.label}) is missing from :root`);
    assert.equal(declared, token.value, `--${token.name} drifted: CSS has ${declared}, brand.ts has ${token.value}`);
  }
});

test("every colour in :root is accounted for in the palette", () => {
  // The other direction: a colour added to the stylesheet and not to the
  // palette is a colour nobody can find, and the brand page will not show it.
  const declared = [...rootBlock.matchAll(/--([a-z0-9-]+)\s*:\s*(#[0-9a-f]{3,8})\s*;/gi)].map(([, name]) => name);
  const known = new Set(brandTokens.map((token) => token.name));
  const orphans = declared.filter((name) => !known.has(name));
  assert.deepEqual(orphans, [], `colours in :root with no entry in brand.ts: ${orphans.join(", ")}`);
});

test("radii are declared once and match", () => {
  for (const radius of brandRadii) {
    assert.equal(cssValue(radius.name), radius.value, `--${radius.name} drifted`);
  }
});

test("every text colour clears 4.5:1 on the surfaces it is used on", () => {
  // The rule that is easiest to break and hardest to see. A brand colour and a
  // text colour are different jobs: --tomato is allowed to be 3.97:1 because
  // it never carries small text, and --rust exists so that labels do not.
  const value = (name: string) => brandTokens.find((token) => token.name === name)!.value;
  const failures: string[] = [];
  for (const token of brandTokens) {
    for (const surface of token.onSurfaces) {
      const ratio = contrastRatio(token.value, value(surface));
      if (ratio < 4.5) failures.push(`--${token.name} on --${surface} is ${ratio}:1`);
    }
  }
  assert.deepEqual(failures, [], failures.join("; "));
});

test("the brand tomato is held back from small text on purpose", () => {
  // If this ever passes, somebody has darkened --tomato and the two-token
  // split has quietly lost its reason to exist — collapse them deliberately
  // rather than leaving a token nobody understands.
  const tomato = brandTokens.find((token) => token.name === "tomato")!;
  assert.deepEqual(tomato.onSurfaces, [], "--tomato must not be listed as a text colour");
  assert.ok(
    contrastRatio(tomato.value, "#fffdf7") < 4.5,
    "--tomato now clears 4.5:1; fold it into --rust rather than keeping two tokens",
  );
});

test("the palette stays small enough to hold in your head", () => {
  // Consistency across pages is a function of how many choices exist. Twenty
  // is already generous for a directory with one accent.
  assert.ok(brandTokens.length <= 20, `${brandTokens.length} tokens is too many to apply consistently`);
  const names = brandTokens.map((token) => token.name);
  assert.equal(new Set(names).size, names.length, "duplicate token names");
  for (const group of brandPalette) {
    assert.ok(group.tokens.length > 0, `${group.title} has no tokens`);
    assert.ok(group.note.length > 0, `${group.title} needs a note saying when to reach for it`);
  }
});
