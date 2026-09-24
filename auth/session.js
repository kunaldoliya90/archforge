// Signed session cookies. A token is "<expiry>.<HMAC-SHA256 of expiry>", so the server
// can verify it without storing anything.

const COOKIE = "af_session";
const SESSION_SECONDS = 7 * 24 * 60 * 60;
const COOKIE_ATTRS = "Path=/; HttpOnly; Secure; SameSite=Lax";

const encoder = new TextEncoder();

// Compares every character regardless of where the first mismatch is, so response
// timing doesn't reveal how much of a secret was right.
export function safeEqual(a, b) {
  let diff = a.length ^ b.length;
  for (let i = 0; i < Math.max(a.length, b.length); i++) {
    diff |= (a.charCodeAt(i) || 0) ^ (b.charCodeAt(i) || 0);
  }
  return diff === 0;
}

async function sign(value, secret) {
  const key = await crypto.subtle.importKey(
    "raw", encoder.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"],
  );
  const mac = await crypto.subtle.sign("HMAC", key, encoder.encode(value));
  return btoa(String.fromCharCode(...new Uint8Array(mac)))
    .replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function readCookie(request) {
  const cookies = request.headers.get("cookie") || "";
  const match = cookies.match(new RegExp(`(?:^|;\\s*)${COOKIE}=([^;]+)`));
  return match ? match[1] : null;
}

/** Returns a Set-Cookie value that starts a new session. */
export async function sessionCookie(secret) {
  const expires = String(Math.floor(Date.now() / 1000) + SESSION_SECONDS);
  const token = `${expires}.${await sign(expires, secret)}`;
  return `${COOKIE}=${token}; ${COOKIE_ATTRS}; Max-Age=${SESSION_SECONDS}`;
}

/** Returns a Set-Cookie value that ends the session. */
export function clearedSessionCookie() {
  return `${COOKIE}=; ${COOKIE_ATTRS}; Max-Age=0`;
}

export async function hasValidSession(request, secret) {
  const token = readCookie(request);
  if (!token) return false;
  const [expires, mac] = token.split(".");
  if (!expires || !mac || Number(expires) * 1000 < Date.now()) return false;
  return safeEqual(mac, await sign(expires, secret));
}
