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

/**
 * Typeface consistency.
 *
 * The display face is a variable font whose character comes from its axes: at
 * default `SOFT` and no `WONK`, Fraunces is a different-looking typeface with
 * the same name. The CSS `font:` shorthand resets `font-variation-settings`,
 * so any rule that sets the display face through the shorthand and forgets to
 * restate the axes silently renders the plain cut — which is how the hero and
 * the harvest tiles ended up in two different faces with nothing in the
 * stylesheet looking wrong.
 */

test("every rule that sets the display face also sets its axes", () => {
  const blocks = [...stylesheet.matchAll(/([^{}]+)\{([^{}]*)\}/g)];
  const offenders: string[] = [];
  for (const [, selector, body] of blocks) {
    const usesShorthand = /font:[^;]*var\(--display\)/.test(body);
    if (!usesShorthand) continue;
    if (!/font-variation-settings/.test(body)) offenders.push(selector.trim().replace(/\s+/g, " ").slice(0, 70));
  }
  assert.deepEqual(offenders, [], `display rules missing font-variation-settings: ${offenders.join(" | ")}`);
});

test("the display axes are declared once, as a token", () => {
  // Every rule points at the same custom property, so changing the voice of
  // the typeface is one edit rather than fifty.
  const declared = cssValue("display-settings");
  assert.ok(declared, "--display-settings is missing from :root");
  assert.match(declared!, /"SOFT"\s+\d+/);
  assert.match(declared!, /"WONK"\s+[01]/);
  const literals = [...stylesheet.matchAll(/font-variation-settings:\s*([^;]+);/g)]
    .map(([, value]) => value.trim())
    .filter((value) => !value.includes("var(--display-settings)"));
  // The hero's second line is allowed its own setting; nothing else should be.
  assert.ok(literals.length <= 1, `hard-coded variation settings: ${literals.join(" | ")}`);
});

/**
 * Stylesheet traps that cost real functionality.
 *
 * These are not style opinions. Each one is a rule that silently broke
 * something a person uses, where nothing in the CSS looked wrong.
 */

test("the hero search field is never clipped", () => {
  // The type-ahead list is a child of `.hero-field`, so any overflow clip on
  // the field clips the suggestions to the height of the pill: the list still
  // opens, still sets aria-expanded, still announces itself — and paints
  // nothing. The button is inset with its own radius instead.
  const field = stylesheet.match(/\.hero-location > \.hero-field\s*\{([^}]*)\}/);
  assert.ok(field, ".hero-location > .hero-field rule is missing");
  assert.doesNotMatch(field![1], /overflow\s*:\s*(hidden|clip|auto|scroll)/, "clipping the field hides the type-ahead");
});

test("the hero column that holds the search outranks its siblings", () => {
  // `.hero > :not(.hero-atlas)` puts every hero child on z-index 2, so the
  // column containing the search makes a stacking context the suggestion list
  // cannot escape — and the ticker, a later sibling, paints over it.
  const column = stylesheet.match(/\.hero > \.hero-copy-col\s*\{([^}]*)\}/);
  assert.ok(column, "no explicit z-index for the hero's search column");
  const z = column![1].match(/z-index:\s*(\d+)/);
  assert.ok(z && Number(z[1]) > 2, `search column must sit above its siblings, got ${z?.[1]}`);
});
