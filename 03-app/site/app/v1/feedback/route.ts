import stats from "../../data/directory-stats.generated.json";
import { bindDiscoveryContext } from "../../lib/discovery-index";
import { getFarm } from "../../lib/discovery-server";
import { feedbackEnabled, handleFeedback } from "../../lib/feedback-handler";

export async function POST(request: Request) {
  bindDiscoveryContext(undefined, request.url);
  // Lazy loading keeps disabled deployments independent of a database connection.
  return handleFeedback(request, {
    enabled: feedbackEnabled(),
    releaseId: stats.releaseId,
    farmExists: async (id) => Boolean(await getFarm(id)),
    store: async (submission, releaseId, validateNew) => {
      const { storeFeedback } = await import("../../lib/feedback-store");
      return storeFeedback(process.env.FEEDBACK_DATABASE_URL!, submission, releaseId, validateNew);
    },
    isConflict: (error) => error instanceof Error && error.name === "FeedbackConflictError",
  });
}
