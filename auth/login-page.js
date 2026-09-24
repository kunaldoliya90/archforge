// The sign-in page, rendered by the middleware. Styles live in theme/login.css,
// which is served without a session.

export const LOGIN_ASSETS = ["/_theme/login.css", "/_theme/favicon.svg"];

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[c]);
}

export function renderLoginPage({ next = "/", username = "", error = "" } = {}) {
  const focusPassword = Boolean(username);
  return `<!doctype html>
<html lang="en" data-theme="light">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex, nofollow">
  <title>Sign in</title>
  <script>
    (function () {
      var t = null;
      try { t = localStorage.getItem("docs-theme"); } catch (e) {}
      if (t !== "light" && t !== "dark") t = matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
      document.documentElement.setAttribute("data-theme", t);
    })();
  </script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap">
  <link rel="stylesheet" href="/_theme/login.css">
  <link rel="icon" type="image/svg+xml" href="/_theme/favicon.svg">
</head>
<body>
  <main class="card">
    <img class="mark" src="/_theme/favicon.svg" alt="" width="36" height="36">
    <h1>Sign in</h1>
    <p class="sub">This documentation is private. Sign in to continue.</p>
    ${error ? `<p class="error" role="alert">${escapeHtml(error)}</p>` : ""}
    <form method="post" action="/login/">
      <input type="hidden" name="next" value="${escapeHtml(next)}">
      <label for="username">Username</label>
      <input id="username" name="username" autocomplete="username" required value="${escapeHtml(username)}"${focusPassword ? "" : " autofocus"}>
      <label for="password">Password</label>
      <input id="password" name="password" type="password" autocomplete="current-password" required${focusPassword ? " autofocus" : ""}>
      <button type="submit">Sign in</button>
    </form>
  </main>
</body>
</html>`;
}
