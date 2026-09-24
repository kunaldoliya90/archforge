// Vercel Edge Middleware: password-protects the whole static site with HTTP Basic Auth.
// Credentials come from the ADMIN_USER / ADMIN_PASS environment variables
// (Vercel → Project → Settings → Environment Variables). Runs before any file is served,
// so unauthenticated visitors never receive page HTML or diagram images.

export const config = {
  matcher: "/:path*",
};

const REALM = "Protected documentation";

function unauthorized(message = "Authentication required") {
  return new Response(message, {
    status: 401,
    headers: {
      "WWW-Authenticate": `Basic realm="${REALM}", charset="UTF-8"`,
      "Cache-Control": "no-store",
    },
  });
}

// Compares every character regardless of where the first mismatch is, so response
// timing doesn't reveal how much of the password was right.
function safeEqual(a, b) {
  let diff = a.length ^ b.length;
  for (let i = 0; i < Math.max(a.length, b.length); i++) {
    diff |= (a.charCodeAt(i) || 0) ^ (b.charCodeAt(i) || 0);
  }
  return diff === 0;
}

export default function middleware(request) {
  const user = process.env.ADMIN_USER;
  const pass = process.env.ADMIN_PASS;

  // Fail closed: a missing env var must never mean "public".
  if (!user || !pass) {
    return new Response("Site locked: ADMIN_USER / ADMIN_PASS are not configured.", { status: 503 });
  }

  const header = request.headers.get("authorization") || "";
  const [scheme, encoded] = header.split(" ");
  if (scheme !== "Basic" || !encoded) return unauthorized();

  let decoded;
  try {
    decoded = new TextDecoder().decode(Uint8Array.from(atob(encoded), (c) => c.charCodeAt(0)));
  } catch {
    return unauthorized();
  }
  const sep = decoded.indexOf(":");
  const givenUser = decoded.slice(0, sep);
  const givenPass = decoded.slice(sep + 1);

  // Evaluate both comparisons so timing doesn't reveal which one failed.
  const userOk = safeEqual(givenUser, user);
  const passOk = safeEqual(givenPass, pass);
  if (sep === -1 || !(userOk && passOk)) return unauthorized("Invalid credentials");

  // Returning nothing lets Vercel continue and serve the static file.
}
