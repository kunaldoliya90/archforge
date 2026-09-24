#!/usr/bin/env python3
"""ArchForge static site builder.

No config file: the site structure *is* the docs/ folder.

    docs/index.md                      → /                      (home)
    docs/01-architecture/01-hld.md     → /architecture/hld/     (section "Architecture")
    docs/assets/hld_overview.png       → /assets/hld_overview.png

* Every folder in docs/ becomes a sidebar section; every .md file becomes a page.
* Page titles come from the first "# Heading" in the file; the one in
  docs/index.md is also the site name shown in the top bar.
* Optional "NN-" prefixes on files/folders control order and are stripped from URLs.
* Link to other pages with their relative .md path — broken links fail the build.
* Images under docs/assets/ render as zoomable diagram cards, and `<!-- diagrams -->`
  in any page expands to a gallery of every diagram.
* A `<!-- public -->` first line marks a page as public. Each public page gets a second copy
  under public/_public/ whose sidebar, search and gallery show only public pages, plus
  a manifest that middleware.js uses to serve it without a sign-in.

    python build.py            # build into public/
"""

from __future__ import annotations

import html
import json
import posixpath
import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from string import Template

import markdown
from pygments.formatters import HtmlFormatter

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / "docs"
THEME = ROOT / "theme"
ARCH = ROOT / "architecture"
OUT = ROOT / "public"
PUBLIC_DIR = "_public"  # public/_public/: the copy of the site that anonymous visitors see

ACRONYMS = {"ai", "api", "adr", "hld", "lld", "llm", "sdk"}
PREFIX = re.compile(r"^(\d+)[-_]")
PUBLIC_MARK = re.compile(r"\A\s*<!--\s*public\s*-->[ \t]*\n?")  # first line only, so code samples can show it
LIVE_RELOAD = '<script>new EventSource("/__reload").onmessage = () => location.reload();</script>'


class BuildError(Exception):
    pass


def write_file(dest: Path, data: bytes | str) -> bool:
    """Write only when the contents changed (rebuilds stay fast on slow Docker bind mounts).

    Returns True if the file was written.
    """
    if isinstance(data, str):
        data = data.encode("utf-8")
    if dest.exists() and dest.stat().st_size == len(data) and dest.read_bytes() == data:
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return True


# ── Structure ────────────────────────────────────────────────────────────────

def order_key(path: Path) -> tuple[int, int, str]:
    if path.stem == "index":
        return (0, 0, "")
    match = PREFIX.match(path.name)
    return (1, int(match.group(1)) if match else 10**6, path.name)


def slug(name: str) -> str:
    return PREFIX.sub("", name)


def humanize(name: str) -> str:
    words = re.split(r"[-_\s]+", slug(name))
    return " ".join(w.upper() if w.lower() in ACRONYMS else w.capitalize() for w in words)


def static_url(rel: str) -> str:
    return "/" + "/".join(slug(part) for part in rel.split("/"))


@dataclass
class Page:
    src: Path
    section: str | None
    url: str = ""
    title: str = ""
    html: str = ""
    toc: list[tuple[int, str, str]] = field(default_factory=list)
    description: str = ""
    public: bool = False

    @property
    def rel(self) -> str:
        return self.src.relative_to(DOCS).as_posix()


def page_url(src: Path) -> str:
    rel = src.relative_to(DOCS)
    parts = [slug(p) for p in rel.parent.parts]
    if slug(rel.stem) != "index":
        parts.append(slug(rel.stem))
    return "/" + "".join(f"{p}/" for p in parts)


def discover() -> list[tuple[str | None, list[Page]]]:
    """Nav groups in order: root pages first (no label), then one group per folder."""
    groups: list[tuple[str | None, list[Page]]] = []
    root_pages = sorted(DOCS.glob("*.md"), key=order_key)
    if root_pages:
        groups.append((None, [Page(p, None) for p in root_pages]))
    folders = [d for d in DOCS.iterdir() if d.is_dir() and not d.name.startswith((".", "_"))]
    for folder in sorted(folders, key=order_key):
        pages = sorted(folder.rglob("*.md"), key=lambda p: (len(p.relative_to(folder).parts), order_key(p)))
        if pages:
            label = humanize(folder.name)
            groups.append((label, [Page(p, label) for p in pages]))
    for _, pages in groups:
        for page in pages:
            page.url = page_url(page.src)
            text = page.src.read_text(encoding="utf-8")
            heading = re.search(r"^#\s+(.+?)\s*$", text, re.M)
            page.title = heading.group(1) if heading else humanize(page.src.stem)
            page.public = bool(PUBLIC_MARK.search(text))
    return groups


