import Link from "next/link";
import { headers } from "next/headers";
import { authenticateCurator } from "../../lib/feedback-auth";
import FeedbackReviewQueue from "../../components/feedback-review-queue";
import "../../feedback/feedback.css";
import "./review.css";

export const dynamic = "force-dynamic";
export const metadata = { title: "Private feedback review · FarmFinder", robots: { index: false, follow: false } };
export default async function ReviewFeedbackPage() {
  let authorized = false;
  try { await authenticateCurator(new Headers(await headers())); authorized = Boolean(process.env.FEEDBACK_REVIEW_DATABASE_URL); } catch { /* Show no report data without verified access. */ }
  return <main className="feedback-main review-main">
    <Link href="/">FarmFinder</Link>
    <p className="section-number">Private workspace</p><h1>Review field notes.</h1>
    {authorized ? <FeedbackReviewQueue /> : <section className="feedback-notice"><h2>Curator access is required.</h2><p>Open this workspace through the configured FarmFinder access gateway. Review remains unavailable until access and storage are configured.</p></section>}
  </main>;
}
