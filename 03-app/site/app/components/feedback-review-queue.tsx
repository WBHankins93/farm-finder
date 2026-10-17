"use client";
import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import type { FeedbackReviewRecord, ReviewStatus } from "../lib/feedback-review-store";

export default function FeedbackReviewQueue() {
  const [status, setStatus] = useState<ReviewStatus>("pending");
  const [offset, setOffset] = useState(0);
  const [reports, setReports] = useState<FeedbackReviewRecord[]>([]);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const requestVersion = useRef(0);
  const saving = useRef(false);
  const noticeRef = useRef<HTMLDivElement>(null);
  const load = useCallback(async () => {
    const version = ++requestVersion.current;
    setBusy(true); setError(""); setReports([]);
    try {
      const response = await fetch(`/v1/feedback/review?status=${status}&offset=${offset}`, { cache: "no-store", signal: AbortSignal.timeout(15000) });
      if (!response.ok) throw new Error(response.status === 401 || response.status === 403 ? "Your curator access needs to be renewed. Reload through the access gateway." : "Could not load reports. Try again.");
      const body = await response.json() as { reports: FeedbackReviewRecord[] };
      if (version === requestVersion.current) setReports(body.reports);
    } catch (cause) { if (version === requestVersion.current) setError(cause instanceof Error ? cause.message : "Could not load reports."); }
    finally { if (version === requestVersion.current) setBusy(false); }
  }, [status, offset]);
  useEffect(() => {
    const requests = requestVersion;
    const timer = setTimeout(() => { void load(); }, 0);
    return () => { clearTimeout(timer); requests.current++; };
  }, [load]);
  useEffect(() => { if (error || notice) noticeRef.current?.focus(); }, [error, notice]);

  async function decide(event: FormEvent<HTMLFormElement>, report: FeedbackReviewRecord) {
    event.preventDefault();
    if (saving.current) return;
    const form = event.currentTarget;
    const fields = Object.fromEntries(new FormData(form));
    saving.current = true; setBusy(true); setError(""); setNotice("");
    try {
      const response = await fetch("/v1/feedback/review", { method: "POST", signal: AbortSignal.timeout(15000), headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ...fields, receipt: report.receipt, expectedRevision: report.revision }) });
      if (!response.ok) throw new Error(response.status === 409 ? "Another decision was saved for this report. Copy your draft, then refresh before deciding again." : "The decision was not confirmed. Your draft remains below. Refresh the history before retrying.");
      form.reset();
      await load(); setNotice("Decision recorded. Public farm records have not changed.");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Decision could not be saved."); }
    finally { saving.current = false; setBusy(false); }
  }
  async function processBatch() {
    if (saving.current) return;
    saving.current = true; setBusy(true); setError(""); setNotice("");
    try {
      const response = await fetch("/v1/feedback/process", { method: "POST", signal: AbortSignal.timeout(60000) });
      if (!response.ok) throw new Error("Processing is unavailable. Reports remain stored for another attempt.");
      const result = await response.json() as { claimed: number; completed: number; retried: number; failed: number };
      await load(); setNotice(`Batch: ${result.claimed} claimed, ${result.completed} completed, ${result.retried} waiting for retry, ${result.failed} failed.`);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Processing failed."); }
    finally { saving.current = false; setBusy(false); }
  }
  return <>
    <p>Review the account and evidence before deciding. Approval prepares a correction for later publication; it does not change the directory.</p>
    <div className="review-controls"><label htmlFor="review-status">Reports <select id="review-status" value={status} disabled={busy} onChange={(event) => { setOffset(0); setStatus(event.target.value as ReviewStatus); }}><option value="pending">Pending review</option><option value="reviewing">Needs information</option><option value="resolved">Decided</option></select></label><button disabled={busy} onClick={() => { void load(); }}>Refresh</button><button disabled={busy} onClick={() => { void processBatch(); }}>Triage next batch</button></div>
    {(error || notice) && <div className="feedback-notice" ref={noticeRef} tabIndex={-1} role={error ? "alert" : "status"}>{error || notice}</div>}
    {busy && <p role="status">Working…</p>}
    {!busy && !error && reports.length === 0 && <p>No reports in this queue.</p>}
    <p className="feedback-hint">Page {offset / 25 + 1}, up to 25 reports, oldest first. Reporter contact details are excluded.</p>
    <div className="review-controls"><button disabled={busy || offset === 0} onClick={() => setOffset(Math.max(0, offset - 25))}>Previous page</button><button disabled={busy || reports.length < 25 || offset >= 10000} onClick={() => setOffset(offset + 25)}>Next page</button></div>
    {reports.map((report) => <article className="review-report" key={report.receipt}>
      <h2>{report.payload.farmName}</h2><p>{report.payload.city}, {report.payload.state} · {report.payload.type} · Revision {report.revision}</p>
      <p><strong>{report.triage?.priority === "high" ? "Priority review" : report.triage ? "Triaged" : "Awaiting triage"}</strong> · {report.outcome ?? "No decision"}</p>
      <p className="review-account">{report.payload.details}</p>
      <dl><dt>Relationship (self-reported)</dt><dd>{report.payload.relationship}</dd><dt>Observed</dt><dd>{report.payload.observedOn || "Unknown"}</dd><dt>Source release</dt><dd>{report.releaseId}</dd><dt>Receipt</dt><dd>{report.receipt}</dd></dl>
      {report.payload.sourceUrl && <p>Submitted evidence: <a href={report.payload.sourceUrl} target="_blank" rel="noopener noreferrer">Open source ↗</a></p>}
      <details><summary>Decision history ({report.history.length})</summary>{report.history.map((entry) => <div key={entry.revision}><p>Revision {entry.revision}: {entry.decision} · {entry.actorEmail} · {entry.createdAt}</p><p>{entry.reason}</p>{entry.evidenceUrl && <a href={entry.evidenceUrl} target="_blank" rel="noopener noreferrer">Decision evidence ↗</a>}</div>)}</details>
      <form className="feedback-form" onSubmit={(event) => { void decide(event, report); }}>
        <fieldset disabled={busy}><legend>Record a decision</legend><label>Decision<select name="decision" defaultValue="needs_information"><option value="needs_information">Needs more information</option><option value="approve">Approve for later publication</option><option value="reject">Reject proposed change</option><option value="duplicate">Duplicate report</option></select></label><label>Evidence and reasoning<textarea name="reason" required minLength={20} maxLength={4000} rows={3} /></label><label>Evidence URL (optional)<input name="evidenceUrl" type="url" maxLength={2048} /></label><button className="feedback-submit" type="submit">Save decision</button></fieldset>
      </form>
    </article>)}
  </>;
}
