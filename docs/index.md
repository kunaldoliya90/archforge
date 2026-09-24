# ArchForge

Architecture diagrams as code, with docs that update as you type. Write diagrams in Python and pages in Markdown. Every save re-renders the diagram, rebuilds the site and refreshes your browser, and the whole thing deploys to Vercel behind a password.

<!-- diagrams -->

## How it works

| Step | You do | ArchForge does |
|---|---|---|
| 1 | Run `python watch.py --serve` | Renders every diagram, builds the site, serves it at `localhost:8000` |
| 2 | Save a diagram in `architecture/` | Re-renders its PNG and refreshes the browser (~1–2 s) |
| 3 | Save a page in `docs/` | Rebuilds the site and refreshes the browser (~1 s) |
| 4 | Push to GitHub | Vercel builds the static site; visitors log in with a password you set |

## Why ArchForge

- **Diagrams are code.** They're reviewed in pull requests, diffed in git, and never go stale in someone's drawing tool.
- **No config files.** The sidebar is your folder structure, and page titles are your headings.
- **Zero install beyond Docker.** Graphviz and every Python dependency live in the container.
- **Readable output.** Search (<kbd>Ctrl</kbd> <kbd>K</kbd>), zoomable diagrams, dark mode, and a layout that works on mobile.
- **Private by default.** A few lines of Vercel Edge Middleware ask for a password before any page is served.

## Next steps

- [Getting started](01-guide/01-getting-started.md): run it locally in two minutes.
- [Writing diagrams](01-guide/02-writing-diagrams.md): the Python API, shared styles and conventions.
- [Writing pages](01-guide/03-writing-pages.md): how folders become navigation, plus every Markdown feature.
- [Deploying](01-guide/04-deploying.md): put it on Vercel behind a password.

!!! tip "Make it yours"
    Change the first heading of `docs/index.md` to rename the site. Replace the files in `architecture/` and `docs/` with your own system. Everything else keeps working.
