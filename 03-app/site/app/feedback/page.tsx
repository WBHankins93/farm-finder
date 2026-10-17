import Link from "next/link";
import FeedbackForm from "../components/feedback-form";
import { getFarm } from "../lib/discovery-server";
import { feedbackEnabled } from "../lib/feedback-handler";
import { BrandMark } from "../lib/marks";
import "./feedback.css";

export const dynamic = "force-dynamic";
export const metadata = { title: "Suggest an update · FarmFinder" };

export default async function FeedbackPage({ searchParams }: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const enabled = feedbackEnabled();
  const params = await searchParams;
  const id = typeof params.farmId === "string" ? params.farmId : "";
  // Only trusted directory details prefill the form, never names in query parameters.
  const farm = enabled && id && id.length <= 160 ? await getFarm(id) : null;
  return <div className="feedback-shell">
    <header className="topbar"><Link className="brand" href="/"><BrandMark className="brand-mark" /><span>FarmFinder<small>Local farms, nationwide</small></span></Link><Link href="/#discover">Back to the directory</Link></header>
    <main className="feedback-main">
      <p className="section-number">Help keep the field guide current</p>
      <h1>Share what you know.</h1>
      <p className="feedback-intro">Know a farm we missed? Noticed a move, a seasonal change, or a detail that needs fixing? Firsthand knowledge helps us keep this directory useful.</p>
      {enabled ? <>
        {id && !farm && <p className="feedback-notice">We could not find that listing. You can still tell us the farm’s name and location below.</p>}
        <FeedbackForm farm={farm ? { id: farm.id, name: farm.name, city: farm.city, state: farm.state } : undefined} />
      </> : <section className="feedback-notice" aria-labelledby="feedback-unavailable"><h2 id="feedback-unavailable">Feedback submissions are not available yet.</h2><p>We are setting up a private review process for community updates. Please check back later.</p><Link href="/#discover">Explore the directory →</Link></section>}
    </main>
  </div>;
}
