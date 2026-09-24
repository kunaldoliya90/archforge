# Deploying

ArchForge builds to plain static files in `public/`, so it runs on any static host. The repository comes ready for **Vercel**, including password protection.

## Vercel

1. Push the repository to GitHub.
2. In Vercel, click **Add New → Project** and import the repository. `vercel.json` already sets everything, so no framework preset is needed:

    | Setting | Value |
    |---|---|
    | Install | `python3 -m pip install --break-system-packages -r requirements-docs.txt` |
    | Build | `python3 build.py` |
    | Output | `public` |

3. Under **Settings → Environment Variables**, add `ADMIN_USER` and `ADMIN_PASS`.
4. Deploy.

Visitors now see a sign-in page before any page or image is served.

## How the password works

`middleware.js` is a Vercel Edge Middleware function that runs before every request:

- **No session:** page visits redirect to `/login/`. Other files (images, `search.json`) return `401`.
- **Correct credentials:** the login form sets a signed, `HttpOnly` session cookie valid for 7 days, and the visitor returns to the page they asked for.
- **Wrong credentials:** the login page shows an error.
- **Env vars not set:** `503`. The site fails closed and never becomes public by accident.

The check happens on the server, so unauthenticated visitors never receive the HTML or the images. This is stronger than a JavaScript-only login page, where the content still reaches the browser.

Sessions are signed with `SESSION_SECRET` if you set it, otherwise with a key derived from the credentials. Changing `ADMIN_PASS` therefore signs everyone out.

!!! tip "Logging out"
    Visit `/logout/` to clear the session cookie and return to the sign-in page.

## Sharing individual pages

To share one page without the password, make this the first line of its Markdown file:

```markdown
<!-- public -->
```

Deploy, then send the page's normal URL. Anyone can open it and the diagrams on it without signing in. Every other page stays private.

Anonymous visitors see a copy of the page where the sidebar, search, gallery and previous/next links include only public pages, so private page titles and content never reach them. Signed-in readers still see the full site. Links from a public page to a private one lead to the sign-in page.

`build.py` writes these copies to `public/_public/` along with a `manifest.json` listing the public pages and their images. `middleware.js` reads that manifest to decide what to serve without a session.

To make a page private again, delete the line and redeploy.

## Making it public

To publish without a password, delete `middleware.js`.

## Other hosts

Run `python build.py` and upload `public/` to Netlify, Cloudflare Pages, GitHub Pages or S3. On hosts other than Vercel, `middleware.js` doesn't apply, so use that host's own access controls if you need a password.

## Continuous integration

`.github/workflows/ci.yml` runs on every pull request and checks that:

- every diagram script renders;
- every diagram has a committed PNG;
- the site builds with no broken links.
