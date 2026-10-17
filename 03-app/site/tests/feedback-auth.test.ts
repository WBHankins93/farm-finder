import assert from "node:assert/strict";
import test from "node:test";
import { generateKeyPair, SignJWT, type JWTPayload } from "jose";
import { authenticateCurator, FeedbackAuthError, feedbackReviewConfigured, type FeedbackAuthConfig } from "../app/lib/feedback-auth";

const keys = generateKeyPair("RS256");
const config: FeedbackAuthConfig = { enabled: "true", issuer: "https://farmfinder.cloudflareaccess.com", audience: "review-app-audience", curatorEmails: "curator@example.com, second@example.com" };
async function signed(patch: JWTPayload = {}, omit: string[] = []) {
  const now = Math.floor(Date.now() / 1000);
  const payload: JWTPayload = { iss: config.issuer, aud: config.audience, sub: "curator-id", email: "Curator@Example.com", iat: now, exp: now + 300, ...patch };
  for (const claim of omit) delete payload[claim];
  return new SignJWT(payload).setProtectedHeader({ alg: "RS256", kid: "test-key" }).sign((await keys).privateKey);
}
function headers(token: string) { return new Headers({ "Cf-Access-Jwt-Assertion": token }); }
async function auth(token: string, settings = config) {
  return authenticateCurator(headers(token), settings, async () => (await keys).publicKey);
}
function failure(status: number) {
  return (error: unknown) => error instanceof FeedbackAuthError && error.status === status && !error.message.includes("eyJ");
}

test("accepts signed Access identity on explicit case-insensitive curator allowlist", async () => {
  assert.deepEqual(await auth(await signed()), { subject: "curator-id", email: "curator@example.com" });
  assert.equal(feedbackReviewConfigured(config), true);
});
test("disabled, missing and unsafe issuer configuration fail closed", async () => {
  for (const patch of [{ enabled: "false" }, { issuer: undefined }, { audience: undefined }, { curatorEmails: undefined }, { curatorEmails: "*" }, { curatorEmails: "curator@example.com," }, { audience: " " }, ...["http://farmfinder.cloudflareaccess.com", "https://farmfinder.cloudflareaccess.com.evil.test", "https://user@farmfinder.cloudflareaccess.com", "https://farmfinder.cloudflareaccess.com/", "https://farmfinder.cloudflareaccess.com:443", "https://farmfinder.cloudflareaccess.com?x=1"].map((issuer) => ({ issuer }))]) {
    const invalid = { ...config, ...patch };
    assert.equal(feedbackReviewConfigured(invalid), false);
    await assert.rejects(auth(await signed(), invalid), failure(503));
  }
});
test("rejects missing assertion and spoofed email headers or cookies", async () => {
  for (const spoof of [{}, { "Cf-Access-Authenticated-User-Email": "curator@example.com" }, { Cookie: `CF_Authorization=${await signed()}` }]) {
    await assert.rejects(authenticateCurator(new Headers(spoof as Record<string, string>), config), failure(401));
  }
});
test("rejects expiry, future validity, wrong audience and issuer", async () => {
  const now = Math.floor(Date.now() / 1000);
  for (const patch of [{ exp: now - 120 }, { nbf: now + 120 }, { iat: now + 120 }, { aud: "other-app" }, { iss: "https://other.cloudflareaccess.com" }]) {
    await assert.rejects(auth(await signed(patch)), failure(401));
  }
});
test("requires valid identity and temporal claims", async () => {
  for (const claim of ["exp", "iat", "sub", "email"]) await assert.rejects(auth(await signed({}, [claim])), failure(401));
  for (const patch of [{ sub: "" }, { sub: " " }, { email: "invalid" }, { email: 123 }, { iat: "yesterday" }, { exp: "tomorrow" }]) {
    await assert.rejects(auth(await signed(patch as JWTPayload)), failure(401));
  }
});
test("signed non-curator cannot elevate privilege with email header", async () => {
  const requestHeaders = headers(await signed({ email: "outsider@example.com" }));
  requestHeaders.set("Cf-Access-Authenticated-User-Email", "curator@example.com");
  await assert.rejects(authenticateCurator(requestHeaders, config, async () => (await keys).publicKey), failure(403));
});
test("rejects payload tampering, unsigned tokens, other algorithms, and oversized assertions", async () => {
  const token = await signed();
  const parts = token.split(".");
  parts[1] = Buffer.from(JSON.stringify({ sub: "forged", email: "curator@example.com" })).toString("base64url");
  const hmac = await new SignJWT({ email: "curator@example.com" }).setProtectedHeader({ alg: "HS256" }).sign(new Uint8Array(32));
  for (const invalid of [parts.join("."), `${parts[0]}.${parts[1]}.`, hmac, "x".repeat(16_385)]) {
    await assert.rejects(auth(invalid), failure(401));
  }
});
test("key service errors never disclose raw tokens or upstream secrets", async () => {
  const token = await signed();
  await assert.rejects(authenticateCurator(headers(token), config, async () => { throw new Error(`secret ${token}`); }), (error: unknown) => {
    assert.ok(error instanceof FeedbackAuthError);
    assert.equal(error.status, 401);
    assert.equal(error.message, "Authentication is required.");
    assert.equal(error.cause, undefined);
    return true;
  });
});
