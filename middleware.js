// Vercel Edge Middleware: password-protects the whole static site behind a sign-in page.
// Credentials come from the ADMIN_USER / ADMIN_PASS environment variables
// (Vercel → Project → Settings → Environment Variables). Runs before any file is served,
// so unauthenticated visitors never receive page HTML or diagram images.
//
//   /login/     sign-in form (GET) and credential check (POST)
//   /logout/    ends the session
//   /_theme/    CSS, JS and icons: always open
//   /_public/   the public copy of pages marked <!-- public --> (see auth/public-pages.js)
//   anything    needs a valid session cookie (see auth/session.js), except public pages,
//               which anonymous visitors see at their normal URL

import { renderLoginPage } from "./auth/login-page.js";
import { PUBLIC_PREFIX, loadPublicManifest, pageKey } from "./auth/public-pages.js";
import { clearedSessionCookie, hasValidSession, safeEqual, sessionCookie } from "./auth/session.js";

export const config = {
  matcher: "/:path*",
};

const FAILED_LOGIN_DELAY_MS = 600;
const OPEN_PREFIXES = ["/_theme/", `${PUBLIC_PREFIX}/`];

// ---- Responses --------------------------------------------------------------

function html(body, status = 200) {
  return new Response(body, {
    status,
    headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store" },
  });
}

function redirect(location, cookie) {
  const headers = { Location: location, "Cache-Control": "no-store" };
  if (cookie) headers["Set-Cookie"] = cookie;
  return new Response(null, { status: 303, headers });
}

// Lets Vercel serve the requested file (what @vercel/edge's next() does).
function passThrough() {
  return new Response(null, { headers: { "x-middleware-next": "1" } });
}

// Serves another path's file under the requested URL (what @vercel/edge's rewrite() does).
function rewrite(url) {
  return new Response(null, { headers: { "x-middleware-rewrite": url.toString() } });
}

function unauthorized() {
  return new Response("Authentication required", { status: 401, headers: { "Cache-Control": "no-store" } });
}

// Only same-site paths, so the login form can't be used as an open redirect.
function safeNext(value) {
  const ok = typeof value === "string" && value.startsWith("/") && !value.startsWith("//") && !value.startsWith("/\\");
  return ok ? value : "/";
}

// ---- Routes -----------------------------------------------------------------

async function showLogin(request, url, secret) {
  const next = safeNext(url.searchParams.get("next"));
  if (await hasValidSession(request, secret)) return redirect(next);
  return html(renderLoginPage({ next }));
}

async function submitLogin(request, { user, pass, secret }) {
  const form = await request.formData().catch(() => null);
  const givenUser = String(form?.get("username") ?? "");
  const givenPass = String(form?.get("password") ?? "");
  const next = safeNext(form?.get("next"));

  // Evaluate both comparisons so timing doesn't reveal which one failed.
  const userOk = safeEqual(givenUser, user);
  const passOk = safeEqual(givenPass, pass);
  if (userOk && passOk) return redirect(next, await sessionCookie(secret));

  await new Promise((resolve) => setTimeout(resolve, FAILED_LOGIN_DELAY_MS)); // Slows down guessing.
  return html(renderLoginPage({ next, username: givenUser, error: "Incorrect username or password." }), 401);
}

function logout() {
  return redirect("/login/", clearedSessionCookie());
}

// Anonymous visitors get the public copy of a public page, and the images it uses.
async function servePublic(url) {
  const { pages, files } = await loadPublicManifest(url.origin);
  const key = pageKey(url.pathname);
  if (pages.has(key)) return rewrite(new URL(PUBLIC_PREFIX + key, url));
  if (files.has(url.pathname)) return passThrough();
  return null;
}

// Page visits are sent to the sign-in page; other files (images, search.json) just get 401.
function requireLogin(request, url) {
  const wantsPage = request.method === "GET" && (request.headers.get("accept") || "").includes("text/html");
  if (!wantsPage) return unauthorized();
  return redirect(`/login/?next=${encodeURIComponent(url.pathname + url.search)}`);
}

// ---- Entry point ------------------------------------------------------------

export default async function middleware(request) {
  const user = process.env.ADMIN_USER;
  const pass = process.env.ADMIN_PASS;

  // Fail closed: a missing env var must never mean "public".
  if (!user || !pass) {
    return new Response("Site locked: ADMIN_USER / ADMIN_PASS are not configured.", { status: 503 });
  }

  // Changing the password (or SESSION_SECRET) invalidates every existing session.
  const secret = process.env.SESSION_SECRET || `${user}:${pass}`;
  const url = new URL(request.url);
  const path = url.pathname.replace(/\/+$/, "") || "/";

  if (path === "/login") {
    return request.method === "POST"
      ? submitLogin(request, { user, pass, secret })
      : showLogin(request, url, secret);
  }
  if (path === "/logout") return logout();
  if (OPEN_PREFIXES.some((prefix) => url.pathname.startsWith(prefix))) return passThrough();

  if (await hasValidSession(request, secret)) return passThrough();
  return (await servePublic(url)) ?? requireLogin(request, url);
}