@dataclass
class View:
    """One audience's copy of the site: every page for signed-in readers, or only the public ones."""
    groups: list[tuple[str | None, list[Page]]]
    out: Path
    search_url: str
    pages: list[Page] = field(init=False)

    def __post_init__(self) -> None:
        self.pages = [p for _, pages in self.groups for p in pages]

    @property
    def home_url(self) -> str:
        if not self.pages or any(p.url == "/" for p in self.pages):
            return "/"
        return self.pages[0].url


# ── Rendering ────────────────────────────────────────────────────────────────

def make_markdown() -> markdown.Markdown:
    return markdown.Markdown(
        # superfences (vs. the built-in fenced_code) allows code blocks nested in lists.
        extensions=["tables", "pymdownx.superfences", "pymdownx.highlight", "toc", "attr_list", "md_in_html",
                    "admonition", "sane_lists"],
        extension_configs={
            "pymdownx.highlight": {"guess_lang": False, "css_class": "highlight"},
            "toc": {"permalink": "#", "permalink_class": "anchor", "permalink_title": "Link to this section"},
        },
    )


def strip_tags(fragment: str) -> str:
    fragment = re.sub(r'<a class="anchor"[^>]*>.*?</a>', "", fragment, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


class Site:
    def __init__(self, dev: bool) -> None:
        self.dev = dev
        self.errors: list[str] = []
        self.changed = 0  # files actually rewritten by this build
        self.groups = discover()
        self.full = View(self.groups, OUT, "/search.json")
        public_groups = [(label, [p for p in pages if p.public]) for label, pages in self.groups]
        self.public = View([g for g in public_groups if g[1]], OUT / PUBLIC_DIR, f"/{PUBLIC_DIR}/search.json")
        self.pages = self.full.pages
        self.by_src = {p.rel: p for p in self.pages}
        self.diagrams: dict[str, tuple[str, list[Page]]] = {}  # asset url → (caption, pages using it)
        self.template = Template((THEME / "base.html").read_text(encoding="utf-8"))
        home = next((p for p in self.pages if p.url == "/"), None)
        self.site_name = home.title if home else "Docs"

    # links & images ----------------------------------------------------------
    def rewrite_links(self, body: str, page: Page) -> str:
        base = posixpath.dirname(page.rel)

        def repl(m: re.Match) -> str:
            attr, path, frag = m.group(1), m.group(2), m.group(3) or ""
            if not path or path.startswith("/") or re.match(r"^[a-z][a-z0-9+.-]*:", path, re.I):
                return m.group(0)
            target = posixpath.normpath(posixpath.join(base, html.unescape(path)))
            if target.endswith(".md"):
                linked = self.by_src.get(target)
                if not linked:
                    self.errors.append(f"docs/{page.rel}: broken link → {path}")
                    return m.group(0)
                return f'{attr}="{linked.url}{frag}"'
            if not (DOCS / target).is_file():
                self.errors.append(f"docs/{page.rel}: missing file → {path}")
                return m.group(0)
            return f'{attr}="{static_url(target)}{frag}"'

        return re.sub(r'\b(href|src)="([^"#]*)(#[^"]*)?"', repl, body)

    def figure(self, m: re.Match, page: Page) -> str:
        alt, src = html.unescape(m.group(1)), m.group(2)
        name = Path(src).stem
        self.diagrams.setdefault(src, (alt, []))[1].append(page)
        source = ARCH / f"{name}.py"
        badge = f'<code class="src-badge">architecture/{source.name}</code>' if source.exists() else ""
        return (
            f'<figure class="diagram" id="diagram-{name}">'
            f'<button class="diagram-open" type="button" data-src="{src}" data-caption="{html.escape(alt)}" aria-label="Zoom: {html.escape(alt)}">'
            f'<img src="{src}" alt="{html.escape(alt)}" loading="lazy"></button>'
            f'<figcaption><span class="cap">{html.escape(alt)}</span>{badge}'
            f'<span class="hint">Click to zoom</span></figcaption></figure>'
        )

    def render(self, page: Page, md: markdown.Markdown) -> None:
        md.reset()
        body = md.convert(PUBLIC_MARK.sub("", page.src.read_text(encoding="utf-8")))
        body = self.rewrite_links(body, page)
        body = re.sub(r'<p>\s*<img alt="([^"]*)" src="(/assets/[^"]+)"\s*/?>\s*</p>',
                      lambda m: self.figure(m, page), body)
        body = body.replace("<table>", '<div class="table-wrap"><table>').replace("</table>", "</table></div>")
        page.html = body

        def walk(tokens: list[dict]) -> None:
            for t in tokens:
                if t["level"] in (2, 3):
                    page.toc.append((t["level"], t["id"], html.unescape(t["name"])))
                walk(t["children"])

        walk(md.toc_tokens)
        first_p = re.search(r"<p>(.*?)</p>", body, re.S)
        page.description = strip_tags(first_p.group(1))[:180] if first_p else ""

    # gallery -----------------------------------------------------------------
    def gallery(self, view: View) -> str:
        assets = sorted((DOCS / "assets").glob("*.png")) if (DOCS / "assets").is_dir() else []
        order = {p.url: i for i, p in enumerate(view.pages)}
        cards = []
        for asset in assets:
            src = f"/assets/{asset.name}"
            caption, users = self.diagrams.get(src, (humanize(asset.stem), []))
            page = next((p for p in users if p.url in order), None)
            if not page and view is not self.full:
                continue  # The public copy only shows diagrams that appear on a public page.
            href = f"{page.url}#diagram-{asset.stem}" if page else src
            where = page.title if page else "Unlinked diagram"
            cards.append((order.get(page.url, 999) if page else 999, (
                f'<a class="card" href="{href}"><div class="thumb"><img src="{src}" alt="" loading="lazy"></div>'
                f'<div class="meta"><strong>{html.escape(caption)}</strong><span>{html.escape(where)} →</span></div></a>'
            )))
        return '<div class="gallery">' + "".join(c for _, c in sorted(cards, key=lambda c: c[0])) + "</div>"

    # chrome ------------------------------------------------------------------
    def nav_html(self, current: Page | None, view: View) -> str:
        out = ['<nav class="nav" aria-label="Documentation">']
        for label, pages in view.groups:
            out.append('<div class="nav-group">')
            if label:
                out.append(f'<div class="nav-label">{html.escape(label)}</div>')
            for p in pages:
                active = ' active" aria-current="page' if current is p else ""
                title = "Overview" if p.url == "/" else p.title
                out.append(f'<a class="nav-link{active}" href="{p.url}">{html.escape(title)}</a>')
            out.append("</div>")
        out.append("</nav>")
        return "".join(out)

    def toc_html(self, page: Page) -> str:
        if len(page.toc) < 2:
            return ""
        links = "".join(f'<a class="toc-link lvl{lvl}" href="#{i}">{html.escape(name)}</a>' for lvl, i, name in page.toc)
        return f'<div class="toc-inner"><div class="toc-label">On this page</div>{links}</div>'

    def pager_html(self, page: Page, view: View) -> str:
        pages = view.pages
        i = pages.index(page)
        prev_p = pages[i - 1] if i > 0 else None
        next_p = pages[i + 1] if i + 1 < len(pages) else None
        if not (prev_p or next_p):
            return ""

        def card(p: Page | None, label: str, cls: str) -> str:
            if not p:
                return "<span></span>"
            return f'<a class="pager-card {cls}" href="{p.url}"><span>{label}</span><strong>{html.escape(p.title)}</strong></a>'

        return f'<nav class="pager">{card(prev_p, "← Previous", "prev")}{card(next_p, "Next →", "next")}</nav>'

    def write(self, view: View, url: str, page: Page | None, content: str, title: str, body_class: str) -> None:
        eyebrow = f'<div class="eyebrow">{html.escape(page.section)}</div>' if page and page.section else ""
        doc = self.template.substitute(
            title=html.escape(title),
            site_name=html.escape(self.site_name),
            home_url=view.home_url,
            search_url=view.search_url,
            description=html.escape(page.description if page else ""),
            body_class=body_class,
            nav=self.nav_html(page, view),
            eyebrow=eyebrow,
            content=content,
            toc=self.toc_html(page) if page else "",
            pager=self.pager_html(page, view) if page else "",
            live_reload=LIVE_RELOAD if self.dev else "",
        )
        dest = view.out / url.lstrip("/")
        if url.endswith("/"):
            dest = dest / "index.html"
        self.changed += write_file(dest, doc)

    # search ------------------------------------------------------------------
    def search_index(self, view: View) -> list[dict]:
        entries = []
        for page in view.pages:
            body = page.html
            heads = list(re.finditer(r'<h([1-3])[^>]*?id="([^"]+)"[^>]*>(.*?)</h\1>', body, re.S))
            spans = [(None, "", 0)] + [
                (m.group(2) if m.group(1) != "1" else None, strip_tags(m.group(3)) if m.group(1) != "1" else "", m.end())
                for m in heads
            ]
            ends = [m.start() for m in heads] + [len(body)]
            for (anchor, heading, start), end in zip(spans, ends):
                text = strip_tags(body[start:end])
                if text or heading:
                    entries.append({
                        "p": page.title, "g": page.section or "", "h": heading,
                        "u": page.url + (f"#{anchor}" if anchor else ""), "x": text[:1200],
                    })
        return entries

    # build -------------------------------------------------------------------
    def build(self) -> None:
        md = make_markdown()
        for page in self.pages:
            self.render(page, md)
        if self.errors:
            raise BuildError("\n".join(self.errors))

        public_files: set[str] = set()
        for view in (self.full, self.public):
            gallery = self.gallery(view)
            for page in view.pages:
                content = page.html.replace("<!-- diagrams -->", gallery)
                is_home = page.url == "/"
                title = self.site_name if is_home else f"{page.title} · {self.site_name}"
                self.write(view, page.url, page, content, title, "home" if is_home else "doc")
                if view is self.public:
                    public_files |= self.linked_files(content)
            self.changed += write_file(view.out / "search.json",
                                       json.dumps(self.search_index(view), ensure_ascii=False))

        # Read by middleware.js to decide what anonymous visitors may open.
        manifest = {"pages": [p.url for p in self.public.pages], "files": sorted(public_files)}
        self.changed += write_file(OUT / PUBLIC_DIR / "manifest.json", json.dumps(manifest, indent=2))

        self.write(self.full, "/404.html", None,
                   '<h1>Page not found</h1><p>That page doesn\'t exist. Try the search (<kbd>Ctrl</kbd> <kbd>K</kbd>) '
                   'or head back to the <a href="/">overview</a>.</p>', f"Not found · {self.site_name}", "doc")

        # Static files from docs/ (diagrams, images) and the theme.
        for f in DOCS.rglob("*"):
            if f.is_file() and f.suffix != ".md" and not f.name.startswith("."):
                dest = OUT / static_url(f.relative_to(DOCS).as_posix()).lstrip("/")
                self.changed += write_file(dest, f.read_bytes())
        theme_out = OUT / "_theme"
        for f in THEME.iterdir():
            if f.is_file() and f.name != "base.html":
                self.changed += write_file(theme_out / f.name, f.read_bytes())
        light = HtmlFormatter(style="xcode", nobackground=True).get_style_defs('[data-theme="light"] .highlight')
        dark = HtmlFormatter(style="github-dark", nobackground=True).get_style_defs('[data-theme="dark"] .highlight')
        self.changed += write_file(theme_out / "pygments.css", light + "\n" + dark)

    @staticmethod
    def linked_files(content: str) -> set[str]:
        """Site files (images, downloads) a page links to, so its public copy can load them."""
        urls = re.findall(r'\b(?:src|href|data-src)="(/[^"#?]+)', content)
        return {u for u in urls if Path(u).suffix and not u.startswith("/_theme/")}


def build(dev: bool = False) -> tuple[int, int]:
    """Build the site into public/. Returns (pages, files that changed)."""
    if not dev and OUT.exists():
        shutil.rmtree(OUT)
    site = Site(dev)
    site.build()
    return len(site.pages), site.changed


if __name__ == "__main__":
    try:
        count, _ = build()
    except BuildError as exc:
        print(f"Build failed:\n{exc}", file=sys.stderr)
        sys.exit(1)
    print(f"Built {count} pages into {OUT.relative_to(ROOT)}/")
