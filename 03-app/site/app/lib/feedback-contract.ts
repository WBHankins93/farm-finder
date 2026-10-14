export const feedbackTypes = ["missing_farm", "correction", "closure", "seasonal", "relocation", "duplicate", "other"] as const;
export const feedbackRelationships = ["owner", "staff", "visitor", "other", "unspecified"] as const;
export type FeedbackSubmission = {
  idempotencyKey: string;
  farmId?: string;
  farmName: string;
  city: string;
  state: string;
  type: typeof feedbackTypes[number];
  details: string;
  relationship: typeof feedbackRelationships[number];
  observedOn?: string;
  sourceUrl?: string;
  email?: string;
};
const states = new Set("AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC".split(" "));

export function parseFeedback(input: unknown):
  { submission: FeedbackSubmission; fieldErrors?: never } |
  { submission?: never; fieldErrors: Record<string, string> } {
  if (!input || typeof input !== "object" || Array.isArray(input)) return { fieldErrors: { form: "Provide a JSON object." } };
  const value = input as Record<string, unknown>;
  const fieldErrors: Record<string, string> = {};
  const text = (key: string, min: number, max: number, optional = false) => {
    const raw = value[key];
    if (optional && (raw === undefined || raw === "")) return undefined;
    if (typeof raw !== "string" || raw.trim().length < min || raw.trim().length > max || /[\u0000-\u0008\u000b\u000c\u000e-\u001f]/.test(raw)) {
      fieldErrors[key] = `Enter ${min}–${max} characters.`;
      return undefined;
    }
    return raw.trim();
  };
  const idempotencyKey = text("idempotencyKey", 36, 36);
  if (idempotencyKey && !/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(idempotencyKey)) fieldErrors.idempotencyKey = "Use a valid request identifier.";
  const farmId = text("farmId", 1, 160, true);
  const farmName = text("farmName", 2, 160);
  const city = text("city", 2, 120);
  const state = text("state", 2, 2)?.toUpperCase();
  if (state && !states.has(state)) fieldErrors.state = "Select a US state.";
  const type = text("type", 1, 30);
  if (!feedbackTypes.includes(type as FeedbackSubmission["type"])) fieldErrors.type = "Select a report type.";
  const details = text("details", 20, 4000);
  const relationship = value.relationship === undefined ? "unspecified" : text("relationship", 1, 20);
  if (!feedbackRelationships.includes(relationship as FeedbackSubmission["relationship"])) fieldErrors.relationship = "Select your relationship to the farm.";
  const observedOn = text("observedOn", 10, 10, true);
  if (observedOn && (!/^\d{4}-\d{2}-\d{2}$/.test(observedOn) || !Number.isFinite(Date.parse(observedOn)) || new Date(observedOn).toISOString().slice(0, 10) !== observedOn || observedOn > new Date().toISOString().slice(0, 10))) fieldErrors.observedOn = "Enter a valid date that is not in the future.";
  const sourceUrl = text("sourceUrl", 1, 2048, true);
  if (sourceUrl) {
    try {
      const url = new URL(sourceUrl);
      if (!["http:", "https:"].includes(url.protocol) || url.username || url.password) throw new Error();
    } catch { fieldErrors.sourceUrl = "Enter an http or https URL without credentials."; }
  }
  const email = text("email", 3, 254, true);
  if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) fieldErrors.email = "Enter a valid email address.";
  if (Object.keys(fieldErrors).length) return { fieldErrors };
  return { submission: { idempotencyKey: idempotencyKey!.toLowerCase(), farmId, farmName: farmName!, city: city!, state: state!, type: type as FeedbackSubmission["type"], details: details!, relationship: relationship as FeedbackSubmission["relationship"], observedOn, sourceUrl, email } };
}
