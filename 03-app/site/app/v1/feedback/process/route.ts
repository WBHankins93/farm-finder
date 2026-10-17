import { handleFeedbackReview } from "../../../lib/feedback-review-handler";
export const dynamic = "force-dynamic";
export const POST = (request: Request) => handleFeedbackReview(request, "process");
