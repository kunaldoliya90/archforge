# Writing pages

Pages are Markdown files in `docs/`. There's no configuration file: the folder structure *is* the site.

## Folders become navigation

```text
docs/
├── index.md                       →  /                          Home
├── 01-guide/                      →  sidebar section "Guide"
│   ├── 01-getting-started.md      →  /guide/getting-started/
│   └── 02-writing-diagrams.md     →  /guide/writing-diagrams/
├── 02-examples/                   →  sidebar section "Examples"
│   └── 01-web-app.md              →  /examples/web-app/
└── assets/                        ←  PNGs rendered from architecture/
```

| Rule | Example |
|---|---|
| A folder becomes a sidebar section | `03-operations/` → **Operations** |
| A `.md` file becomes a page | `03-operations/runbook.md` → `/operations/runbook/` |
| A page's title is its first `# Heading` | `# Incident runbook` |
| An optional `NN-` prefix sets the order and is removed from URLs | `02-writing-diagrams.md` → `/guide/writing-diagrams/` |
| The first heading of `docs/index.md` is the site name | `# ArchForge` |

**To add a page, create a Markdown file.** It appears in the sidebar on the next save.

## Links

Link to other pages by their relative `.md` path:

```markdown
See [Writing diagrams](02-writing-diagrams.md) or the [web app example](../02-examples/01-web-app.md#components).
```

ArchForge rewrites these to the real URLs. A link to a page that doesn't exist **fails the build**, so broken links never reach production.

## Markdown features

Everything in standard Markdown works: tables, fenced code with syntax highlighting, lists and inline HTML. There are also a few extras.

### Callouts

```markdown
!!! warning "Heads up"
    Indented content goes inside the box.
```

!!! warning "Heads up"
    Indented content goes inside the box.

Types: `note`, `tip`, `warning`, `danger`.

### Collapsible blocks

```markdown
<details markdown="1">
<summary>ADR-001: Use Postgres</summary>

Markdown works in here.
</details>
```

<details markdown="1">
<summary>ADR-001: Use Postgres</summary>

Markdown works in here: **bold**, `code`, lists and tables.
</details>

### Diagram gallery

Put `<!-- diagrams -->` anywhere on a page to insert a grid of every diagram, linking each one to the page that uses it. The home page does this.

## Customising the look

The theme is plain HTML, CSS and JavaScript in `theme/`, with no framework and no build step:

| File | What it controls |
|---|---|
| `theme/style.css` | Colours, fonts and layout. Change the tokens at the top to rebrand. |
| `theme/base.html` | The page shell: top bar, sidebar, search and diagram viewer |
| `theme/app.js` | Search, dark mode, the outline and the zoomable diagram viewer |
| `theme/favicon.svg` | The logo in the top bar and browser tab |
