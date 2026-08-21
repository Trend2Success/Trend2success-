import { createHmac, timingSafeEqual } from "node:crypto";

/**
 * Computes the HMAC-SHA256 signature for a raw webhook body, hex-encoded.
 */
export function signWebhookPayload(rawBody: string, secret: string): string {
  return createHmac("sha256", secret).update(rawBody).digest("hex");
}

/**
 * Verifies a webhook signature using a constant-time comparison so response
 * timing can't be used to guess the correct signature byte-by-byte.
 *
 * `rawBody` must be the exact, unparsed request body — verifying against a
 * re-serialized JSON object can disagree with what the sender signed.
 */
export function verifyWebhookSignature(
  rawBody: string,
  signatureHeader: string | null,
  secret: string,
): boolean {
  if (!signatureHeader) return false;

  const expected = signWebhookPayload(rawBody, secret);
  const expectedBuf = Buffer.from(expected, "hex");
  const providedBuf = Buffer.from(signatureHeader, "hex");

  if (expectedBuf.length !== providedBuf.length) return false;
  return timingSafeEqual(expectedBuf, providedBuf);
}
