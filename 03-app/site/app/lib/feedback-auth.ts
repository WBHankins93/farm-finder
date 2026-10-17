import { createRemoteJWKSet, jwtVerify, type JWTVerifyGetKey } from "jose";

// Server-side only. The issuer and allowlist never come from request input.
export type FeedbackAuthConfig = {
  enabled?: string;
  issuer?: string;
  audience?: string;
  curatorEmails?: string;
};
export type FeedbackCurator = { subject: string; email: string };
export class FeedbackAuthError extends Error {
  constructor(public readonly status: 401 | 403 | 503) {
    super(status === 503 ? "Feedback review is unavailable." : status === 403 ? "Curator access is required." : "Authentication is required.");
    this.name = "FeedbackAuthError";
  }
}
function environmentConfig(): FeedbackAuthConfig {
  return {
    enabled: process.env.FEEDBACK_REVIEW_ENABLED,
    issuer: process.env.FEEDBACK_ACCESS_ISSUER,
    audience: process.env.FEEDBACK_ACCESS_AUDIENCE,
    curatorEmails: process.env.FEEDBACK_CURATOR_EMAILS,
  };
}
const emailPattern = /^[^\s@,]+@[^\s@,]+\.[^\s@,]+$/;
function validatedConfig(config: FeedbackAuthConfig) {
  const emails = config.curatorEmails?.split(",").map((email) => email.trim().toLowerCase());
  if (config.enabled !== "true" ||
    !config.issuer || !/^https:\/\/[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.cloudflareaccess\.com$/.test(config.issuer) ||
    !config.audience || config.audience !== config.audience.trim() || /\s/.test(config.audience) ||
    !emails?.length || emails.some((email) => !emailPattern.test(email))) return null;
  return { issuer: config.issuer, audience: config.audience, emails: new Set(emails) };
}
export function feedbackReviewConfigured(config: FeedbackAuthConfig = environmentConfig()): boolean {
  return validatedConfig(config) !== null;
}
let cachedIssuer: string | undefined;
let cachedResolver: JWTVerifyGetKey | undefined;
function issuerKeys(issuer: string): JWTVerifyGetKey {
  if (issuer !== cachedIssuer || !cachedResolver) {
    cachedResolver = createRemoteJWKSet(new URL(`${issuer}/cdn-cgi/access/certs`), {
      timeoutDuration: 5000, cooldownDuration: 30_000, cacheMaxAge: 600_000,
    });
    cachedIssuer = issuer;
  }
  return cachedResolver;
}

// Dependency injection supports signed-token tests; routes use only the headers argument.
export async function authenticateCurator(
  headers: Headers,
  config: FeedbackAuthConfig = environmentConfig(),
  resolveKey?: JWTVerifyGetKey,
): Promise<FeedbackCurator> {
  const settings = validatedConfig(config);
  if (!settings) throw new FeedbackAuthError(503);
  const token = headers.get("Cf-Access-Jwt-Assertion");
  if (!token || token.length > 16_384) throw new FeedbackAuthError(401);
  let payload;
  try {
    ({ payload } = await jwtVerify(token, resolveKey ?? issuerKeys(settings.issuer), {
      algorithms: ["RS256"], issuer: settings.issuer, audience: settings.audience,
      requiredClaims: ["exp", "iat", "sub", "email"], clockTolerance: 30,
    }));
  } catch {
    // Never expose tokens, upstream details, or verification errors to callers/logs.
    throw new FeedbackAuthError(401);
  }
  if (typeof payload.sub !== "string" || !payload.sub.trim() || payload.sub.length > 512 ||
    typeof payload.email !== "string" || !emailPattern.test(payload.email) ||
    typeof payload.iat !== "number" || !Number.isFinite(payload.iat) ||
    payload.iat > Date.now() / 1000 + 30) throw new FeedbackAuthError(401);
  const email = payload.email.toLowerCase();
  if (!settings.emails.has(email)) throw new FeedbackAuthError(403);
  return { subject: payload.sub, email };
}
