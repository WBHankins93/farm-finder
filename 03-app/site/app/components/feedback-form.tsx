"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { parseFeedback, type FeedbackSubmission } from "../lib/feedback-contract";

type ListedFarm = { id: string; name: string; city: string; state: string };

export default function FeedbackForm({ farm }: { farm?: ListedFarm }) {
  const [linkedFarmId, setLinkedFarmId] = useState(farm?.id);
  const [retryConflict, setRetryConflict] = useState(false);
  const [pending, setPending] = useState(false);
  const [receipt, setReceipt] = useState("");
  const [error, setError] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const sending = useRef(false);
  const attempt = useRef<{ snapshot: string; key: string } | null>(null);
  const notice = useRef<HTMLDivElement>(null);

  useEffect(() => { if (error || receipt) notice.current?.focus(); }, [error, receipt]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (sending.current) return;
    const form = event.currentTarget;
    const data = { ...Object.fromEntries(new FormData(form)), farmId: linkedFarmId };
    const snapshot = JSON.stringify(data);
    // Keep the key in memory across ambiguous failures; never persist private reports.
    if (attempt.current?.snapshot !== snapshot) {
      attempt.current = { snapshot, key: crypto.randomUUID() };
    }
    const result = parseFeedback({ ...data, idempotencyKey: attempt.current.key });
    setError("");
    setRetryConflict(false);
    setFieldErrors({});
    if (!result.submission) {
      setFieldErrors(result.fieldErrors);
      setError("Check the highlighted fields, then send your update again.");
      return;
    }
    const submission: FeedbackSubmission = result.submission;
    sending.current = true;
    setPending(true);
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 20_000);
    try {
      const response = await fetch("/v1/feedback", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(submission), signal: controller.signal,
      });
      const payload: unknown = await response.json();
      const body = payload && typeof payload === "object" ? payload as Record<string, unknown> : {};
      const errors = body.fieldErrors && typeof body.fieldErrors === "object"
        ? Object.fromEntries(Object.entries(body.fieldErrors).filter((entry): entry is [string, string] => typeof entry[1] === "string"))
        : {};
      if (response.ok && body.status === "received" && typeof body.receipt === "string") {
        setReceipt(body.receipt);
      } else if (response.status === 400 && Object.keys(errors).length) {
        setFieldErrors(errors);
        setError(errors.farmId || errors.form || "Check the highlighted fields, then send your update again.");
      } else if (response.status === 409) {
        setRetryConflict(true);
        setError("This request identifier belongs to a different report. You can start a new request with the text below.");
      } else {
        setError(response.status === 429
          ? "We have received too many requests. Please try again later. Your text is still here."
          : "We could not confirm receipt. Please try again later. Your text is still here.");
      }
    } catch {
      setError("We could not confirm receipt. Check your connection and try again. Your text is still here.");
    } finally {
      clearTimeout(timeout);
      sending.current = false;
      setPending(false);
    }
  }

  function errorProps(name: string) {
    return { "aria-invalid": !!fieldErrors[name], "aria-describedby": fieldErrors[name] ? `${name}-error` : undefined };
  }
  function fieldError(name: string) {
    return fieldErrors[name] ? <span className="feedback-field-error" id={`${name}-error`}>{fieldErrors[name]}</span> : null;
  }

  if (receipt) return <div className="feedback-notice feedback-success" ref={notice} tabIndex={-1} role="status">
    <h2>Thank you for the field note.</h2>
    <p>Your update is saved for review. It has not changed the public listing.</p>
    <p>Keep this receipt for your records: <strong>{receipt}</strong></p>
    <Link href="/#discover">Back to the directory →</Link>
  </div>;

  return <form className="feedback-form" onSubmit={submit}>
    <p className="feedback-required">All fields are required unless marked optional. No account needed.</p>
    {error && <div className="feedback-notice" ref={notice} tabIndex={-1} role="alert">{error}
      {fieldErrors.farmId && linkedFarmId && <p><button type="button" onClick={() => { setLinkedFarmId(undefined); setFieldErrors({}); setError("Listing link removed. Your text is still here; send it when ready."); }}>Continue without the listing link</button></p>}
      {retryConflict && <p><button type="button" onClick={() => { attempt.current = null; setRetryConflict(false); setError("Ready to send as a new report. Your text is still here."); }}>Start a new request</button></p>}
    </div>}
    <fieldset disabled={pending}>
      <legend>About the farm</legend>
      {farm && linkedFarmId && <p className="feedback-linked">Updating the listing for <strong>{farm.name}</strong>. Describe any name or location changes below.</p>}
      <label htmlFor="farmName">Farm name<input id="farmName" name="farmName" required minLength={2} maxLength={160} defaultValue={farm?.name} {...errorProps("farmName")} />{fieldError("farmName")}</label>
      <div className="feedback-row">
        <label htmlFor="city">City or town<input id="city" name="city" required minLength={2} maxLength={120} defaultValue={farm?.city} {...errorProps("city")} />{fieldError("city")}</label>
        <label htmlFor="state">State abbreviation<input id="state" name="state" required minLength={2} maxLength={2} pattern="[A-Za-z]{2}" placeholder="LA" defaultValue={farm?.state} autoCapitalize="characters" {...errorProps("state")} />{fieldError("state")}</label>
      </div>
      <label htmlFor="type">What should we update?<select id="type" name="type" defaultValue={farm ? "correction" : "missing_farm"} {...errorProps("type")}>
        <option value="missing_farm">Add a missing farm</option><option value="correction">Correct listing details</option><option value="closure">Report a closure or reopening</option><option value="seasonal">Update seasonal availability</option><option value="relocation">Report a move</option><option value="duplicate">Report a duplicate listing</option><option value="other">Something else</option>
      </select>{fieldError("type")}</label>
      <label htmlFor="details">What did you learn?<span className="feedback-hint" id="details-hint">Tell us what changed and how you know. Please leave out private home addresses and other people’s personal details. At least 20 characters.</span><textarea id="details" name="details" rows={6} required minLength={20} maxLength={4000} {...errorProps("details")} aria-describedby={`details-hint${fieldErrors.details ? " details-error" : ""}`} />{fieldError("details")}</label>
    </fieldset>
    <fieldset disabled={pending}>
      <legend>A little more context</legend>
      <label htmlFor="relationship">Your connection to the farm <span className="feedback-optional">(optional)</span><select id="relationship" name="relationship" defaultValue="unspecified" {...errorProps("relationship")}><option value="unspecified">Prefer not to say</option><option value="owner">Owner</option><option value="staff">Staff member</option><option value="visitor">Visitor or customer</option><option value="other">Other</option></select>{fieldError("relationship")}</label>
      <label htmlFor="observedOn">When did you learn this? <span className="feedback-optional">(optional)</span><input id="observedOn" name="observedOn" type="date" {...errorProps("observedOn")} />{fieldError("observedOn")}</label>
      <label htmlFor="sourceUrl">Public link supporting your update <span className="feedback-optional">(optional)</span><input id="sourceUrl" name="sourceUrl" type="url" maxLength={2048} placeholder="https://" {...errorProps("sourceUrl")} />{fieldError("sourceUrl")}</label>
      <label htmlFor="email">Your email <span className="feedback-optional">(optional, private)</span><input id="email" name="email" type="email" autoComplete="email" maxLength={254} {...errorProps("email")} aria-describedby={`email-hint${fieldErrors.email ? " email-error" : ""}`} /><span className="feedback-hint" id="email-hint">Only for following up on this report. It will not appear in the directory.</span>{fieldError("email")}</label>
    </fieldset>
    <p className="feedback-hint">Reports are stored privately for review. Verified corrections may appear in the directory. A report alone does not remove a farm or confirm a closure.</p>
    <button className="feedback-submit" type="submit" disabled={pending}>{pending ? "Sending your update…" : "Send update for review"}</button>
    <span className="sr-only" role="status">{pending ? "Sending your update. Please wait." : ""}</span>
  </form>;
}
