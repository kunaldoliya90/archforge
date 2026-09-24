# Deploying

ArchForge builds to plain static files in `public/`, so it runs on any static host. The repository comes ready for **Vercel**, including password protection.

## Vercel

1. Push the repository to GitHub.
2. In Vercel, click **Add New → Project** and import the repository. `vercel.json` already sets everything, so no framework preset is needed:

    | Setting | Value |
    |---|---|
    | Install | `python3 -m pip install -r requirements-docs.txt` |
    | Build | `python3 build.py` |
    | Output | `public` |

3. Under **Settings → Environment Variables**, add `ADMIN_USER` and `ADMIN_PASS`.
4. Deploy.

Visitors now get a browser login prompt before any page or image is served.

## How the password works

`middleware.js` is a Vercel Edge Middleware function that runs before every request:

- **Correct credentials:** the file is served.
- **Missing or wrong credentials:** `401`, and the browser asks for a login.
- **Env vars not set:** `503`. The site fails closed and never becomes public by accident.

The check happens on the server, so unauthenticated visitors never receive the HTML or the images. This is stronger than a JavaScript login page, where the content still reaches the browser.

!!! tip "Logging out"
    Browsers cache Basic Auth credentials until they close. To switch users, visit `https://logout@your-domain.vercel.app` to replace the cached login.

## Making it public

To publish without a password, delete `middleware.js`.

## Other hosts

Run `python build.py` and upload `public/` to Netlify, Cloudflare Pages, GitHub Pages or S3. On hosts other than Vercel, `middleware.js` doesn't apply, so use that host's own access controls if you need a password.

## Continuous integration

`.github/workflows/ci.yml` runs on every pull request and checks that:

- every diagram script renders;
- every diagram has a committed PNG;
- the site builds with no broken links.
