import type { Farm } from "./farms";

type FarmSummaryFields = Pick<
  Farm,
  "name" | "category" | "city" | "state" | "productsText" | "products" | "marketPresence"
>;

/**
 * Product fields come from several source systems. Some sources provide one
 * item per array entry while others preserve a comma- or semicolon-delimited
 * phrase. Flattening both forms here keeps that source text intact in the
 * record while giving the profile one predictable display shape.
 */
export function normalizeProductLabels(...sources: Array<string | readonly string[]>): string[] {
  const seen = new Set<string>();
  const labels: string[] = [];

  for (const source of sources) {
    const values = typeof source === "string" ? [source] : source;
    for (const value of values) {
      for (const fragment of splitProductFragments(value)) {
        const label = fragment.trim().replace(/\s+/g, " ");
        if (!label) continue;

        const key = label.toLocaleLowerCase("en-US");
        if (seen.has(key)) continue;
        seen.add(key);
        labels.push(label);
      }
    }
  }

  return labels;
}

function splitProductFragments(value: string): string[] {
  const fragments: string[] = [];
  let start = 0;
  let parenthesisDepth = 0;

  for (let index = 0; index < value.length; index += 1) {
    const character = value[index];
    if (character === "(") parenthesisDepth += 1;
    else if (character === ")" && parenthesisDepth > 0) parenthesisDepth -= 1;
    else if ((character === "," || character === ";") && parenthesisDepth === 0) {
      fragments.push(value.slice(start, index));
      start = index + 1;
    }
  }

  fragments.push(value.slice(start));
  return fragments;
}

const productListFormatter = new Intl.ListFormat("en-US", {
  style: "long",
  type: "conjunction",
});

export function formatProductLabels(labels: readonly string[]): string {
  return productListFormatter.format(labels);
}

export function formatProductSummary(labels: readonly string[], limit = 5): string {
  const visible = labels.slice(0, limit);
  const remaining = labels.length - visible.length;
  const formatted = formatProductLabels(visible);
  return remaining > 0 ? `${formatted}, plus ${remaining} more` : formatted;
}

export function productLabelsForFarm(farm: Pick<Farm, "productsText" | "products">): string[] {
  // productsText is the record's authored display order. The structured array
  // is a fallback and may also contribute labels omitted from that text.
  return normalizeProductLabels(farm.productsText, farm.products);
}

export function farmLocationLabel(farm: Pick<Farm, "city" | "state" | "parish">): string {
  const place = [farm.city.trim(), farm.state.trim()].filter(Boolean).join(", ");
  const area = farm.parish.trim() || "Area not listed";
  return place ? `${place} · ${area}` : area;
}

export function farmProfileSummary(farm: FarmSummaryFields, productLabels = productLabelsForFarm(farm)): string {
  const category = farm.category.trim().toLocaleLowerCase("en-US");
  const article = /^[aeiou]/i.test(category) ? "an" : "a";
  const producerType = category ? `${article} ${category} producer` : "an independent producer";
  const location = [farm.city.trim(), farm.state.trim()].filter(Boolean).join(", ");
  const locationPhrase = location ? ` near ${location}` : "";
  const products = productLabels.length
    ? ` Known products include ${formatProductSummary(productLabels)}.`
    : " Specific products have not been listed yet.";
  const selling = farm.marketPresence.trim()
    ? ` Current sales information lists ${farm.marketPresence.toLocaleLowerCase("en-US")}.`
    : " A confirmed sales schedule is not listed yet.";

  return `${farm.name} is ${producerType}${locationPhrase}.${products}${selling}`;
}
